"""
管理路由 - 提示词管理
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from api.services.db_service import db
from api.services.ai_service import (
    CLEANER_SYSTEM_PROMPT,
    EXPRESSER_SYSTEM_PROMPT,
    CLARIFIER_SYSTEM_PROMPT,
    MINDMAPPER_SYSTEM_PROMPT,
    NARRATIVE_SYSTEM_PROMPT
)

router = APIRouter()


# 默认提示词（用于初始化）
DEFAULT_PROMPTS = {
    "cleaner": {
        "name": "整理器",
        "content": CLEANER_SYSTEM_PROMPT,
        "description": "负责去噪并更新 Crystal 结构（每次投喂自动调用）"
    },
    "expresser": {
        "name": "表达器",
        "content": EXPRESSER_SYSTEM_PROMPT,
        "description": "负责将想法转化为不同风格的表达"
    },
    "clarifier": {
        "name": "澄清器",
        "content": CLARIFIER_SYSTEM_PROMPT,
        "description": "负责确认是否正确理解用户想法"
    },
    "mindmapper": {
        "name": "导图器",
        "content": MINDMAPPER_SYSTEM_PROMPT,
        "description": "负责将想法提炼为思维导图结构"
    },
    "narrative": {
        "name": "叙事器",
        "content": NARRATIVE_SYSTEM_PROMPT,
        "description": "负责将时间轴记录整合为连贯叙事"
    }
}


class PromptItem(BaseModel):
    """提示词项"""
    key: str
    name: str
    content: str
    description: Optional[str] = ""
    updated_at: Optional[str] = None


class PromptUpdate(BaseModel):
    """提示词更新请求"""
    content: str


class PromptListResponse(BaseModel):
    """提示词列表响应"""
    prompts: List[PromptItem]


@router.get("/prompts", response_model=PromptListResponse)
async def list_prompts():
    """获取所有提示词"""
    prompts = db.get_all_prompts()

    # 如果数据库没有提示词，初始化默认值
    if not prompts:
        for key, data in DEFAULT_PROMPTS.items():
            db.upsert_prompt(key, data["name"], data["content"], data["description"])
        prompts = db.get_all_prompts()

    return PromptListResponse(prompts=[
        PromptItem(
            key=p["key"],
            name=p["name"],
            content=p["content"],
            description=p.get("description", ""),
            updated_at=p.get("updated_at")
        )
        for p in prompts
    ])


@router.get("/prompts/{key}", response_model=PromptItem)
async def get_prompt(key: str):
    """获取单个提示词"""
    prompts = db.get_all_prompts()

    # 如果没有找到，尝试初始化默认值
    prompt = next((p for p in prompts if p["key"] == key), None)

    if not prompt and key in DEFAULT_PROMPTS:
        data = DEFAULT_PROMPTS[key]
        result = db.upsert_prompt(key, data["name"], data["content"], data["description"])
        return PromptItem(**result)

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    return PromptItem(
        key=prompt["key"],
        name=prompt["name"],
        content=prompt["content"],
        description=prompt.get("description", ""),
        updated_at=prompt.get("updated_at")
    )


@router.put("/prompts/{key}", response_model=PromptItem)
async def update_prompt(key: str, request: PromptUpdate):
    """更新提示词内容"""
    prompts = db.get_all_prompts()
    prompt = next((p for p in prompts if p["key"] == key), None)

    if not prompt and key in DEFAULT_PROMPTS:
        # 使用默认值的名称和描述
        data = DEFAULT_PROMPTS[key]
        result = db.upsert_prompt(key, data["name"], request.content, data["description"])
    elif prompt:
        result = db.upsert_prompt(key, prompt["name"], request.content, prompt.get("description", ""))
    else:
        raise HTTPException(status_code=404, detail="Prompt not found")

    return PromptItem(**result)


@router.post("/prompts/reset/{key}", response_model=PromptItem)
async def reset_prompt(key: str):
    """重置提示词为默认值"""
    if key not in DEFAULT_PROMPTS:
        raise HTTPException(status_code=404, detail="Prompt not found")

    data = DEFAULT_PROMPTS[key]
    result = db.upsert_prompt(key, data["name"], data["content"], data["description"])

    return PromptItem(**result)
