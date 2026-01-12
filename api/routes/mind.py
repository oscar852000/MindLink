"""
Mind 路由 - 管理想法空间
"""
import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from api.services.db_service import db
from api.services.ai_service import format_crystal_markdown, generate_mindmap_from_timeline, extract_unique_content
from api.auth import get_current_user_flexible
from api.prompts import ABSORB_SYSTEM_NOTE_TEMPLATE

logger = logging.getLogger(__name__)

router = APIRouter()


class MindCreate(BaseModel):
    """创建 Mind 请求"""
    title: str
    north_star: Optional[str] = None


class MindResponse(BaseModel):
    """Mind 响应"""
    id: str
    title: str
    north_star: Optional[str] = None
    summary: Optional[str] = None
    narrative: Optional[str] = None
    tags: List[str] = []
    crystal_markdown: Optional[str] = None
    created_at: str
    updated_at: str


class MindListResponse(BaseModel):
    """Mind 列表响应"""
    minds: List[MindResponse]


class CrystalResponse(BaseModel):
    """Crystal 响应（结构视图）"""
    mind_id: str
    structure_markdown: str  # 结构视图
    crystal_json: Optional[dict] = None
    updated_at: str


class TimelineEvent(BaseModel):
    """时间线事件"""
    id: int
    event_type: str
    summary: str
    created_at: str


class TimelineResponse(BaseModel):
    """时间线响应"""
    mind_id: str
    events: List[TimelineEvent]


@router.post("", response_model=MindResponse)
async def create_mind(request: MindCreate, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """创建新的 Mind"""
    mind_id = f"mind_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    mind = db.create_mind(
        mind_id=mind_id,
        title=request.title,
        user_id=user["id"],
        north_star=request.north_star
    )

    return MindResponse(
        id=mind["id"],
        title=mind["title"],
        north_star=mind.get("north_star"),
        summary=None,
        tags=[],
        crystal_markdown=format_crystal_markdown(mind.get("crystal")),
        created_at=mind["created_at"],
        updated_at=mind["updated_at"]
    )


