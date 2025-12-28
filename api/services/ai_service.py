"""
AI 服务 - 调用 AI Hub
"""
import httpx
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

# AI Hub 配置
AI_HUB_URL = "http://localhost:8000"
DEFAULT_MODEL = "google_gemini_3_flash"


async def call_ai(
    messages: list,
    thinking_level: str = "medium",
    max_tokens: int = 4096
) -> str:
    """
    调用 AI Hub

    Args:
        messages: 消息列表，OpenAI 格式
        thinking_level: 思考等级 (minimal/low/medium/high)
        max_tokens: 最大输出 token 数

    Returns:
        AI 回复的文本内容
    """
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{AI_HUB_URL}/run/chat_completion/{DEFAULT_MODEL}",
            json={
                "messages": messages,
                "model_params": {
                    "thinking_level": thinking_level,
                    "max_output_tokens": max_tokens
                }
            }
        )

        if response.status_code != 200:
            logger.error(f"AI Hub 调用失败: {response.status_code} - {response.text}")
            raise Exception(f"AI Hub 调用失败: {response.status_code}")

        data = response.json()

        if data.get("error_message"):
            raise Exception(data["error_message"])

        # 提取回复内容
        choices = data.get("choices", [])
        if choices and choices[0].get("content"):
            return choices[0]["content"]

        raise Exception("AI 没有返回有效内容")


async def organize_feed(
    current_crystal: Optional[str],
    feeds: List[dict],
    mind_title: str
) -> str:
    """
    整理投喂内容，生成/更新 Crystal

    Args:
        current_crystal: 当前的 Crystal（可能为空）
        feeds: 投喂记录列表
        mind_title: Mind 标题

    Returns:
        更新后的 Crystal 内容
    """
    # 构建投喂内容
    feeds_text = "\n".join([
        f"[{f['created_at']}] {f['content']}"
        for f in feeds[-10:]  # 只取最近10条
    ])

    system_prompt = """你是一个专业的想法整理助手。你的任务是：
1. 只聆听和整理，不加入自己的见解
2. 提取核心观点和认知，忽略牢骚、啰嗦、重复
3. 新的认知默认覆盖旧的
4. 保持内容清晰、准确、简洁

输出格式：
## 核心目标
[一句话描述]

## 当前认知
- 要点1
- 要点2
...

## 待解决问题（如有）
- ?

## 关键细节
[重要但不适合放在核心认知的内容]"""

    if current_crystal:
        user_prompt = f"""主题：{mind_title}

当前总览：
{current_crystal}

新增投喂：
{feeds_text}

请整合新增内容，更新总览。保持简洁清晰。"""
    else:
        user_prompt = f"""主题：{mind_title}

投喂内容：
{feeds_text}

请根据以上内容，生成初始总览。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    return await call_ai(messages, thinking_level="medium")


async def generate_output(
    crystal: str,
    instruction: str,
    mind_title: str
) -> str:
    """
    根据指令生成输出

    Args:
        crystal: 当前 Crystal 内容
        instruction: 用户指令（如"写一段给程序员的说明"）
        mind_title: Mind 标题

    Returns:
        生成的输出内容
    """
    system_prompt = """你是一个专业的表达助手。你的任务是：
1. 根据用户的指令，将想法内容转化为合适的表达
2. 忠于原始内容，不添加未提供的信息
3. 根据目标受众调整风格和语气
4. 可以调整长度和详细程度"""

    user_prompt = f"""主题：{mind_title}

想法内容：
{crystal}

输出指令：{instruction}

请根据指令生成合适的表达。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    return await call_ai(messages, thinking_level="medium")
