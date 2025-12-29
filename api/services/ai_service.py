"""
AI 服务 - 调用 AI Hub 实现整理和输出
"""
import copy
import httpx
import json
import logging
from typing import Optional, List, Dict, Any, Tuple

from api.config import AI_HUB_URL, DEFAULT_MODEL, CRYSTAL_TEMPLATE

logger = logging.getLogger(__name__)


def get_prompt(key: str, default: str) -> str:
    """从数据库获取提示词，如果没有则返回默认值"""
    try:
        from api.services.db_service import db
        content = db.get_prompt(key)
        return content if content else default
    except Exception:
        return default


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

# ========== 去噪+结构更新组合器 ==========

CLEANER_SYSTEM_PROMPT = """你是 MindLink 的整理器，负责两个任务：

## 任务1：去噪记录（cleaned_content）
将用户输入去噪后保存，规则：
- 去除：语气词（嗯、那个、就是说）、纯重复内容、冗余表达
- 保留：观点、情绪、细节、比喻、例子、原始措辞
- 整顿：修正用词、简洁表达、理顺逻辑
- 允许大幅压缩，但不丢失原意

## 任务2：更新结构（structure）
根据去噪内容，更新或补充结构字段：
- core_goal: 核心目标（一句话）
- current_knowledge: 当前认知（要点列表）
- highlights: 亮点创意
- pending_notes: 待定事项（陈述句，非问句）
- evolution: 如有重大变化，记录

## 输出格式
```json
{
    "cleaned_content": "去噪后的内容...",
    "structure": {
        "core_goal": "...",
        "current_knowledge": [...],
        "highlights": [...],
        "pending_notes": [...],
        "evolution": [...]
    },
    "summary": "本次整理摘要"
}
```

只返回 JSON。"""


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
    system_prompt = get_prompt("cleaner", CLEANER_SYSTEM_PROMPT)

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
        result = await call_ai(messages, thinking_level="medium", max_tokens=4096)

        # 解析 JSON
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]

        data = json.loads(result.strip())

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
        # 返回原内容和空结构
        return content, current_structure or copy.deepcopy(CRYSTAL_TEMPLATE), "解析失败"

    except Exception as e:
        logger.error(f"去噪失败: {e}")
        raise


# ========== 叙事视图生成器 ==========

NARRATIVE_SYSTEM_PROMPT = """你是 MindLink 的叙事整理器，负责将时间轴上的多条记录整合为一篇连贯的叙事。

## 任务
将用户不同时间的记录，整合为一篇体现思想演变的叙事文档。

## 规则
1. 保留时间感：体现思想的演变、推翻、迭代过程
2. 整顿逻辑：让内容更连贯、易读
3. 可以压缩：在不丢失核心思想的前提下精简
4. 保留情绪：用户的感受也是重要内容

## 输出
直接输出叙事文本，不要 JSON 包装。"""


async def generate_narrative(
    cleaned_feeds: List[Dict[str, Any]],
    mind_title: str
) -> str:
    """
    生成叙事视图（整合所有时间轴内容）

    Args:
        cleaned_feeds: 去噪后的投喂列表 [{cleaned_content, created_at}, ...]
        mind_title: Mind 标题

    Returns:
        叙事文本
    """
    if not cleaned_feeds:
        return "暂无内容"

    system_prompt = get_prompt("narrative", NARRATIVE_SYSTEM_PROMPT)

    # 构建时间轴内容
    timeline_text = "\n\n".join([
        f"【{f['created_at'][:10]}】\n{f['cleaned_content']}"
        for f in cleaned_feeds
    ])

    user_prompt = f"""## Mind 标题
{mind_title}

## 时间轴记录
{timeline_text}

请整合为一篇连贯的叙事，体现思想演变过程。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    return await call_ai(messages, thinking_level="medium", max_tokens=8192)


# ========== 输出器 (Expresser) ==========

EXPRESSER_SYSTEM_PROMPT = """你帮用户把想法转化为不同风格的表达。

## 核心原则
1. **忠于原意** - 只说用户想法里有的内容，不添加
2. **自然流畅** - 像正常人说话，不要官腔、不要套话
3. **适应场景** - 根据受众调整语气，但内容不变

## 风格指南
- 给投资人：简洁有力，突出价值，不啰嗦
- 给程序员：直接说重点，技术语言OK，不用解释基础概念
- 给朋友：口语化，轻松，可以用比喻
- 电梯稿：30秒能说完，一句话抓住核心

## 禁止事项
- ❌ 不要用"首先、其次、最后"这种八股结构
- ❌ 不要用"值得一提的是"、"不可否认"这种套话
- ❌ 不要加用户没说的观点
- ❌ 不要过度修饰，简单直接

## 好的表达示例
❌ "本产品旨在通过人工智能技术赋能用户实现思维的结构化管理"
✓ "帮你把乱七八糟的想法整理清楚"

根据用户的指令，用自然的语言表达他们的想法。"""


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
    # 从数据库获取提示词，如果没有则使用默认值
    system_prompt = get_prompt("expresser", EXPRESSER_SYSTEM_PROMPT)

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

    return await call_ai(messages, thinking_level="medium", max_tokens=4096)


# ========== Crystal 格式化（用于展示） ==========

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


# ========== 思维导图生成器 (MindMapper) ==========

MINDMAPPER_SYSTEM_PROMPT = """你是思维提炼器，负责将用户的想法转化为思维导图结构。

