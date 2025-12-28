"""
Feed 路由 - 投喂和输出
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from api.services.db_service import db
from api.services.ai_service import organize_feeds, generate_output, format_crystal_markdown

logger = logging.getLogger(__name__)

router = APIRouter()


class FeedRequest(BaseModel):
    """投喂请求"""
    content: str


class FeedResponse(BaseModel):
    """投喂响应"""
    status: str
    message: str
    feed_id: str


class FeedItem(BaseModel):
    """投喂项"""
    id: str
    content: str
    created_at: str


class FeedListResponse(BaseModel):
    """投喂列表响应"""
    feeds: List[FeedItem]


class OutputRequest(BaseModel):
    """输出请求"""
    instruction: str  # 例如: "写一段给程序员看的需求说明"


class OutputResponse(BaseModel):
    """输出响应"""
    content: str
    mind_id: str


async def _organize_mind(mind_id: str):
    """异步整理 Mind（后台任务）"""
    try:
        mind = db.get_mind(mind_id)
        if not mind:
            return

        # 获取最近的投喂
        feeds = db.get_feeds(mind_id, limit=10)
        if not feeds:
            return

        # 反转列表，让旧的在前面
        feeds = list(reversed(feeds))

        # 调用整理器
        new_crystal, summary = await organize_feeds(
            current_crystal=mind.get("crystal"),
            new_feeds=feeds,
            mind_title=mind["title"]
        )

        # 更新数据库
        db.update_crystal(mind_id, new_crystal, summary)
        logger.info(f"Mind {mind_id} 整理完成: {summary}")

    except Exception as e:
        logger.error(f"整理 Mind {mind_id} 失败: {e}")


@router.post("/minds/{mind_id}/feed", response_model=FeedResponse)
async def add_feed(mind_id: str, request: FeedRequest, background_tasks: BackgroundTasks):
    """向 Mind 投喂想法"""
    mind = db.get_mind(mind_id)
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    # 记录投喂
    feed_id = f"feed_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    db.add_feed(feed_id, mind_id, request.content)

    # 异步触发整理
    background_tasks.add_task(_organize_mind, mind_id)

    return FeedResponse(
        status="ok",
        message="已记录",
        feed_id=feed_id
    )


@router.get("/minds/{mind_id}/feeds", response_model=FeedListResponse)
async def get_feeds(mind_id: str, limit: int = 20):
    """获取 Mind 的投喂列表"""
    mind = db.get_mind(mind_id)
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    feeds = db.get_feeds(mind_id, limit)

    return FeedListResponse(feeds=[
        FeedItem(
            id=f["id"],
            content=f["content"],
            created_at=f["created_at"]
        )
        for f in feeds
    ])


@router.post("/minds/{mind_id}/output", response_model=OutputResponse)
async def generate_mind_output(mind_id: str, request: OutputRequest):
    """根据指令生成输出"""
    mind = db.get_mind(mind_id)
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    crystal = mind.get("crystal")
    if not crystal or not crystal.get("current_knowledge"):
        raise HTTPException(
            status_code=400,
            detail="Mind 还没有足够的内容，请先投喂一些想法"
        )

    try:
        output = await generate_output(
            crystal=crystal,
            instruction=request.instruction,
            mind_title=mind["title"]
        )

        # 记录输出
        output_id = f"output_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        db.add_output(output_id, mind_id, request.instruction, output)

        return OutputResponse(content=output, mind_id=mind_id)

    except Exception as e:
        logger.error(f"生成输出失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/minds/{mind_id}/reorganize")
async def reorganize_mind(mind_id: str):
    """手动触发重新整理"""
    mind = db.get_mind(mind_id)
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    feeds = db.get_feeds(mind_id, limit=20)
    if not feeds:
        raise HTTPException(status_code=400, detail="没有投喂内容")

    try:
        feeds = list(reversed(feeds))
        new_crystal, summary = await organize_feeds(
            current_crystal=mind.get("crystal"),
            new_feeds=feeds,
            mind_title=mind["title"]
        )

        db.update_crystal(mind_id, new_crystal, summary)

        return {
            "status": "ok",
            "summary": summary,
            "crystal_markdown": format_crystal_markdown(new_crystal)
        }

    except Exception as e:
        logger.error(f"重新整理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
