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
    crystal_markdown: Optional[str] = None
    created_at: str
    updated_at: str


class MindListResponse(BaseModel):
    """Mind 列表响应"""
    minds: List[MindResponse]


class CrystalResponse(BaseModel):
    """Crystal 响应"""
    mind_id: str
    crystal_markdown: str
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
        crystal_markdown=format_crystal_markdown(mind.get("crystal")),
        created_at=mind["created_at"],
        updated_at=mind["updated_at"]
    )


@router.get("", response_model=MindListResponse)
async def list_minds():
    """获取所有 Mind 列表"""
    minds = db.list_minds()

    return MindListResponse(minds=[
        MindResponse(
            id=m["id"],
            title=m["title"],
            north_star=m.get("north_star"),
            crystal_markdown=None,  # 列表不返回完整 Crystal
            created_at=m["created_at"],
            updated_at=m["updated_at"]
        )
        for m in minds
    ])


@router.get("/{mind_id}", response_model=MindResponse)
async def get_mind(mind_id: str):
    """获取单个 Mind 详情"""
    mind = db.get_mind(mind_id)

    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    return MindResponse(
        id=mind["id"],
        title=mind["title"],
        north_star=mind.get("north_star"),
        crystal_markdown=format_crystal_markdown(mind.get("crystal")),
        created_at=mind["created_at"],
        updated_at=mind["updated_at"]
    )


@router.get("/{mind_id}/crystal", response_model=CrystalResponse)
async def get_crystal(mind_id: str):
    """获取 Mind 的当前总览（Crystal）"""
    mind = db.get_mind(mind_id)

    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    return CrystalResponse(
        mind_id=mind_id,
        crystal_markdown=format_crystal_markdown(mind.get("crystal")),
        crystal_json=mind.get("crystal"),
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
