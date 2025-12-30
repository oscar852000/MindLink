"""
Mind 路由 - 管理想法空间
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from api.services.db_service import db
from api.services.ai_service import format_crystal_markdown

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
async def create_mind(request: MindCreate):
    """创建新的 Mind"""
    mind_id = f"mind_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    mind = db.create_mind(
        mind_id=mind_id,
        title=request.title,
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
async def list_minds():
    """获取所有 Mind 列表"""
    minds = db.list_minds()

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
async def get_mind(mind_id: str):
    """获取单个 Mind 详情"""
    mind = db.get_mind(mind_id)

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
async def delete_mind(mind_id: str):
    """删除 Mind 及其所有关联数据"""
    mind = db.get_mind(mind_id)

    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    success = db.delete_mind(mind_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete mind")

    return {"success": True, "message": f"Mind '{mind['title']}' 已删除"}


@router.get("/{mind_id}/crystal", response_model=CrystalResponse)
async def get_crystal(mind_id: str):
    """获取 Mind 的结构视图"""
    mind = db.get_mind(mind_id)

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
async def get_timeline(mind_id: str):
    """获取 Mind 的时间线"""
    mind = db.get_mind(mind_id)

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
