"""
AI 服务 - 调用 AI Hub 实现整理和输出

所有提示词定义在 api/prompts.py，此文件只包含业务逻辑。
"""
import copy
import httpx
import json
import logging
from typing import Optional, List, Dict, Any, Tuple

from api.config import AI_HUB_URL, DEFAULT_MODEL, CRYSTAL_TEMPLATE, GEMINI_API_KEY
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
    tag_library: List[str],
    existing_memory: str = ""
) -> Dict[str, Any]:
    """
    生成叙事视图，同时更新概述、标签，并提取记忆锚点

    Args:
        cleaned_feeds: 去噪后的投喂列表
        mind_title: Mind 标题
        current_summary: 当前概述（可能为空）
        current_tags: 当前标签列表
        tag_library: 全局标签库
        existing_memory: 现有晶体底层记忆摘要

    Returns:
        {narrative, summary, summary_changed, tags, tags_changed, memory_anchors}
    """
    if not cleaned_feeds:
        return {
            "narrative": "暂无内容",
            "summary": None,
            "summary_changed": False,
            "tags": [],
            "tags_changed": False,
            "memory_anchors": []
        }

    # 获取基础叙事提示词
    base_prompt = get_prompt("narrative_with_meta")
    
    # 获取记忆锚点提示词并注入现有记忆
    memory_prompt = get_prompt("memory_anchor")
    memory_prompt = memory_prompt.replace("{existing_memory}", existing_memory or "（暂无记忆条目）")
    
    # 合并系统提示词
    system_prompt = base_prompt + "\n\n" + memory_prompt

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

请生成叙事，判断是否需要更新概述和标签，并识别可纳入晶体底层记忆的锚点。"""

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
            "tags_changed": data.get("tags_changed", False),
            "memory_anchors": data.get("memory_anchors", [])
        }

    except json.JSONDecodeError as e:
        logger.error(f"叙事 JSON 解析失败: {e}")
        return {
            "narrative": result if result else "生成失败",
            "summary": None,
            "summary_changed": False,
            "tags": [],
            "tags_changed": False,
            "memory_anchors": []
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
    structure: Optional[Dict[str, Any]] = None,
    memory_context: str = ""
) -> str:
    """
    根据指令生成输出（基于去噪内容）

    Args:
        cleaned_feeds: 去噪后的投喂列表
        instruction: 用户指令
        mind_title: Mind 标题
        structure: 结构信息（可选，用于参考）
        memory_context: 匹配的记忆上下文（可选）

    Returns:
        生成的输出内容
    """
    system_prompt = get_prompt("expresser")
    
    # 如果有记忆上下文，追加到系统提示词
    if memory_context:
        system_prompt = system_prompt + "\n\n" + memory_context

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

def _ensure_list(value) -> list:
    """确保值是列表，如果是字符串则转为单元素列表"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(value)]


def format_crystal_markdown(crystal: Dict[str, Any]) -> str:
    """将 Crystal 格式化为 Markdown 结构视图"""
    if not crystal:
        return "还没有内容，先投喂一些想法吧"

    sections = []

    # 核心目标
    if crystal.get("core_goal"):
        sections.append(f"## 核心目标\n{crystal['core_goal']}")

    # 当前认知
    knowledge = _ensure_list(crystal.get("current_knowledge"))
    if knowledge:
        items = "\n".join([f"- {k}" for k in knowledge])
        sections.append(f"## 当前认知\n{items}")

    # 亮点创意
    highlights = _ensure_list(crystal.get("highlights"))
    if highlights:
        items = "\n".join([f"- {h}" for h in highlights])
        sections.append(f"## 亮点创意\n{items}")

    # 待定事项
    pending = _ensure_list(crystal.get("pending_notes"))
    if pending:
        items = "\n".join([f"- {p}" for p in pending])
        sections.append(f"## 待定事项\n{items}")

    # 演变记录
    evolution = _ensure_list(crystal.get("evolution"))
    if evolution:
        items = "\n".join([f"- {e}" for e in evolution[-5:]])  # 只显示最近5条
        sections.append(f"## 演变记录\n{items}")

    return "\n\n".join(sections) if sections else "还没有内容，先投喂一些想法吧"


# ============================================================
# 思维导图生成
# ============================================================

