"""
AI 服务 - 调用 AI Hub 实现整理和输出
"""
import httpx
import json
import logging
from typing import Optional, List, Dict, Any, Tuple

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


# ========== Crystal 结构定义 ==========

CRYSTAL_TEMPLATE = {
    "core_goal": "",           # 核心目标（一句话）
    "current_knowledge": [],   # 当前认知（要点列表）
    "highlights": [],          # 亮点创意（细节池）
    "pending_questions": [],   # 待确认/待解决
    "evolution": []            # 演变记录
}


# ========== 整理器 (Organizer) ==========

ORGANIZER_SYSTEM_PROMPT = """你是 MindLink 的整理器（Organizer），负责将用户的投喂内容整理到结构化的 Crystal 中。

## 你的角色
- 你是编辑器，不是作者
- 只聆听和整理，不加入自己的见解
- 基于用户投喂内容进行归纳

## Crystal 结构
Crystal 包含以下字段：
- core_goal: 核心目标（一句话，保持焦点）
- current_knowledge: 当前认知（要点列表，事实/观点/决策）
- highlights: 亮点创意（可强化核心的细节、创意点）
- pending_questions: 待确认（模糊或需要用户澄清的点）
- evolution: 演变记录（每次关键变化的简短摘要）

## 整理规则（四类动作）
1. Add: 新增观点/信息/细节
2. Refine: 同一观点更清晰更准确（不改变原意）
3. Conflict: 与旧认知互斥（标记到 pending_questions）
4. Obsolete: 过期内容（从 current_knowledge 移除，记录到 evolution）

## 噪声处理
- 忽略：牢骚、啰嗦、纯重复、跑题内容（不进入 Crystal）
- 记录：观点、认知、决策、亮点创意

## 时间权重
- 新认知默认覆盖旧认知
- 但要在 evolution 中记录变化

## 输出格式
必须返回有效的 JSON，结构如下：
{
    "core_goal": "一句话核心目标",
    "current_knowledge": ["要点1", "要点2", ...],
    "highlights": ["亮点1", "亮点2", ...],
    "pending_questions": ["问题1", ...],
    "evolution": ["变化记录1", ...],
    "organize_summary": "本次整理的简短摘要"
}

只返回 JSON，不要其他内容。"""


