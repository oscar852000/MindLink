"""
MindLink 配置文件 - 统一管理所有配置
"""
import os

# ========== AI Hub 配置 ==========
AI_HUB_URL = os.getenv("AI_HUB_URL", "http://localhost:8000")
DEFAULT_MODEL = "google_gemini_3_flash"

# ========== 可用模型列表 ==========
AVAILABLE_MODELS = [
    {
        "id": "google_gemini_3_flash",
        "name": "Gemini 3 Flash",
        "description": "快速响应，适合日常对话",
        "thinking_level": "medium"
    },
    {
        "id": "google_gemini_3_pro",
        "name": "Gemini 3 Pro",
        "description": "深度思考，适合复杂分析",
        "thinking_level": "high"
    },
    {
        "id": "plato_gpt_5_2_chat",
        "name": "GPT-5.2 柏拉图",
        "description": "最强推理能力",
        "thinking_level": None
    }
]

# ========== 对话风格列表 ==========
AVAILABLE_STYLES = [
    {
        "id": "default",
        "name": "理性分析",
        "description": "客观、有条理地分析问题",
        "prompt_key": "chat_style_default"
    },
    {
        "id": "socratic",
        "name": "苏格拉底式",
        "description": "多反问，引导深入思考",
        "prompt_key": "chat_style_socratic"
    },
    {
        "id": "creative",
        "name": "创意发散",
        "description": "联想丰富，开放性强",
        "prompt_key": "chat_style_creative"
    }
]

# ========== Crystal 结构模板 ==========
CRYSTAL_TEMPLATE = {
    "core_goal": "",           # 核心目标（一句话）
    "current_knowledge": [],   # 当前认知（要点列表）
    "highlights": [],          # 亮点创意（细节池）
    "pending_notes": [],       # 待定事项（陈述句，非问句）
    "evolution": [],           # 演变记录
}
