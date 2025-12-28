"""
Feed 路由 - 投喂和输出
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from api.services.db_service import db
from api.services.ai_service import (
    clean_and_update_structure,
    generate_output,
    generate_clarification_questions,
    generate_mindmap,
    mindmap_to_markdown,
    generate_narrative
)

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
    cleaned_content: Optional[str] = None
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


async def _process_feed(mind_id: str, feed_id: str, content: str):
    """处理投喂：去噪 + 更新结构（后台任务）"""
    try:
        mind = db.get_mind(mind_id)
        if not mind:
            return

        # 调用去噪+结构更新组合器
        cleaned_content, new_structure, summary = await clean_and_update_structure(
            content=content,
            current_structure=mind.get("crystal"),
            mind_title=mind["title"]
        )

        # 保存去噪内容
        db.update_feed_cleaned(feed_id, cleaned_content)

        # 更新结构
        db.update_crystal(mind_id, new_structure, summary)

        logger.info(f"Mind {mind_id} 处理完成: {summary}")

    except Exception as e:
        logger.error(f"处理 Mind {mind_id} 失败: {e}")


@router.post("/minds/{mind_id}/feed", response_model=FeedResponse)
async def add_feed(mind_id: str, request: FeedRequest, background_tasks: BackgroundTasks):
    """向 Mind 投喂想法"""
    mind = db.get_mind(mind_id)
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    # 记录投喂
    feed_id = f"feed_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    db.add_feed(feed_id, mind_id, request.content)

    # 异步处理：去噪 + 更新结构
    background_tasks.add_task(_process_feed, mind_id, feed_id, request.content)

    return FeedResponse(
        status="ok",
        message="已记录，正在处理",
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
            cleaned_content=f.get("cleaned_content"),
            created_at=f["created_at"]
        )
        for f in feeds
    ])


@router.post("/minds/{mind_id}/output", response_model=OutputResponse)
async def generate_mind_output(mind_id: str, request: OutputRequest):
    """根据指令生成输出（基于去噪内容）"""
    mind = db.get_mind(mind_id)
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    # 获取所有去噪后的内容
    cleaned_feeds = db.get_all_cleaned_feeds(mind_id)
    if not cleaned_feeds:
        raise HTTPException(
            status_code=400,
            detail="Mind 还没有足够的内容，请先投喂一些想法"
        )

    try:
        output = await generate_output(
            cleaned_feeds=cleaned_feeds,
            instruction=request.instruction,
            mind_title=mind["title"],
            structure=mind.get("crystal")
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
    """手动触发重新整理（已弃用，保留兼容）"""
    # 新架构下，每次投喂都会自动处理
    # 这个接口保留用于兼容，但实际上不需要再调用
    return {
        "status": "ok",
        "message": "新架构下无需手动整理，每次投喂自动处理"
    }


# ========== 时间轴视图 ==========

class TimelineItem(BaseModel):
    """时间轴项"""
    date: str
    items: List[dict]


class TimelineViewResponse(BaseModel):
    """时间轴视图响应"""
    timeline: List[TimelineItem]


@router.get("/minds/{mind_id}/timeline-view")
async def get_timeline_view(mind_id: str):
    """获取时间轴视图（按日期分组的去噪记录）"""
    mind = db.get_mind(mind_id)
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    feeds = db.get_all_cleaned_feeds(mind_id)

    # 按日期分组
    from collections import defaultdict
    grouped = defaultdict(list)
    for f in feeds:
        date = f["created_at"][:10]  # 取日期部分
        time = f["created_at"][11:16]  # 取时间部分
        grouped[date].append({
            "id": f["id"],
            "time": time,
            "content": f["cleaned_content"]
        })

    # 转换为列表，按日期倒序
    timeline = [
        {"date": date, "items": items}
        for date, items in sorted(grouped.items(), reverse=True)
    ]

    return {"timeline": timeline}


# ========== 叙事视图 ==========

class NarrativeResponse(BaseModel):
    """叙事视图响应"""
    narrative: str
    feed_count: int


@router.post("/minds/{mind_id}/narrative")
async def generate_narrative_view(mind_id: str):
    """生成叙事视图（点击触发）"""
    mind = db.get_mind(mind_id)
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    feeds = db.get_all_cleaned_feeds(mind_id)
    if not feeds:
        return NarrativeResponse(
            narrative="暂无内容，请先投喂一些想法",
            feed_count=0
        )

    try:
        narrative = await generate_narrative(
            cleaned_feeds=feeds,
            mind_title=mind["title"]
        )

        return NarrativeResponse(
            narrative=narrative,
            feed_count=len(feeds)
        )

    except Exception as e:
        logger.error(f"生成叙事视图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 澄清问答 ==========

class ClarifyQuestion(BaseModel):
    """澄清问题"""
    question: str
    context: str
    options: List[str]


class ClarifyResponse(BaseModel):
    """澄清响应"""
    has_questions: bool
    questions: List[ClarifyQuestion]


class AnswerRequest(BaseModel):
    """回答请求"""
    question: str
    answer: str  # 可以是选项内容，也可以是自定义输入


class AnswerResponse(BaseModel):
    """回答响应"""
    status: str
    message: str


@router.post("/minds/{mind_id}/clarify", response_model=ClarifyResponse)
async def get_clarification_questions(mind_id: str):
    """获取 AI 生成的澄清问题"""
    mind = db.get_mind(mind_id)
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    crystal = mind.get("crystal")
    if not crystal or not crystal.get("current_knowledge"):
        return ClarifyResponse(
            has_questions=False,
            questions=[]
        )

    try:
        questions = await generate_clarification_questions(
            crystal=crystal,
            mind_title=mind["title"]
        )

        return ClarifyResponse(
            has_questions=len(questions) > 0,
            questions=[
                ClarifyQuestion(
                    question=q["question"],
                    context=q.get("context", ""),
                    options=q.get("options", [])
                )
                for q in questions
            ]
        )

    except Exception as e:
        logger.error(f"生成澄清问题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/minds/{mind_id}/answer", response_model=AnswerResponse)
async def submit_answer(mind_id: str, request: AnswerRequest, background_tasks: BackgroundTasks):
    """提交澄清问题的答案（自动作为投喂内容）"""
    mind = db.get_mind(mind_id)
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    # 将问答格式化为投喂内容
    content = f"【澄清】{request.question}\n答：{request.answer}"

    # 记录投喂
    feed_id = f"feed_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    db.add_feed(feed_id, mind_id, content)

    # 异步触发整理
    background_tasks.add_task(_organize_mind, mind_id)

    return AnswerResponse(
        status="ok",
        message="已记录答案"
    )


# ========== 思维导图 ==========

class MindmapResponse(BaseModel):
    """思维导图响应"""
    mindmap: dict  # JSON 结构
    markdown: str  # Markmap 渲染用


@router.get("/minds/{mind_id}/mindmap", response_model=MindmapResponse)
async def get_mindmap(mind_id: str):
    """获取思维导图"""
    mind = db.get_mind(mind_id)
    if not mind:
        raise HTTPException(status_code=404, detail="Mind not found")

    crystal = mind.get("crystal")
    if not crystal or not crystal.get("current_knowledge"):
        # 返回空导图
        empty_map = {
            "center": mind.get("title", "新想法"),
            "branches": []
        }
        return MindmapResponse(
            mindmap=empty_map,
            markdown=f"# {mind.get('title', '新想法')}"
        )

    try:
        mindmap = await generate_mindmap(
            crystal=crystal,
            mind_title=mind["title"]
        )

        markdown = mindmap_to_markdown(mindmap)

        return MindmapResponse(
            mindmap=mindmap,
            markdown=markdown
        )

    except Exception as e:
        logger.error(f"生成思维导图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