async def organize_feeds(
    current_crystal: Optional[Dict[str, Any]],
    new_feeds: List[Dict[str, Any]],
    mind_title: str
) -> Tuple[Dict[str, Any], str]:
    """
    整理投喂内容到 Crystal

    Args:
        current_crystal: 当前 Crystal（可能为空）
        new_feeds: 新投喂列表
        mind_title: Mind 标题

    Returns:
        (更新后的 Crystal, 整理摘要)
    """
    # 构建投喂内容
    feeds_text = "\n".join([
        f"[{f['created_at']}] {f['content']}"
        for f in new_feeds
    ])

    if current_crystal and current_crystal.get("current_knowledge"):
        user_prompt = f"""## Mind 标题
{mind_title}

## 当前 Crystal
```json
{json.dumps(current_crystal, ensure_ascii=False, indent=2)}
```

## 新增投喂
{feeds_text}

请整合新投喂内容，更新 Crystal。只返回更新后的完整 JSON。"""
    else:
        user_prompt = f"""## Mind 标题
{mind_title}

## 投喂内容
{feeds_text}

请根据投喂内容，生成初始 Crystal。只返回 JSON。"""

    messages = [
        {"role": "system", "content": ORGANIZER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    try:
        result = await call_ai(messages, thinking_level="medium")

        # 尝试解析 JSON
        # 处理可能的 markdown 代码块
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]

        crystal = json.loads(result.strip())

        # 提取摘要
        summary = crystal.pop("organize_summary", "更新 Crystal")

        # 确保所有必要字段存在
        for key in CRYSTAL_TEMPLATE:
            if key not in crystal:
                crystal[key] = CRYSTAL_TEMPLATE[key]

        return crystal, summary

    except json.JSONDecodeError as e:
        logger.error(f"Crystal JSON 解析失败: {e}, 原始内容: {result[:500]}")
        # 返回简单的文本 Crystal
        return {
            "core_goal": mind_title,
            "current_knowledge": [f["content"] for f in new_feeds[:5]],
            "highlights": [],
            "pending_questions": [],
            "evolution": ["初始化（JSON解析失败，使用原始内容）"]
        }, "初始化 Crystal"

    except Exception as e:
        logger.error(f"整理失败: {e}")
        raise


# ========== 输出器 (Expresser) ==========

EXPRESSER_SYSTEM_PROMPT = """你是 MindLink 的表达助手，负责将用户的想法（Crystal）按照指定要求转化为不同风格的表达。

## 你的角色
- 表达助手，忠实传达用户的想法
- 不添加 Crystal 中没有的信息
- 不改变用户的立场和观点

## 输出原则
1. 忠于 Crystal 内容
2. 根据用户指令调整风格和长度
3. 适应目标受众

## 常见输出场景
- 给投资人：商业导向、愿景驱动、精炼有力
- 给程序员：技术细节、结构化、逻辑清晰
- 给朋友：口语化、轻松、易懂
- 电梯稿：30秒能说完、精准有力
- 完整说明：全面详细、有条理

根据用户的指令生成合适的表达。"""


async def generate_output(
    crystal: Dict[str, Any],
    instruction: str,
    mind_title: str
) -> str:
    """
    根据指令生成输出

    Args:
        crystal: 当前 Crystal 内容
        instruction: 用户指令
        mind_title: Mind 标题

    Returns:
        生成的输出内容
    """
    crystal_text = f"""## 核心目标
{crystal.get('core_goal', '未设定')}

## 当前认知
{chr(10).join(['- ' + k for k in crystal.get('current_knowledge', [])])}

## 亮点创意
{chr(10).join(['- ' + h for h in crystal.get('highlights', [])])}
"""

    user_prompt = f"""## Mind 标题
{mind_title}

## 想法内容（Crystal）
{crystal_text}

## 输出指令
{instruction}

请根据指令生成合适的表达。"""

    messages = [
        {"role": "system", "content": EXPRESSER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    return await call_ai(messages, thinking_level="medium")


# ========== Crystal 格式化（用于展示） ==========

def format_crystal_markdown(crystal: Dict[str, Any]) -> str:
    """将 Crystal 格式化为 Markdown 展示"""
    if not crystal:
        return "还没有内容，先投喂一些想法吧"

    sections = []

    # 核心目标
    if crystal.get("core_goal"):
        sections.append(f"## 核心目标\n{crystal['core_goal']}")

    # 当前认知
    if crystal.get("current_knowledge"):
        items = "\n".join([f"- {k}" for k in crystal["current_knowledge"]])
        sections.append(f"## 当前认知\n{items}")

    # 亮点创意
    if crystal.get("highlights"):
        items = "\n".join([f"- {h}" for h in crystal["highlights"]])
        sections.append(f"## 亮点创意\n{items}")

    # 待确认
    if crystal.get("pending_questions"):
        items = "\n".join([f"- {q}" for q in crystal["pending_questions"]])
        sections.append(f"## 待确认/待解决\n{items}")

    # 演变记录
    if crystal.get("evolution"):
        items = "\n".join([f"- {e}" for e in crystal["evolution"][-5:]])  # 只显示最近5条
        sections.append(f"## 演变记录\n{items}")

    return "\n\n".join(sections) if sections else "还没有内容，先投喂一些想法吧"


# ========== 澄清器 (Clarifier) ==========

CLARIFIER_SYSTEM_PROMPT = """你是 MindLink 的澄清助手。

## 核心定位
你的任务是确认自己是否正确**理解**了用户的想法。
你不是来**解决**用户的问题，也不是来**追问答案**的。

用户记录的悬而未决的想法、疑问、矛盾，都是他们思考的一部分。
你只需要确认：我理解对了吗？

## 你应该做的
- 简洁复述你对核心目标的理解，让用户确认
- 确认你对关键概念的理解是否正确
- 问题要短，选项要简单

## 你不应该做的
- ❌ 追问用户悬而未决的问题的答案
- ❌ 试图帮用户做决策
- ❌ 添加自己的分析和解读
- ❌ 用复杂的长句子

## 输出格式
返回 JSON 数组：
[
    {
        "question": "你的核心目标是XXX，对吗？",
        "context": "",
        "options": ["是的", "不对"]
    }
]

规则：
- 最多 2 个问题
- 选项只需要：是的 / 不对 / 部分对
- 想法清晰时，返回空数组 []
- 只返回 JSON"""


async def generate_clarification_questions(
    crystal: Dict[str, Any],
    mind_title: str
) -> List[Dict[str, Any]]:
    """
    分析 Crystal 生成澄清问题

    Args:
        crystal: 当前 Crystal 内容
        mind_title: Mind 标题

    Returns:
        问题列表，每个问题包含 question, context, options
    """
    if not crystal or not crystal.get("current_knowledge"):
        return []

    crystal_text = f"""## 核心目标
{crystal.get('core_goal', '未设定')}

## 当前认知
{chr(10).join(['- ' + k for k in crystal.get('current_knowledge', [])])}

## 亮点创意
{chr(10).join(['- ' + h for h in crystal.get('highlights', [])])}
"""

    user_prompt = f"""## Mind 标题
{mind_title}

## 用户的想法内容
{crystal_text}

请确认你是否正确理解了用户的想法。
- 如果想法已经清晰，返回空数组 []
- 如果有不确定的理解，用简短问题确认
- 不要追问用户还没想好的事情"""

    messages = [
        {"role": "system", "content": CLARIFIER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    try:
        result = await call_ai(messages, thinking_level="medium")

        # 处理可能的 markdown 代码块
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]

        questions = json.loads(result.strip())

        # 确保返回的是列表
        if not isinstance(questions, list):
            return []

        # 验证每个问题的结构
        valid_questions = []
        for q in questions[:3]:  # 最多3个问题
            if isinstance(q, dict) and "question" in q and "options" in q:
                valid_questions.append({
                    "question": q.get("question", ""),
                    "context": q.get("context", ""),
                    "options": q.get("options", [])[:4]  # 最多4个选项
                })

        return valid_questions

    except json.JSONDecodeError as e:
        logger.error(f"澄清问题 JSON 解析失败: {e}")
        return []
    except Exception as e:
        logger.error(f"生成澄清问题失败: {e}")
        raise
