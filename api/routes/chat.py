"""
Chat 路由 - AI 对话功能
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from api.services.db_service import db
from api.services.chat_service import (
    chat_with_mind,
    get_available_models,
    get_available_styles
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    """对话消息"""
    role: str  # "user" 或 "assistant"
    content: str


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    history: List[ChatMessage] = []
    model: str = "google_gemini_3_flash"
    style: str = "default"


class ChatResponse(BaseModel):
    """对话响应"""
    reply: str
    model_used: str


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
async def send_chat_message(mind_id: str, request: ChatRequest):
    """发送对话消息"""
    mind = db.get_mind(mind_id)
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    try:
        # 调用对话服务
        reply = await chat_with_mind(
            mind_id=mind_id,
            mind=mind,
            message=request.message,
            history=[msg.model_dump() for msg in request.history],
            model=request.model,
            style=request.style
        )

        return ChatResponse(
            reply=reply,
            model_used=request.model
        )

    except Exception as e:
        logger.error(f"对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