@router.get("", response_model=MindListResponse)
async def list_minds(user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """获取当前用户的 Mind 列表"""
    minds = db.list_minds(user_id=user["id"])

    result = []
    for m in minds:
        tags = db.get_mind_tags(m["id"])
        result.append(MindResponse(
            id=m["id"],
            title=m["title"],
            north_star=m.get("north_star"),
            summary=m.get("summary"),
            tags=tags,
            crystal_markdown=None,  # 列表不返回完整 Crystal
            created_at=m["created_at"],
            updated_at=m["updated_at"]
        ))

    return MindListResponse(minds=result)


@router.get("/{mind_id}", response_model=MindResponse)
async def get_mind(mind_id: str, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """获取单个 Mind 详情"""
    mind = db.get_mind(mind_id, user_id=user["id"])

    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    tags = db.get_mind_tags(mind_id)

    return MindResponse(
        id=mind["id"],
        title=mind["title"],
        north_star=mind.get("north_star"),
        summary=mind.get("summary"),
        narrative=mind.get("narrative"),
        tags=tags,
        crystal_markdown=format_crystal_markdown(mind.get("crystal")),
        created_at=mind["created_at"],
        updated_at=mind["updated_at"]
    )


@router.delete("/{mind_id}")
async def delete_mind(mind_id: str, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """删除 Mind 及其所有关联数据"""
    mind = db.get_mind(mind_id, user_id=user["id"])

    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    success = db.delete_mind(mind_id, user_id=user["id"])

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete mind")

    return {"success": True, "message": f"Mind '{mind['title']}' 已删除"}


@router.get("/{mind_id}/crystal", response_model=CrystalResponse)
async def get_crystal(mind_id: str, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """获取 Mind 的结构视图"""
    mind = db.get_mind(mind_id, user_id=user["id"])

    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    crystal = mind.get("crystal")

    return CrystalResponse(
        mind_id=mind_id,
        structure_markdown=format_crystal_markdown(crystal),
        crystal_json=crystal,
        updated_at=mind["updated_at"]
    )


@router.get("/{mind_id}/timeline", response_model=TimelineResponse)
async def get_timeline(mind_id: str, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """获取 Mind 的时间线"""
    mind = db.get_mind(mind_id, user_id=user["id"])

    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    events = db.get_timeline(mind_id)

    return TimelineResponse(
        mind_id=mind_id,
        events=[
            TimelineEvent(
                id=e["id"],
                event_type=e["event_type"],
                summary=e["summary"] or "",
                created_at=e["created_at"]
            )
            for e in events
        ]
    )


@router.get("/{mind_id}/mindmap")
async def get_mindmap(mind_id: str, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """获取Mind的思维导图（从缓存读取）"""
    logger.info(f"[Mindmap API] 请求 mind_id={mind_id}, user_id={user['id']}")

    mind = db.get_mind(mind_id, user_id=user["id"])
    if not mind:
        logger.warning(f"[Mindmap API] Mind not found: {mind_id}")
        raise HTTPException(status_code=404, detail="Mind not found")

    mindmap_cache = mind.get("mindmap_cache")
    logger.info(f"[Mindmap API] mindmap_cache 长度: {len(mindmap_cache) if mindmap_cache else 0}")

    if mindmap_cache:
        mindmap_data = json.loads(mindmap_cache)
        mindmap_data["_has_cache"] = True
        return mindmap_data

    # 如果缓存不存在，返回提示（标记无缓存）
    logger.info(f"[Mindmap API] 无缓存，返回默认值")
    return {
        "name": mind.get("title", "未命名"),
        "children": [],
        "_has_cache": False
    }


@router.post("/{mind_id}/mindmap")
async def generate_mindmap(mind_id: str, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """生成/更新Mind的思维导图"""
    logger.info(f"[Mindmap Generate] 开始生成 mind_id={mind_id}")

    mind = db.get_mind(mind_id, user_id=user["id"])
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    # 获取去噪后的内容
    feeds = db.get_all_cleaned_feeds(mind_id)
    if not feeds:
        return {
            "name": mind.get("title", "未命名"),
            "children": [{"name": "暂无内容，请先投喂想法"}],
            "_has_cache": False
        }

    try:
        # 调用 AI 生成思维导图
        mindmap_data = await generate_mindmap_from_timeline(feeds, mind["title"])

        # 保存到缓存
        db.update_mind_mindmap(mind_id, json.dumps(mindmap_data, ensure_ascii=False))
        logger.info(f"[Mindmap Generate] 生成完成")

        mindmap_data["_has_cache"] = True
        return mindmap_data

    except Exception as e:
        logger.error(f"[Mindmap Generate] 生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 晶体融合 API
# ============================================================

class AbsorbRequest(BaseModel):
    """晶体融合请求"""
    master_mind_id: str  # 主晶体 ID
    slave_mind_id: str   # 附晶体 ID


class SupplementItem(BaseModel):
    """补充内容项"""
    original_time: str
    content: str
    source_title: str


class AbsorbPreviewResponse(BaseModel):
    """融合预览响应"""
    success: bool
    preview: Dict[str, Any]


class AbsorbConfirmRequest(BaseModel):
    """融合确认请求"""
    master_mind_id: str
    slave_mind_id: str
    supplements: List[Dict[str, Any]]


class AbsorbConfirmResponse(BaseModel):
    """融合确认响应"""
    success: bool
    message: str
    feeds_added: int
    slave_deleted: bool


@router.post("/absorb", response_model=AbsorbPreviewResponse)
async def absorb_preview(request: AbsorbRequest, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """
    晶体融合预览 - 提取附晶体独特内容

    不写入数据库，只返回预览数据
    """
    logger.info(f"[Absorb Preview] master={request.master_mind_id}, slave={request.slave_mind_id}")

    # 验证主晶体
    master_mind = db.get_mind(request.master_mind_id, user_id=user["id"])
    if not master_mind:
        raise HTTPException(status_code=404, detail="主晶体不存在")

    # 验证附晶体
    slave_mind = db.get_mind(request.slave_mind_id, user_id=user["id"])
    if not slave_mind:
        raise HTTPException(status_code=404, detail="附晶体不存在")

    # 不能自己融合自己
    if request.master_mind_id == request.slave_mind_id:
        raise HTTPException(status_code=400, detail="不能将晶体融合到自身")

    # 获取两个晶体的时间轴内容
    master_feeds = db.get_all_cleaned_feeds(request.master_mind_id)
    slave_feeds = db.get_all_cleaned_feeds(request.slave_mind_id)

    # 调用 AI 提取独特内容
    try:
        result = await extract_unique_content(
            master_feeds=master_feeds,
            slave_feeds=slave_feeds,
            master_title=master_mind["title"],
            slave_title=slave_mind["title"]
        )

        # 格式化补充内容
        supplements = []
        for item in result.get("supplements", []):
            supplements.append({
                "original_time": item.get("original_time", ""),
                "content": item.get("original_content", ""),
                "source_title": slave_mind["title"]
            })

        return AbsorbPreviewResponse(
            success=True,
            preview={
                "supplements": supplements,
                "supplement_count": len(supplements),
                "reasoning": result.get("reasoning", ""),
                "master_title": master_mind["title"],
                "slave_title": slave_mind["title"],
                "master_mind_id": request.master_mind_id,
                "slave_mind_id": request.slave_mind_id
            }
        )

    except Exception as e:
        logger.error(f"[Absorb Preview] 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/absorb/confirm", response_model=AbsorbConfirmResponse)
async def absorb_confirm(request: AbsorbConfirmRequest, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """
    晶体融合确认 - 执行实际的数据写入和删除
    """
    logger.info(f"[Absorb Confirm] master={request.master_mind_id}, slave={request.slave_mind_id}")

    # 验证主晶体
    master_mind = db.get_mind(request.master_mind_id, user_id=user["id"])
    if not master_mind:
        raise HTTPException(status_code=404, detail="主晶体不存在")

    # 验证附晶体
    slave_mind = db.get_mind(request.slave_mind_id, user_id=user["id"])
    if not slave_mind:
        raise HTTPException(status_code=404, detail="附晶体不存在")

    try:
        feeds_added = 0
        now = datetime.now()

        # 1. 在主晶体当前时刻新增「吞并说明」记录
        system_note = ABSORB_SYSTEM_NOTE_TEMPLATE.format(
            time=now.strftime("%Y-%m-%d %H:%M"),
            slave_title=slave_mind["title"]
        )

        system_feed_id = f"feed_{now.strftime('%Y%m%d%H%M%S%f')}"
        db.add_feed(
            feed_id=system_feed_id,
            mind_id=request.master_mind_id,
            content=system_note
        )
        # 系统说明不需要去噪，直接设置 cleaned_content
        db.update_feed_cleaned(system_feed_id, system_note)

        # 2. 将补充内容按原始时间插入主晶体时间轴
        for i, item in enumerate(request.supplements):
            # 生成新的 feed_id（使用原始时间 + 序号确保唯一）
            original_time = item.get("original_time", "")
            logger.info(f"[Absorb Confirm] 处理第 {i+1} 条，original_time={original_time}")
            # 尝试解析原始时间，如果失败则用当前时间
            try:
                if original_time:
                    # 处理不同的时间格式
                    if "T" in original_time:
                        # ISO 格式：2026-01-02T06:40 或 2026-01-02T06:40:00
                        if len(original_time) == 16:  # "2026-01-02T06:40"
                            feed_time = datetime.strptime(original_time, "%Y-%m-%dT%H:%M")
                        else:
                            feed_time = datetime.fromisoformat(original_time.replace("Z", "+00:00").split("+")[0])
                    elif len(original_time) == 16:  # "2026-01-05 10:30"
                        feed_time = datetime.strptime(original_time, "%Y-%m-%d %H:%M")
                    else:
                        feed_time = datetime.strptime(original_time[:19], "%Y-%m-%d %H:%M:%S")
                    logger.info(f"[Absorb Confirm] 解析成功: {feed_time}")
                else:
                    feed_time = now
            except Exception as e:
                logger.error(f"[Absorb Confirm] 时间解析失败: {original_time}, 错误: {e}")
                feed_time = now

            feed_id = f"feed_{feed_time.strftime('%Y%m%d%H%M%S')}{i:04d}"

            # 标注来源
            source_title = item.get("source_title", slave_mind["title"])
            content_with_source = f"[来自附晶体：{source_title}] {item.get('content', '')}"

            # 添加到主晶体
            db.add_feed_with_time(
                feed_id=feed_id,
                mind_id=request.master_mind_id,
                content=content_with_source,
                created_at=feed_time.isoformat()
            )
            # 已经是整理过的内容，直接设置为 cleaned_content
            db.update_feed_cleaned(feed_id, content_with_source)

            feeds_added += 1

        # 3. 删除附晶体
        db.delete_mind(request.slave_mind_id, user_id=user["id"])

        logger.info(f"[Absorb Confirm] 完成: 添加 {feeds_added} 条记录，删除附晶体")

        return AbsorbConfirmResponse(
            success=True,
            message=f"融合完成！已将「{slave_mind['title']}」的 {feeds_added} 条独特内容补充到「{master_mind['title']}」",
            feeds_added=feeds_added,
            slave_deleted=True
        )

    except Exception as e:
        logger.error(f"[Absorb Confirm] 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
