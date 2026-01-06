"""
Memory 路由 - 晶体底层记忆管理
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from api.services.db_service import db
from api.auth import get_current_user_flexible

logger = logging.getLogger(__name__)

router = APIRouter()


class MemoryItem(BaseModel):
    """记忆条目"""
    id: int
    key: str
    definition: str
    category: str
    aliases: List[str] = []
    source_mind_id: Optional[str] = None
    version: int
    created_at: str
    updated_at: str


class MemoryListResponse(BaseModel):
    """记忆列表响应"""
    memories: List[MemoryItem]
    count: int


class MemoryUpdateRequest(BaseModel):
    """更新记忆请求"""
    definition: str
    category: Optional[str] = "general"
    aliases: Optional[List[str]] = []


class MemoryCreateRequest(BaseModel):
    """创建记忆请求"""
    key: str
    definition: str
    category: Optional[str] = "general"
    aliases: Optional[List[str]] = []


@router.get("/memory")
async def list_memories(user: Dict[str, Any] = Depends(get_current_user_flexible)) -> MemoryListResponse:
    """获取用户的所有晶体底层记忆"""
    memories = db.get_all_base_memory(user["id"])
    return MemoryListResponse(
        memories=[MemoryItem(**m) for m in memories],
        count=len(memories)
    )


@router.get("/memory/{key}")
async def get_memory(key: str, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """根据 key 获取单条记忆"""
    memory = db.get_base_memory_by_key(user["id"], key)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return MemoryItem(**memory)


@router.post("/memory")
async def create_memory(
    request: MemoryCreateRequest,
    user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """手动创建记忆条目"""
    result = db.upsert_base_memory(
        user_id=user["id"],
        key=request.key,
        definition=request.definition,
        category=request.category,
        aliases=request.aliases
    )
    return result


@router.put("/memory/{key}")
async def update_memory(
    key: str,
    request: MemoryUpdateRequest,
    user: Dict[str, Any] = Depends(get_current_user_flexible)
):
    """更新记忆条目"""
    existing = db.get_base_memory_by_key(user["id"], key)
    if not existing:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    result = db.upsert_base_memory(
        user_id=user["id"],
        key=key,
        definition=request.definition,
        category=request.category,
        aliases=request.aliases
    )
    return result


@router.delete("/memory/{key}")
async def delete_memory(key: str, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """删除记忆条目"""
    success = db.delete_base_memory(user["id"], key)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "deleted", "key": key}
