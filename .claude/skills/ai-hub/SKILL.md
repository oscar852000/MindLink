---
name: ai-hub
description: AI Hub 调用规范。当任务涉及 AI 模型调用、ai_service.py、或需要新增 AI 功能时自动加载。
---

# AI Hub 调用规范

**文档维护声明**：本文档可以修改。如果发现内容与实际不符、过时、或有错误，必须修改。但保持精简，避免臃肿。

## 核心约束

```
⚠️ 绝对不修改 /root/ai_hub 的任何代码
   MindLink 只是 AI Hub 的调用方
```

---

## 服务信息

| 项目 | 值 |
|------|-----|
| 服务地址 | `http://localhost:8000` |
| 推荐模型 | `google_gemini_3_flash` |
| 配置位置 | `api/config.py` |

---

## 调用示例

```python
import httpx
from api.config import AI_HUB_URL, DEFAULT_MODEL

async def call_ai(messages: list, thinking_level: str = "medium"):
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{AI_HUB_URL}/run/chat_completion/{DEFAULT_MODEL}",
            json={
                "messages": messages,
                "model_params": {
                    "thinking_level": thinking_level,
                    "max_output_tokens": 4096
                }
            }
        )
        return response.json()
```

---

## thinking_level 选择

| 级别 | 适用场景 |
|------|----------|
| `minimal` | 简单确认、快速响应 |
| `low` | 轻量整理 |
| `medium` | 标准整理任务（推荐） |
| `high` | 深度分析、复杂输出 |

---

## 可用模型

在 `api/config.py` 的 `AVAILABLE_MODELS` 中定义：

```python
AVAILABLE_MODELS = [
    {"id": "google_gemini_3_flash", "name": "Gemini 3 Flash"},
    # ... 其他模型
]
```

---

## 现有 AI 服务函数

所有 AI 调用都在 `api/services/ai_service.py`：

| 函数 | 用途 |
|------|------|
| `call_ai()` | 底层调用封装 |
| `clean_and_update_structure()` | 去噪 + 更新 Crystal |
| `generate_narrative_with_meta()` | 生成叙事 |
| `generate_output()` | 按指令生成表达 |
| `generate_mindmap_from_timeline()` | 生成思维导图 |

---

## 新增 AI 功能的正确流程

1. 在 `api/prompts.py` 添加提示词定义
2. 在 `api/services/ai_service.py` 添加调用函数
3. 在路由层调用服务函数
4. **不要**：绕过 ai_service 直接调用 AI Hub
