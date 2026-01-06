"""
Chat 路由 - AI 对话功能
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from api.services.db_service import db
from api.services.chat_service import (
    chat_with_mind,
    get_available_models,
    get_available_styles
)
from api.auth import get_current_user_flexible

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    """对话消息"""
    role: str  # "user" 或 "assistant"
    content: str


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    model: str = "google_gemini_3_flash"
    style: str = "default"


class ChatResponse(BaseModel):
    """对话响应"""
    reply: str
    model_used: str


class ChatHistoryResponse(BaseModel):
    """对话历史响应"""
    messages: List[Dict[str, Any]]


class ClearHistoryResponse(BaseModel):
    """清空历史响应"""
    deleted_count: int


class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    name: str
    description: str


class ModelsResponse(BaseModel):
    """模型列表响应"""
    models: List[ModelInfo]


class StyleInfo(BaseModel):
    """风格信息"""
    id: str
    name: str
    description: str


class StylesResponse(BaseModel):
    """风格列表响应"""
    styles: List[StyleInfo]


@router.post("/minds/{mind_id}/chat", response_model=ChatResponse)
async def send_chat_message(mind_id: str, request: ChatRequest,
                            user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """发送对话消息"""
    mind = db.get_mind(mind_id, user_id=user["id"])
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    try:
        # 从数据库获取历史记录
        history_records = db.get_chat_history(mind_id)
        history = [{"role": r["role"], "content": r["content"]} for r in history_records]

        # 保存用户消息到数据库
        db.add_chat_message(mind_id, "user", request.message, request.model, request.style)

        # 调用对话服务
        reply = await chat_with_mind(
            mind_id=mind_id,
            mind=mind,
            message=request.message,
            history=history,
            user_id=user["id"],
            model=request.model,
            style=request.style
        )

        # 保存 AI 回复到数据库
        db.add_chat_message(mind_id, "assistant", reply, request.model, request.style)

        return ChatResponse(
            reply=reply,
            model_used=request.model
        )

    except Exception as e:
        logger.error(f"对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/minds/{mind_id}/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(mind_id: str, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """获取对话历史"""
    mind = db.get_mind(mind_id, user_id=user["id"])
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    messages = db.get_chat_history(mind_id)
    return ChatHistoryResponse(messages=messages)


@router.delete("/minds/{mind_id}/chat/history", response_model=ClearHistoryResponse)
async def clear_chat_history(mind_id: str, user: Dict[str, Any] = Depends(get_current_user_flexible)):
    """清空对话历史"""
    mind = db.get_mind(mind_id, user_id=user["id"])
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    deleted_count = db.clear_chat_history(mind_id)
    return ClearHistoryResponse(deleted_count=deleted_count)


@router.get("/chat/models", response_model=ModelsResponse)
async def list_chat_models():
    """获取可用的对话模型"""
    models = get_available_models()
    return ModelsResponse(models=[
        ModelInfo(id=m["id"], name=m["name"], description=m["description"])
        for m in models
    ])


@router.get("/chat/styles", response_model=StylesResponse)
async def list_chat_styles():
    """获取可用的对话风格"""
    styles = get_available_styles()
    return StylesResponse(styles=[
        StyleInfo(id=s["id"], name=s["name"], description=s["description"])
        for s in styles
    ])
