"""
Chat 服务 - AI 对话功能

所有提示词定义在 api/prompts.py，此文件只包含对话业务逻辑。
"""
import logging
from typing import List, Dict, Any

from api.config import AVAILABLE_MODELS, AVAILABLE_STYLES
from api.prompts import get_prompt
from api.services.db_service import db
from api.services.ai_service import call_ai, format_crystal_markdown

logger = logging.getLogger(__name__)


# ============================================================
# 公开接口
# ============================================================

def get_available_models() -> List[Dict[str, Any]]:
    """获取可用模型列表"""
    return [
        {"id": m["id"], "name": m["name"], "description": m["description"]}
        for m in AVAILABLE_MODELS
    ]


def get_available_styles() -> List[Dict[str, Any]]:
    """获取可用风格列表"""
    return [
        {"id": s["id"], "name": s["name"], "description": s["description"]}
        for s in AVAILABLE_STYLES
    ]


# ============================================================
# 内部函数
# ============================================================

def _build_system_prompt(mind: Dict[str, Any], style: str, memory_context: str = "") -> str:
    """构建系统提示词"""
    mind_id = mind["id"]
    mind_title = mind["title"]

    # 获取 Crystal 结构
    crystal = mind.get("crystal")
    crystal_summary = format_crystal_markdown(crystal) if crystal else "暂无结构化认知"

    # 获取时间轴内容
    cleaned_feeds = db.get_all_cleaned_feeds(mind_id)
    if cleaned_feeds:
        timeline_content = "\n".join([
            f"- [{f['created_at'][:16]}] {f['cleaned_content']}"
            for f in cleaned_feeds[-100:]  # 最近100条
        ])
    else:
        timeline_content = "暂无记录"

    # 组装基础提示词（填充变量）
    base_prompt = get_prompt("chat_base").format(
        mind_title=mind_title,
        crystal_summary=crystal_summary,
        timeline_content=timeline_content
    )

    # 获取风格提示词
    style_config = next((s for s in AVAILABLE_STYLES if s["id"] == style), AVAILABLE_STYLES[0])
    style_prompt = get_prompt(style_config["prompt_key"])

    # 注入记忆上下文（如果有）
    if memory_context:
        return f"{base_prompt}\n\n{memory_context}\n\n{style_prompt}"
    
    return f"{base_prompt}\n\n{style_prompt}"


# ============================================================
# 对话功能
# ============================================================

async def chat_with_mind(
    mind_id: str,
    mind: Dict[str, Any],
    message: str,
    history: List[Dict[str, str]],
    user_id: int,
    model: str = "google_gemini_3_flash",
    style: str = "default"
) -> str:
    """
    与 Mind 进行对话

    Args:
        mind_id: Mind ID
        mind: Mind 数据
        message: 用户消息
        history: 历史对话记录
        user_id: 用户 ID（用于获取记忆）
        model: 模型 ID
        style: 对话风格

    Returns:
        AI 回复内容
    """
    # 获取晶体内容用于匹配记忆
    cleaned_feeds = db.get_all_cleaned_feeds(mind_id)
    crystal_content = "\n".join([
        f.get('cleaned_content', '') for f in cleaned_feeds if f.get('cleaned_content')
    ])
    
    # 匹配相关记忆并格式化
    matched_memories = db.match_memories_by_content(user_id, crystal_content)
    memory_context = db.format_matched_memories(matched_memories)
    
    if matched_memories:
        logger.info(f"对话注入 {len(matched_memories)} 条相关记忆")

    # 构建系统提示词（包含记忆上下文）
    system_prompt = _build_system_prompt(mind, style, memory_context)

    # 构建消息列表
    messages = [{"role": "system", "content": system_prompt}]

    # 添加历史消息
    for msg in history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # 添加当前消息
    messages.append({"role": "user", "content": message})

    # 获取模型配置
    model_config = next((m for m in AVAILABLE_MODELS if m["id"] == model), AVAILABLE_MODELS[0])

    # 确定 thinking_level
    thinking_level = model_config.get("thinking_level")

    # 调用 AI（复用 ai_service.call_ai）
    return await call_ai(
        messages=messages,
        thinking_level=thinking_level,
        max_tokens=15000,
        model=model
    )