async def generate_mindmap_from_timeline(
    cleaned_feeds: List[Dict[str, Any]],
    mind_title: str
) -> Dict[str, Any]:
    """基于时间轴内容生成思维导图结构"""
    if not cleaned_feeds:
        return {"name": mind_title, "children": [{"name": "暂无内容"}]}

    system_prompt = get_prompt("mindmap")
    timeline_text = "\n\n".join([
        f"【{f['created_at'][:10]}】\n{f['cleaned_content']}"
        for f in cleaned_feeds
    ])

    user_prompt = f"""Mind标题：{mind_title}

时间轴记录：
{timeline_text}

请整理为思维导图。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        result = await call_ai(messages, thinking_level="medium", max_tokens=8000)
        mindmap_data = _parse_json_response(result)
        if "name" not in mindmap_data:
            mindmap_data = {"name": mind_title, "children": [{"name": "生成失败"}]}
        return mindmap_data
    except Exception as e:
        logger.error(f"生成思维导图失败: {e}")
        return {"name": mind_title, "children": [{"name": "生成失败"}]}


# ============================================================
# 语音转文字
# ============================================================

async def _convert_webm_to_mp3(audio_data: bytes) -> bytes:
    """使用 ffmpeg 将音频转换为 mp3"""
    import subprocess
    import tempfile
    import os

    # 使用通用后缀，ffmpeg 会自动检测格式
    with tempfile.NamedTemporaryFile(suffix='.input', delete=False) as input_file:
        input_file.write(audio_data)
        input_path = input_file.name

    mp3_path = input_path.replace('.input', '.mp3')

    try:
        # 使用 ffmpeg 转换（使用绝对路径）
        result = subprocess.run([
            '/usr/bin/ffmpeg', '-y', '-i', input_path,
            '-acodec', 'libmp3lame', '-ar', '16000', '-ac', '1',
            mp3_path
        ], capture_output=True, timeout=30)

        if result.returncode != 0:
            logger.error(f"ffmpeg 转换失败: {result.stderr.decode()}")
            raise Exception("音频格式转换失败")

        with open(mp3_path, 'rb') as f:
            mp3_data = f.read()

        return mp3_data
    finally:
        # 清理临时文件
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(mp3_path):
            os.remove(mp3_path)


async def transcribe_audio(
    audio_data: bytes,
    mime_type: str = "audio/webm",
    language: str = "yue",
    model: str = "plato_gpt_4o_mini_transcribe"
) -> str:
    """
    使用 AI Hub 转录音频

    Args:
        audio_data: 音频二进制数据
        mime_type: 音频格式
        language: 语言代码（yue=粤语, zh=普通话, en=英语）
        model: 转录模型 ID

    Returns:
        转录的文字
    """
    import io

    # 需要转换的格式（OpenAI API 对这些格式支持不稳定）
    need_convert = (
        "audio/webm", "audio/webm;codecs=opus",
        "audio/mp4", "audio/m4a", "audio/ogg"
    )

    if mime_type in need_convert:
        logger.info(f"转换 {mime_type} → mp3")
        audio_data = await _convert_webm_to_mp3(audio_data)
        mime_type = "audio/mp3"

    # 根据 mime_type 确定文件扩展名
    ext_map = {
        "audio/webm": "webm",
        "audio/wav": "wav",
        "audio/mp3": "mp3",
        "audio/mpeg": "mp3",
        "audio/ogg": "ogg",
        "audio/flac": "flac",
    }
    ext = ext_map.get(mime_type, "mp3")
    filename = f"audio.{ext}"

    # 调用 AI Hub 转录 API
    url = f"{AI_HUB_URL}/run/transcribe/{model}"

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            # 使用 multipart/form-data 上传
            files = {"file": (filename, io.BytesIO(audio_data), mime_type)}
            data = {"language": language}

            response = await client.post(url, files=files, data=data)

            if response.status_code != 200:
                logger.error(f"AI Hub 转录错误: {response.status_code} - {response.text}")
                raise Exception(f"转录失败: {response.status_code}")

            result = response.json()

            # 提取文字
            text = result.get("text", "").strip()
            if not text:
                raise Exception("转录结果为空")

            logger.info(f"音频转录成功 [{model}]: {text[:100]}...")
            return text

    except httpx.TimeoutException:
        raise Exception("转录超时，请重试")
    except Exception as e:
        logger.error(f"音频转录失败: {e}")
        raise Exception(f"转录失败: {str(e)}")


# ============================================================
# Gemini 语音转文字
# ============================================================

async def transcribe_audio_gemini(
    audio_data: bytes,
    mime_type: str = "audio/webm",
    language: str = "yue"
) -> str:
    """
    使用 Gemini API 转录音频

    Args:
        audio_data: 音频二进制数据
        mime_type: 音频格式
        language: 语言代码（yue=粤语, zh=普通话, en=英语）

    Returns:
        转录的文字
    """
    import base64

    # 语言提示
    lang_hints = {
        "yue": "粤语/广东话",
        "zh": "普通话/中文",
        "en": "English"
    }
    lang_hint = lang_hints.get(language, "粤语")

    # Base64 编码音频
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')

    # 构建请求
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{
            "parts": [
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": audio_base64
                    }
                },
                {
                    "text": f"请将这段音频转录为文字。语言是{lang_hint}。只输出转录的文字内容，不要添加任何解释或标点符号修正。"
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048
        }
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload)

            if response.status_code != 200:
                logger.error(f"Gemini 转录错误: {response.status_code} - {response.text}")
                raise Exception(f"Gemini API 错误: {response.status_code}")

            result = response.json()

            # 提取文字
            candidates = result.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "").strip()
                    if text:
                        logger.info(f"Gemini 转录成功: {text[:100]}...")
                        return text

            raise Exception("Gemini 转录结果为空")

    except httpx.TimeoutException:
        raise Exception("Gemini 转录超时，请重试")
    except Exception as e:
        logger.error(f"Gemini 转录失败: {e}")
        raise Exception(f"Gemini 转录失败: {str(e)}")
