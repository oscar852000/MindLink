"""
AI 服务 - 调用 AI Hub 实现整理和输出

所有提示词定义在 api/prompts.py，此文件只包含业务逻辑。
"""
import copy
import httpx
import json
import logging
from typing import Optional, List, Dict, Any, Tuple

from api.config import AI_HUB_URL, DEFAULT_MODEL, CRYSTAL_TEMPLATE
from api.prompts import get_prompt

logger = logging.getLogger(__name__)


# ============================================================
# AI Hub 调用
# ============================================================

async def call_ai(
    messages: list,
    thinking_level: str = "medium",
    max_tokens: int = 4096,
    model: str = None
) -> str:
    """
    调用 AI Hub

    Args:
        messages: 消息列表，OpenAI 格式
        thinking_level: 思考等级 (minimal/low/medium/high)
        max_tokens: 最大输出 token 数
        model: 模型 ID，默认使用 DEFAULT_MODEL

    Returns:
        AI 回复的文本内容
    """
    model = model or DEFAULT_MODEL

    # 构建请求参数
    model_params = {"max_output_tokens": max_tokens}
    if thinking_level:
        model_params["thinking_level"] = thinking_level

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
            raise Exception(f"AI Hub 调用失败: {response.status_code}")

        data = response.json()

        if data.get("error_message"):
            raise Exception(data["error_message"])

        # 提取回复内容（支持多种返回格式）
        choices = data.get("choices", [])
        if choices:
            choice = choices[0]
            if "content" in choice:
                return choice["content"]
            elif "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]

        if "content" in data:
            return data["content"]

        raise Exception("AI 没有返回有效内容")


def _parse_json_response(result: str) -> dict:
    """解析 AI 返回的 JSON（处理 markdown 代码块）"""
    if "```json" in result:
        result = result.split("```json")[1].split("```")[0]
    elif "```" in result:
        result = result.split("```")[1].split("```")[0]
    return json.loads(result.strip())


# ============================================================
# 去噪 + 结构更新
# ============================================================

async def clean_and_update_structure(
    content: str,
    current_structure: Optional[Dict[str, Any]],
    mind_title: str
) -> Tuple[str, Dict[str, Any], str]:
    """
    去噪并更新结构（一次调用，两个输出）

    Args:
        content: 用户输入的原始内容
        current_structure: 当前结构（可能为空）
        mind_title: Mind 标题

    Returns:
        (去噪后内容, 更新后结构, 摘要)
    """
    system_prompt = get_prompt("cleaner")

    if current_structure and current_structure.get("current_knowledge"):
        user_prompt = f"""## Mind 标题
{mind_title}

## 当前结构
```json
{json.dumps(current_structure, ensure_ascii=False, indent=2)}
```

## 新输入内容
{content}

请去噪并更新结构。"""
    else:
        user_prompt = f"""## Mind 标题
{mind_title}

## 输入内容
{content}

请去噪并生成初始结构。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        result = await call_ai(messages, thinking_level="medium", max_tokens=15000)
        data = _parse_json_response(result)

        cleaned_content = data.get("cleaned_content", content)
        structure = data.get("structure", copy.deepcopy(CRYSTAL_TEMPLATE))
        summary = data.get("summary", "已整理")

        # 确保结构字段完整
        for key in CRYSTAL_TEMPLATE:
            if key not in structure:
                structure[key] = CRYSTAL_TEMPLATE[key]

        return cleaned_content, structure, summary

    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败: {e}")
        return content, current_structure or copy.deepcopy(CRYSTAL_TEMPLATE), "解析失败"

    except Exception as e:
        logger.error(f"去噪失败: {e}")
        raise


# ============================================================
# 叙事视图生成
# ============================================================

async def generate_narrative_with_meta(
    cleaned_feeds: List[Dict[str, Any]],
    mind_title: str,
    current_summary: Optional[str],
    current_tags: List[str],
    tag_library: List[str]
) -> Dict[str, Any]:
    """
    生成叙事视图，同时更新概述和标签

    Args:
        cleaned_feeds: 去噪后的投喂列表
        mind_title: Mind 标题
        current_summary: 当前概述（可能为空）
        current_tags: 当前标签列表
        tag_library: 全局标签库

    Returns:
        {narrative, summary, summary_changed, tags, tags_changed}
    """
    if not cleaned_feeds:
        return {
            "narrative": "暂无内容",
            "summary": None,
            "summary_changed": False,
            "tags": [],
            "tags_changed": False
        }

    system_prompt = get_prompt("narrative_with_meta")

    # 构建时间轴内容
    timeline_text = "\n\n".join([
        f"【{f['created_at'][:10]}】\n{f['cleaned_content']}"
        for f in cleaned_feeds
    ])

    # 构建标签库参考
    tag_library_text = ", ".join(tag_library) if tag_library else "（暂无标签库）"

    user_prompt = f"""## Mind 标题
{mind_title}

