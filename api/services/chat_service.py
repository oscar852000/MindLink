"""
Chat 服务 - AI 对话功能
"""
import httpx
import logging
from typing import List, Dict, Any, Optional

from api.config import AI_HUB_URL, AVAILABLE_MODELS, AVAILABLE_STYLES
from api.services.db_service import db
from api.services.ai_service import format_crystal_markdown

logger = logging.getLogger(__name__)

# 默认提示词
DEFAULT_PROMPTS = {
    "chat_base": """你是一个智能助手，正在帮助用户深入思考「{mind_title}」这个主题。

## 当前认知概览
{crystal_summary}

## 时间轴记录（用户的原始想法）
{timeline_content}

## 你的角色
1. 你已经完全了解用户关于这个主题的所有想法和记录
2. 基于用户的真实想法进行讨论，帮助他们深化思考
3. 可以提出新视角或补充，但要标注是你的建议
4. 不编造事实，不臆断用户意图
5. 鼓励用户思考，可以适当反问

## 行为准则
- 回复要简洁有力，避免啰嗦
- 引用用户的想法时，要准确
- 如果用户提出的想法与现有认知冲突，温和指出
- 可以帮助用户发现他们想法中的盲点或亮点""",

    "chat_style_default": """## 风格：理性分析
- 客观、有条理地分析问题
- 结构化呈现观点
- 注重逻辑推理""",

    "chat_style_socratic": """## 风格：苏格拉底式
- 多用反问引导思考
- 不直接给答案，而是帮助用户自己发现
- 追问"为什么"和"怎么做"
- 温和但有深度""",

    "chat_style_creative": """## 风格：创意发散
- 联想丰富，开放性强
- 提供意想不到的角度
- 鼓励跳跃性思维
- 用比喻和类比"""
}


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


def _get_prompt(prompt_key: str) -> str:
    """获取提示词（优先从数据库，否则用默认）"""
    prompt = db.get_prompt(prompt_key)
    if prompt and prompt.get("content"):
        return prompt["content"]
    return DEFAULT_PROMPTS.get(prompt_key, "")


def _build_system_prompt(mind: Dict[str, Any], style: str) -> str:
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
            for f in cleaned_feeds[-20:]  # 最近20条
        ])
    else:
        timeline_content = "暂无记录"

    # 组装基础提示词
    base_prompt = _get_prompt("chat_base").format(
        mind_title=mind_title,
        crystal_summary=crystal_summary,
        timeline_content=timeline_content
    )

    # 获取风格提示词
    style_config = next((s for s in AVAILABLE_STYLES if s["id"] == style), AVAILABLE_STYLES[0])
    style_prompt = _get_prompt(style_config["prompt_key"])

    return f"{base_prompt}\n\n{style_prompt}"


async def chat_with_mind(
    mind_id: str,
    mind: Dict[str, Any],
    message: str,
    history: List[Dict[str, str]],
    model: str = "google_gemini_3_flash",
    style: str = "default"
) -> str:
    """与 Mind 进行对话"""

    # 构建系统提示词（每次都重新构建，确保数据最新）
    system_prompt = _build_system_prompt(mind, style)

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

    # 构建请求参数
    model_params = {
        "temperature": 0.7,
        "max_output_tokens": 2048
    }

    # Gemini 模型支持 thinking_level
    if model_config.get("thinking_level"):
        model_params["thinking_level"] = model_config["thinking_level"]

    # 调用 AI Hub
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{AI_HUB_URL}/run/chat_completion/{model}",
            json={
                "messages": messages,
                "model_params": model_params
            }
        )

        if response.status_code != 200:
            logger.error(f"AI Hub 调用失败: {response.status_code} - {response.text}")
            raise Exception(f"AI 服务调用失败: {response.status_code}")

        result = response.json()

        # 提取回复内容（支持多种返回格式）
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            if "content" in choice:
                return choice["content"]
            elif "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]
        elif "message" in result and "content" in result["message"]:
            return result["message"]["content"]
        elif "content" in result:
            return result["content"]

        logger.error(f"AI Hub 返回格式异常: {result}")
        raise Exception("AI 返回格式异常")
