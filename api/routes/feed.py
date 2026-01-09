"""
Feed 路由 - 投喂和输出
"""
from collections import defaultdict
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import json

from api.services.db_service import db
from api.services.ai_service import (
    clean_and_update_structure,
    generate_output,
    generate_narrative_with_meta
)
from api.auth import get_current_user_flexible

logger = logging.getLogger(__name__)

router = APIRouter()


class FeedRequest(BaseModel):
    """投喂请求"""
    content: str


class FeedResponse(BaseModel):
    """投喂响应"""
    status: str
    message: str
    feed_id: str


class FeedItem(BaseModel):
    """投喂项"""
    id: str
    content: str
    cleaned_content: Optional[str] = None
    created_at: str


class FeedListResponse(BaseModel):
    """投喂列表响应"""
    feeds: List[FeedItem]


class OutputRequest(BaseModel):
    """输出请求"""
    instruction: str  # 例如: "写一段给程序员看的需求说明"


class OutputResponse(BaseModel):
    """输出响应"""
    content: str
    mind_id: str


async def _process_feed(mind_id: str, feed_id: str, content: str):
    """处理投喂：去噪 + 更新结构（后台任务）"""
    try:
        mind = db.get_mind(mind_id)
        if not mind:
            return

        # 调用去噪+结构更新组合器
        cleaned_content, new_structure, summary = await clean_and_update_structure(
            content=content,
            current_structure=mind.get("crystal"),
            mind_title=mind["title"]
        )

        # 保存去噪内容
        db.update_feed_cleaned(feed_id, cleaned_content)

        # 更新结构
        db.update_crystal(mind_id, new_structure, summary)

        logger.info(f"Mind {mind_id} 处理完成: {summary}")

    except Exception as e:
        logger.error(f"处理 Mind {mind_id} 失败: {e}")