## 时间轴记录
{timeline_text}

## 当前概述
{current_summary or "（暂无）"}

## 当前标签
{", ".join(current_tags) if current_tags else "（暂无）"}

## 全局标签库（优先复用）
{tag_library_text}

请生成叙事，并判断是否需要更新概述和标签。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        result = await call_ai(messages, thinking_level="medium", max_tokens=15000)
        data = _parse_json_response(result)

        return {
            "narrative": data.get("narrative", ""),
            "summary": data.get("summary"),
            "summary_changed": data.get("summary_changed", False),
            "tags": data.get("tags", [])[:5],  # 最多5个标签
            "tags_changed": data.get("tags_changed", False)
        }

    except json.JSONDecodeError as e:
        logger.error(f"叙事 JSON 解析失败: {e}")
        return {
            "narrative": result if result else "生成失败",
            "summary": None,
            "summary_changed": False,
            "tags": [],
            "tags_changed": False
        }
    except Exception as e:
        logger.error(f"生成叙事失败: {e}")
        raise


# ============================================================
# 输出器 (Expresser)
# ============================================================

async def generate_output(
    cleaned_feeds: List[Dict[str, Any]],
    instruction: str,
    mind_title: str,
    structure: Optional[Dict[str, Any]] = None
) -> str:
    """
    根据指令生成输出（基于去噪内容）

    Args:
        cleaned_feeds: 去噪后的投喂列表
        instruction: 用户指令
        mind_title: Mind 标题
        structure: 结构信息（可选，用于参考）

    Returns:
        生成的输出内容
    """
    system_prompt = get_prompt("expresser")

    # 构建源材料（使用去噪后的内容）
    if cleaned_feeds:
        source_text = "\n\n".join([
            f"【{f['created_at'][:10]}】\n{f['cleaned_content']}"
            for f in cleaned_feeds if f.get('cleaned_content')
        ])
    else:
        source_text = "暂无内容"

    # 添加结构参考（如果有）
    structure_ref = ""
    if structure and structure.get("core_goal"):
        knowledge_list = '\n'.join(['- ' + k for k in structure.get('current_knowledge', [])])
        structure_ref = f"""

## 核心目标（参考）
{structure.get('core_goal', '')}

## 要点（参考）
{knowledge_list}"""

    user_prompt = f"""## Mind 标题
{mind_title}

## 源材料（去噪后的原始记录）
{source_text}
{structure_ref}

## 输出指令
{instruction}

请根据指令，基于源材料生成合适的表达。保留原意，不要添加用户没说过的内容。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    return await call_ai(messages, thinking_level="medium", max_tokens=15000)


# ============================================================
# Crystal 格式化（用于展示）
# ============================================================

def format_crystal_markdown(crystal: Dict[str, Any]) -> str:
    """将 Crystal 格式化为 Markdown 结构视图"""
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

    # 待定事项
    if crystal.get("pending_notes"):
        items = "\n".join([f"- {p}" for p in crystal["pending_notes"]])
        sections.append(f"## 待定事项\n{items}")

    # 演变记录
    if crystal.get("evolution"):
        items = "\n".join([f"- {e}" for e in crystal["evolution"][-5:]])  # 只显示最近5条
        sections.append(f"## 演变记录\n{items}")

    return "\n\n".join(sections) if sections else "还没有内容，先投喂一些想法吧"