## 核心原则
1. **忠于原意** - 只用用户说过的内容，不添加
2. **高度精炼** - 每个节点不超过12个字
3. **层级清晰** - 最多3层，结构合理

## 提炼规则
- 核心目标 → 中心节点
- 当前认知中相关的内容 → 归类到同一分支
- 亮点创意 → 可作为分支或子节点
- 待确认 → 标记为 pending 类型

## 输出格式
返回 JSON：
{
  "center": "中心主题（来自核心目标）",
  "branches": [
    {
      "label": "分支名（简短）",
      "children": ["子节点1", "子节点2"],
      "type": "normal"
    },
    {
      "label": "待确认的事项",
      "children": [],
      "type": "pending"
    }
  ]
}

## 数量限制
- 分支数：2-6个
- 每个分支的子节点：0-4个
- 总节点数不超过20个

只返回 JSON，不要其他内容。"""


async def generate_mindmap(
    crystal: Dict[str, Any],
    mind_title: str
) -> Dict[str, Any]:
    """
    根据 Crystal 生成思维导图结构

    Args:
        crystal: 当前 Crystal 内容
        mind_title: Mind 标题

    Returns:
        思维导图结构 {center, branches}
    """
    if not crystal or not crystal.get("current_knowledge"):
        return {
            "center": mind_title or "新想法",
            "branches": []
        }

    # 从数据库获取提示词，如果没有则使用默认值
    system_prompt = get_prompt("mindmapper", MINDMAPPER_SYSTEM_PROMPT)

    # 预处理列表为字符串
    knowledge_lines = '\n'.join(['- ' + k for k in crystal.get('current_knowledge', [])])
    highlights_lines = '\n'.join(['- ' + h for h in crystal.get('highlights', [])])
    pending_lines = '\n'.join(['- ' + q for q in crystal.get('pending_notes', [])])

    crystal_text = f"""## 核心目标
{crystal.get('core_goal', '未设定')}

## 当前认知
{knowledge_lines}

## 亮点创意
{highlights_lines}

## 待定事项
{pending_lines}
"""

    user_prompt = f"""## Mind 标题
{mind_title}

## 用户的想法内容
{crystal_text}

请将这些内容提炼为思维导图结构。只返回 JSON。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        result = await call_ai(messages, thinking_level="medium")

        # 处理可能的 markdown 代码块
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]

        mindmap = json.loads(result.strip())

        # 确保结构完整
        if "center" not in mindmap:
            mindmap["center"] = crystal.get("core_goal", mind_title)
        if "branches" not in mindmap:
            mindmap["branches"] = []

        return mindmap

    except json.JSONDecodeError as e:
        logger.error(f"MindMap JSON 解析失败: {e}")
        # 返回基于 Crystal 的简单结构
        return {
            "center": crystal.get("core_goal", mind_title),
            "branches": [
                {"label": "当前认知", "children": crystal.get("current_knowledge", [])[:5], "type": "normal"},
                {"label": "亮点创意", "children": crystal.get("highlights", [])[:3], "type": "normal"}
            ]
        }
    except Exception as e:
        logger.error(f"生成思维导图失败: {e}")
        raise


def mindmap_to_markdown(mindmap: Dict[str, Any]) -> str:
    """将思维导图结构转换为 Markdown（供 Markmap 渲染）"""
    if not mindmap:
        return "# 新想法"

    lines = [f"# {mindmap.get('center', '想法')}"]

    for branch in mindmap.get("branches", []):
        label = branch.get("label", "")
        branch_type = branch.get("type", "normal")

        # pending 类型加问号标记
        if branch_type == "pending":
            lines.append(f"\n## {label} ❓")
        else:
            lines.append(f"\n## {label}")

        for child in branch.get("children", []):
            lines.append(f"- {child}")

    return "\n".join(lines)


# ========== 澄清器 (Clarifier) ==========

CLARIFIER_SYSTEM_PROMPT = """你是记录员，正在帮用户整理想法。

## 核心规则
**默认不问问题。** 只有当你真的不明白用户在说什么时才问。

90% 的情况你应该返回空数组 []，因为：
- 用户说的话大多数是清楚的
- 即使有模糊的地方，也不需要立刻澄清
- "悬而未决"本身就是用户想法的一部分，不需要你追问

## 什么时候可以问（极少数情况）
- 核心目标完全看不懂（不是"细节不清楚"，是"完全不懂在说什么"）
- 两个说法明显矛盾，你不知道以哪个为准

## 什么时候不要问
- 用户已经说清楚的内容（别重复确认）
- 用户标记为"待定"的内容（那是他们还没想好的）
- 细节问题（不重要）
- 你能猜到答案的问题（别装傻）

## 输出格式
返回 JSON 数组。通常是 []。

如果真的需要问（很少）：
[{"question": "简短问题", "context": "", "options": ["是", "不是"]}]

最多1个问题，选项最多2个。"""


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

    # 从数据库获取提示词，如果没有则使用默认值
    system_prompt = get_prompt("clarifier", CLARIFIER_SYSTEM_PROMPT)

    # 预处理列表为字符串
    knowledge_lines = '\n'.join(['- ' + k for k in crystal.get('current_knowledge', [])])
    highlights_lines = '\n'.join(['- ' + h for h in crystal.get('highlights', [])])

    crystal_text = f"""## 核心目标
{crystal.get('core_goal', '未设定')}

## 当前认知
{knowledge_lines}

## 亮点创意
{highlights_lines}
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
        {"role": "system", "content": system_prompt},
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