@router.post("/minds/{mind_id}/feed", response_model=FeedResponse)
async def add_feed(mind_id: str, request: FeedRequest, background_tasks: BackgroundTasks,
                   user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """向 Mind 投喂想法"""
    mind = db.get_mind(mind_id, user_id=user["id"])
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    # 记录投喂
    feed_id = f"feed_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    db.add_feed(feed_id, mind_id, request.content)

    # 异步处理：去噪 + 更新结构
    background_tasks.add_task(_process_feed, mind_id, feed_id, request.content)

    return FeedResponse(
        status="ok",
        message="已记录，正在处理",
        feed_id=feed_id
    )


@router.get("/minds/{mind_id}/feeds", response_model=FeedListResponse)
async def get_feeds(mind_id: str, limit: int = 20, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """获取 Mind 的投喂列表"""
    mind = db.get_mind(mind_id, user_id=user["id"])
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    feeds = db.get_feeds(mind_id, limit)

    return FeedListResponse(feeds=[
        FeedItem(
            id=f["id"],
            content=f["content"],
            cleaned_content=f.get("cleaned_content"),
            created_at=f["created_at"]
        )
        for f in feeds
    ])


class UpdateFeedRequest(BaseModel):
    """更新投喂请求"""
    content: str


@router.put("/feeds/{feed_id}")
async def update_feed(feed_id: str, request: UpdateFeedRequest,
                      user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """更新投喂内容（直接更新 cleaned_content）"""
    # 注：此处简化处理，实际应验证 feed 归属
    result = db.update_feed_content(feed_id, request.content)
    if not result:
        raise HTTPException(status_code=404, detail="Feed not found")
    return {"status": "ok", "message": "已更新"}


@router.delete("/feeds/{feed_id}")
async def delete_feed(feed_id: str, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """删除投喂"""
    # 注：此处简化处理，实际应验证 feed 归属
    result = db.delete_feed(feed_id)
    if not result:
        raise HTTPException(status_code=404, detail="Feed not found")
    return {"status": "ok", "message": "已删除"}


@router.post("/minds/{mind_id}/output", response_model=OutputResponse)
async def generate_mind_output(mind_id: str, request: OutputRequest,
                               user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """根据指令生成输出（基于去噪内容，注入相关记忆上下文）"""
    mind = db.get_mind(mind_id, user_id=user["id"])
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    # 获取所有去噪后的内容
    cleaned_feeds = db.get_all_cleaned_feeds(mind_id)
    if not cleaned_feeds:
        raise HTTPException(
            status_code=400,
            detail="Mind 还没有足够的内容，请先投喂一些想法"
        )

    try:
        # 构建晶体内容用于匹配记忆
        crystal_content = "\n".join([
            f.get('cleaned_content', '') for f in cleaned_feeds if f.get('cleaned_content')
        ])
        
        # 匹配相关记忆并格式化
        matched_memories = db.match_memories_by_content(user["id"], crystal_content)
        memory_context = db.format_matched_memories(matched_memories)
        
        if matched_memories:
            logger.info(f"输出注入 {len(matched_memories)} 条相关记忆")

        output = await generate_output(
            cleaned_feeds=cleaned_feeds,
            instruction=request.instruction,
            mind_title=mind["title"],
            structure=mind.get("crystal"),
            memory_context=memory_context
        )

        # 记录输出
        output_id = f"output_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        db.add_output(output_id, mind_id, request.instruction, output)

        return OutputResponse(content=output, mind_id=mind_id)

    except Exception as e:
        logger.error(f"生成输出失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 时间轴视图 ==========

class TimelineItem(BaseModel):
    """时间轴项"""
    date: str
    items: List[dict]


class TimelineViewResponse(BaseModel):
    """时间轴视图响应"""
    timeline: List[TimelineItem]


@router.get("/minds/{mind_id}/timeline-view")
async def get_timeline_view(mind_id: str, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """获取时间轴视图（按日期分组的去噪记录）"""
    mind = db.get_mind(mind_id, user_id=user["id"])
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    feeds = db.get_all_cleaned_feeds(mind_id)

    # 按日期分组
    grouped = defaultdict(list)
    for f in feeds:
        date = f["created_at"][:10]  # 取日期部分
        time = f["created_at"][11:16]  # 取时间部分
        grouped[date].append({
            "id": f["id"],
            "time": time,
            "content": f["cleaned_content"]
        })

    # 转换为列表，日期倒序（新日期在前），每天内的 items 也按时间倒序（新时间在前）
    timeline = [
        {"date": date, "items": sorted(items, key=lambda x: x["time"], reverse=True)}
        for date, items in sorted(grouped.items(), reverse=True)
    ]

    return {"timeline": timeline}


# ========== 叙事视图 ==========

class NarrativeResponse(BaseModel):
    """叙事视图响应"""
    narrative: str
    feed_count: int
    summary: Optional[str] = None
    summary_changed: bool = False
    tags: List[str] = []
    tags_changed: bool = False


@router.post("/minds/{mind_id}/narrative")
async def generate_narrative_view(mind_id: str, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """生成叙事视图（点击触发），同时更新概述、标签，并提取记忆锚点"""
    mind = db.get_mind(mind_id, user_id=user["id"])
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    feeds = db.get_all_cleaned_feeds(mind_id)
    if not feeds:
        return NarrativeResponse(
            narrative="暂无内容，请先投喂一些想法",
            feed_count=0
        )

    try:
        # 获取当前概述和标签
        current_summary = mind.get("summary")
        current_tags = db.get_mind_tags(mind_id)

        # 获取全局标签库
        all_tags = db.get_all_tags()
        tag_library = [t["name"] for t in all_tags]

        # 获取现有晶体底层记忆摘要
        existing_memory = db.get_base_memory_summary(user["id"])

        # 调用带元数据的叙事生成（包含记忆锚点提取）
        result = await generate_narrative_with_meta(
            cleaned_feeds=feeds,
            mind_title=mind["title"],
            current_summary=current_summary,
            current_tags=current_tags,
            tag_library=tag_library,
            existing_memory=existing_memory
        )

        # 如果概述有变化，更新数据库
        if result["summary_changed"] and result["summary"]:
            db.update_mind_summary(mind_id, result["summary"])

        # 如果标签有变化，更新数据库
        if result["tags_changed"] and result["tags"]:
            db.set_mind_tags(mind_id, result["tags"])

        # 保存叙事内容
        if result["narrative"]:
            db.update_mind_narrative(mind_id, result["narrative"])

        # 处理记忆锚点
        memory_anchors = result.get("memory_anchors", [])
        anchors_created = 0
        anchors_updated = 0
        for anchor in memory_anchors:
            action = anchor.get("action", "skip")
            if action in ("create", "update"):
                db.upsert_base_memory(
                    user_id=user["id"],
                    key=anchor.get("key", ""),
                    definition=anchor.get("definition", ""),
                    category=anchor.get("category", "general"),
                    source_mind_id=mind_id
                )
                if action == "create":
                    anchors_created += 1
                else:
                    anchors_updated += 1
        
        if anchors_created or anchors_updated:
            logger.info(f"晶体底层记忆更新: 创建{anchors_created}条, 更新{anchors_updated}条")

        return NarrativeResponse(
            narrative=result["narrative"],
            feed_count=len(feeds),
            summary=result["summary"],
            summary_changed=result["summary_changed"],
            tags=result["tags"],
            tags_changed=result["tags_changed"]
        )

    except Exception as e:
        logger.error(f"生成叙事视图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
