"""
Mind 路由 - 管理想法空间
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter()


class MindCreate(BaseModel):
    """创建 Mind 请求"""
    title: str


class MindResponse(BaseModel):
    """Mind 响应"""
    id: str
    title: str
    crystal: Optional[str] = None
    created_at: str
    updated_at: str


class MindListResponse(BaseModel):
    """Mind 列表响应"""
    minds: List[MindResponse]


# 临时存储（后续改为数据库）
_minds_store = {}


@router.post("", response_model=MindResponse)
async def create_mind(request: MindCreate):
    """创建新的 Mind"""
    mind_id = f"mind_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    now = datetime.now().isoformat()

    mind = {
        "id": mind_id,
        "title": request.title,
        "crystal": None,
        "feeds": [],
        "created_at": now,
        "updated_at": now
    }

    _minds_store[mind_id] = mind

    return MindResponse(
        id=mind_id,
        title=request.title,
        crystal=None,
        created_at=now,
        updated_at=now
    )


@router.get("", response_model=MindListResponse)
async def list_minds():
    """获取所有 Mind 列表"""
    minds = [
        MindResponse(
            id=m["id"],
            title=m["title"],
            crystal=m.get("crystal"),
            created_at=m["created_at"],
            updated_at=m["updated_at"]
        )
        for m in _minds_store.values()
    ]
    return MindListResponse(minds=minds)


@router.get("/{mind_id}", response_model=MindResponse)
async def get_mind(mind_id: str):
    """获取单个 Mind 详情"""
    if mind_id not in _minds_store:
        raise HTTPException(status_code=404, detail="Mind not found")

    m = _minds_store[mind_id]
    return MindResponse(
        id=m["id"],
        title=m["title"],
        crystal=m.get("crystal"),
        created_at=m["created_at"],
        updated_at=m["updated_at"]
    )


@router.get("/{mind_id}/crystal")
async def get_crystal(mind_id: str):
    """获取 Mind 的当前总览（Crystal）"""
    if mind_id not in _minds_store:
        raise HTTPException(status_code=404, detail="Mind not found")

    m = _minds_store[mind_id]
    return {
        "mind_id": mind_id,
        "crystal": m.get("crystal"),
        "updated_at": m["updated_at"]
    }
