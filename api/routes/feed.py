"""
Feed 路由 - 投喂和输出
"""
from collections import defaultdict
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from api.services.db_service import db
from api.services.ai_service import (
    clean_and_update_structure,
    generate_output,
    generate_narrative_with_meta
)
from api.auth import get_current_user

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
                   user: Dict[str, Any] = Depends(get_current_user)):
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
async def get_feeds(mind_id: str, limit: int = 20, user: Dict[str, Any] = Depends(get_current_user)):
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
                      user: Dict[str, Any] = Depends(get_current_user)):
    """更新投喂内容（直接更新 cleaned_content）"""
    # 注：此处简化处理，实际应验证 feed 归属
    result = db.update_feed_content(feed_id, request.content)
    if not result:
        raise HTTPException(status_code=404, detail="Feed not found")
    return {"status": "ok", "message": "已更新"}


@router.delete("/feeds/{feed_id}")
async def delete_feed(feed_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    """删除投喂"""
    # 注：此处简化处理，实际应验证 feed 归属
    result = db.delete_feed(feed_id)
    if not result:
        raise HTTPException(status_code=404, detail="Feed not found")
    return {"status": "ok", "message": "已删除"}


@router.post("/minds/{mind_id}/output", response_model=OutputResponse)
async def generate_mind_output(mind_id: str, request: OutputRequest,
                               user: Dict[str, Any] = Depends(get_current_user)):
    """根据指令生成输出（基于去噪内容）"""
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
        output = await generate_output(
            cleaned_feeds=cleaned_feeds,
            instruction=request.instruction,
            mind_title=mind["title"],
            structure=mind.get("crystal")
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
async def get_timeline_view(mind_id: str, user: Dict[str, Any] = Depends(get_current_user)):
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
async def generate_narrative_view(mind_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    """生成叙事视图（点击触发），同时更新概述和标签"""
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

        # 调用带元数据的叙事生成
        result = await generate_narrative_with_meta(
            cleaned_feeds=feeds,
            mind_title=mind["title"],
            current_summary=current_summary,
            current_tags=current_tags,
            tag_library=tag_library
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
