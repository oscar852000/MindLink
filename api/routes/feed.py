"""
Feed 路由 - 投喂和输出
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from api.services.ai_service import organize_feed, generate_output
from api.routes.mind import _minds_store

router = APIRouter()


class FeedRequest(BaseModel):
    """投喂请求"""
    content: str


class FeedResponse(BaseModel):
    """投喂响应"""
    status: str
    message: str
    feed_id: str


class OutputRequest(BaseModel):
    """输出请求"""
    instruction: str  # 例如: "写一段给程序员看的需求说明"


class OutputResponse(BaseModel):
    """输出响应"""
    content: str
    mind_id: str


@router.post("/minds/{mind_id}/feed", response_model=FeedResponse)
async def add_feed(mind_id: str, request: FeedRequest):
    """向 Mind 投喂想法"""
    if mind_id not in _minds_store:
        raise HTTPException(status_code=404, detail="Mind not found")

    # 记录投喂
    feed_id = f"feed_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    feed = {
        "id": feed_id,
        "content": request.content,
        "created_at": datetime.now().isoformat()
    }

    mind = _minds_store[mind_id]
    if "feeds" not in mind:
        mind["feeds"] = []
    mind["feeds"].append(feed)

    # 异步整理（当前同步执行，后续可改为异步任务）
    try:
        new_crystal = await organize_feed(
            current_crystal=mind.get("crystal"),
            feeds=mind["feeds"],
            mind_title=mind["title"]
        )
        mind["crystal"] = new_crystal
        mind["updated_at"] = datetime.now().isoformat()
    except Exception as e:
        # 整理失败不影响投喂记录
        pass

    return FeedResponse(
        status="ok",
        message="已记录",
        feed_id=feed_id
    )


@router.post("/minds/{mind_id}/output", response_model=OutputResponse)
async def generate_mind_output(mind_id: str, request: OutputRequest):
    """根据指令生成输出"""
    if mind_id not in _minds_store:
        raise HTTPException(status_code=404, detail="Mind not found")

    mind = _minds_store[mind_id]

    if not mind.get("crystal"):
        raise HTTPException(
            status_code=400,
            detail="Mind 还没有足够的内容，请先投喂一些想法"
        )

    try:
        output = await generate_output(
            crystal=mind["crystal"],
            instruction=request.instruction,
            mind_title=mind["title"]
        )
        return OutputResponse(content=output, mind_id=mind_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
