"""
管理路由 - 提示词管理

提示词定义在 api/prompts.py，此文件只负责 API 路由。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from api.services.db_service import db
from api.prompts import PROMPT_REGISTRY, get_prompt

router = APIRouter()


# ============================================================
# 数据模型
# ============================================================

class PromptItem(BaseModel):
    """提示词项"""
    key: str
    name: str
    content: str
    description: Optional[str] = ""
    category: Optional[str] = None
    updated_at: Optional[str] = None


class PromptUpdate(BaseModel):
    """提示词更新请求"""
    content: str


class PromptListResponse(BaseModel):
    """提示词列表响应"""
    prompts: List[PromptItem]


# ============================================================
# API 路由
# ============================================================

@router.get("/prompts", response_model=PromptListResponse)
async def list_prompts():
    """获取所有提示词"""
    # 从数据库获取已存在的提示词
    db_prompts = db.get_all_prompts()
    existing_keys = {p["key"] for p in db_prompts}

    # 确保所有默认提示词都存在（自动添加缺失的）
    for key, meta in PROMPT_REGISTRY.items():
        if key not in existing_keys:
            db.upsert_prompt(
                key=key,
                name=meta["name"],
                content=meta["content"],
                description=meta["description"]
            )

    # 重新获取完整列表
    db_prompts = db.get_all_prompts()

    # 合并元数据
    result = []
    for p in db_prompts:
        meta = PROMPT_REGISTRY.get(p["key"], {})
        result.append(PromptItem(
            key=p["key"],
            name=p["name"],
            content=p["content"],
            description=p.get("description", ""),
            category=meta.get("category"),
            updated_at=p.get("updated_at")
        ))

    return PromptListResponse(prompts=result)


@router.get("/prompts/{key}", response_model=PromptItem)
async def get_prompt_by_key(key: str):
    """获取单个提示词"""
    # 先尝试从数据库获取
    db_prompts = db.get_all_prompts()
    prompt = next((p for p in db_prompts if p["key"] == key), None)

    # 如果没有找到，尝试初始化默认值
    if not prompt and key in PROMPT_REGISTRY:
        meta = PROMPT_REGISTRY[key]
        result = db.upsert_prompt(
            key=key,
            name=meta["name"],
            content=meta["content"],
            description=meta["description"]
        )
        return PromptItem(
            key=result["key"],
            name=result["name"],
            content=result["content"],
            description=result.get("description", ""),
            category=meta.get("category"),
            updated_at=result.get("updated_at")
        )

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    meta = PROMPT_REGISTRY.get(key, {})
    return PromptItem(
        key=prompt["key"],
        name=prompt["name"],
        content=prompt["content"],
        description=prompt.get("description", ""),
        category=meta.get("category"),
        updated_at=prompt.get("updated_at")
    )


@router.put("/prompts/{key}", response_model=PromptItem)
async def update_prompt(key: str, request: PromptUpdate):
    """更新提示词内容"""
    # 获取元数据
    meta = PROMPT_REGISTRY.get(key)
    if not meta:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # 检查是否已存在
    db_prompts = db.get_all_prompts()
    existing = next((p for p in db_prompts if p["key"] == key), None)

    # 更新或创建
    result = db.upsert_prompt(
        key=key,
        name=existing["name"] if existing else meta["name"],
        content=request.content,
        description=existing.get("description", "") if existing else meta["description"]
    )

    return PromptItem(
        key=result["key"],
        name=result["name"],
        content=result["content"],
        description=result.get("description", ""),
        category=meta.get("category"),
        updated_at=result.get("updated_at")
    )


@router.post("/prompts/reset/{key}", response_model=PromptItem)
async def reset_prompt(key: str):
    """重置提示词为默认值"""
    meta = PROMPT_REGISTRY.get(key)
    if not meta:
        raise HTTPException(status_code=404, detail="Prompt not found")

    result = db.upsert_prompt(
        key=key,
        name=meta["name"],
        content=meta["content"],
        description=meta["description"]
    )

    return PromptItem(
        key=result["key"],
        name=result["name"],
        content=result["content"],
        description=result.get("description", ""),
        category=meta.get("category"),
        updated_at=result.get("updated_at")
    )
