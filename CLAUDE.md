# MindLink - Claude Code 开发指南

> 本文档供 Claude Code 自动读取，包含项目定位、开发规范和重要注意事项。

---

## 项目定位

**MindLink 是一个 AI 驱动的想法整理助手**，帮助用户将零散的想法持续整理成清醒的认知。

### 产品口号

> **MindLink：把想法变成可演化的记忆单元，把单元连接成你的第二大脑神经网络。**
>
> 你负责灵感与洞察，AI 负责清醒与表达。

### 哲学内核

MindLink 的目标不是记录生活，而是维持思想的"持续清醒"。

- **Mind = 可持续演化的"记忆晶体"** - 一个想法的状态机存档
- **MindLink = 晶体之间的"语义/因果/依赖连接"** - 未来可形成神经网络
- **人类负责**：直觉、审美、洞察、非线性跳跃（创意那部分）
- **AI 负责**：结构化、归纳、追溯、表达、连接（逻辑整顿那部分）

这是一个"脑机接口 / 大脑外挂"的实现载体：可迭代的档案 + 可追溯的演变 + 可按目的输出。

### 核心理念

> 一个只会聆听、整理、表达的超能力助手——不加见解，只让你的想法保持清醒。

### 产品原则（系统铁律）

1. **AI 是编辑器，不是作者** - 不妄做事实、不加个人观点
2. **一个 Mind = 一个核心话题** - 保持唯一性与清醒度
3. **时间覆盖权重** - 新认知更重要，但历史可追溯
4. **确认机制慎用** - 仅在冲突时触发，避免破坏自动化手感

### 两大核心功能

| 功能 | 说明 |
|------|------|
| **整理（Crystallize）** | 用户投喂 → AI 归纳更新 → 想法保持"清醒" |
| **输出（Express）** | 一个想法 → 多种表达（投资人/程序员/朋友） |

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    MindLink (本项目)                         │
│   前端 (web/) → API (api/) → AI Hub 调用                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓ HTTP API (localhost:8000)
┌─────────────────────────────────────────────────────────────┐
│                    AI Hub (/root/ai_hub)                    │
│            ⚠️ 只调用，绝对不修改 ai_hub 代码                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
                    ┌─────────────┐
                    │ Gemini 3    │
                    │ Flash       │
                    └─────────────┘
```

---

## 目录结构

```
/root/MindLink/
├── api/                    # 后端 API
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # 统一配置（AI Hub、模型、Crystal 模板）
│   ├── routes/            # 路由模块
│   │   ├── mind.py        # Mind CRUD
│   │   ├── feed.py        # 投喂、输出、时间轴、澄清、导图
│   │   ├── chat.py        # AI 对话
│   │   └── admin.py       # 提示词管理
│   └── services/          # 业务逻辑层
│       ├── ai_service.py  # AI 调用（整理、输出、导图等）
│       ├── chat_service.py # 对话服务
│       └── db_service.py  # 数据库操作
├── web/                    # 前端静态文件
│   ├── index.html
│   ├── admin.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── data/                   # 数据存储 (不提交到 Git)
├── logs/                   # 日志 (不提交到 Git)
└── docs/                   # 文档
```

---

## 代码架构规范

### 三层架构

```
┌─────────────────────────────────────────┐
│           路由层 (api/routes/)           │
│   接收请求、参数验证、返回响应            │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│          服务层 (api/services/)          │
│   业务逻辑、AI 调用、数据处理             │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│          数据层 (db_service.py)          │
│   数据库操作、数据持久化                  │
└─────────────────────────────────────────┘
```

### 配置统一管理

所有配置集中在 `api/config.py`：

| 配置项 | 说明 |
|--------|------|
| `AI_HUB_URL` | AI Hub 服务地址 |
| `DEFAULT_MODEL` | 默认 AI 模型 |
| `AVAILABLE_MODELS` | 可用模型列表 |
| `AVAILABLE_STYLES` | 对话风格列表 |
| `CRYSTAL_TEMPLATE` | Crystal 结构模板 |

### Crystal 字段规范

**统一使用以下字段名：**

```python
{
    "core_goal": "",           # 核心目标（一句话）
    "current_knowledge": [],   # 当前认知（要点列表）
    "highlights": [],          # 亮点创意（细节池）
    "pending_notes": [],       # 待定事项（陈述句，非问句）
    "evolution": [],           # 演变记录
}
```

⚠️ **注意**：不要使用 `pending_questions`，统一使用 `pending_notes`

### AI 服务函数说明

| 函数 | 用途 | 提示词 Key |
|------|------|-----------|
| `clean_and_update_structure()` | 去噪 + 更新结构 | `cleaner` |
| `generate_narrative()` | 生成叙事视图 | `narrative` |
| `generate_output()` | 按指令生成表达 | `expresser` |
| `generate_mindmap()` | 生成思维导图 | `mindmapper` |
| `generate_clarification_questions()` | 生成澄清问题 | `clarifier` |

---

## 开发禁忌

### ❌ 禁止打补丁式开发

| 反模式 | 正确做法 |
|--------|----------|
| 保留废弃代码"以防万一" | 直接删除，Git 有历史记录 |
| 添加兼容旧字段名的代码 | 统一迁移到新字段名 |
| 复制粘贴配置到多个文件 | 集中到 `config.py` |
| 添加 `# TODO: 以后删除` | 立即处理或创建 Issue |

### ❌ 禁止重复定义

- 配置项必须在 `config.py` 统一定义
- 不要在多个文件中重复定义 `AI_HUB_URL`、`AVAILABLE_MODELS` 等

### ✅ 正确做法

```python
# 正确：从统一配置导入
from api.config import AI_HUB_URL, DEFAULT_MODEL

# 错误：在每个文件重复定义
AI_HUB_URL = "http://localhost:8000"  # ❌ 不要这样做
```

---

## 核心数据模型

| 对象 | 定义 |
|------|------|
| **Mind** | 一个想法档案（标题 + 核心目标） |
| **FeedItem** | 用户投喂的原始片段 |
| **Crystal** | Mind 的结构化清醒档案 |
| **Timeline** | 事件时间线 |

### Crystal 结构

```markdown
## 核心目标
[一句话，保持焦点]

## 当前认知
- 要点1
- 要点2

## 亮点创意
[细节池]

## 待确认/待解决
[模糊点]

## 演变记录
[版本化变更摘要]
```

---

## 整理器（Organizer）规则

| 动作 | 说明 | 是否需确认 |
|------|------|-----------|
| **Add** | 新增观点/信息 | 否 |
| **Refine** | 优化表达（不改变原意） | 否 |
| **Conflict** | 与旧认知互斥 | 是 |
| **Obsolete** | 过期内容 | 是 |

**噪声处理**：
- 忽略：牢骚、啰嗦、重复、跑题
- 记录：观点、认知、亮点创意

---

## AI Hub 调用规范

### 服务地址
```
http://localhost:8000
```

### 推荐模型
```
adapter_id: google_gemini_3_flash
```

### 调用示例

```python
import httpx

AI_HUB_URL = "http://localhost:8000"

async def call_ai(messages: list, thinking_level: str = "medium"):
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{AI_HUB_URL}/run/chat_completion/google_gemini_3_flash",
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

### thinking_level 选择

| 级别 | 适用场景 |
|------|----------|
| `minimal` | 简单确认、快速响应 |
| `low` | 轻量整理 |
| `medium` | 标准整理任务（推荐） |
| `high` | 深度分析、复杂输出 |

---

## 开发规范

### 1. 版本控制（强制）

**必须使用 Git 管理代码，禁止创建 .bak 备份文件！**

```bash
# 修改前：先提交当前状态
git add -A && git commit -m "备份：修改xxx前"

# 修改后：提交变更
git add -A && git commit -m "feat: 描述改动"
git push
```

**提交信息规范：**

| 前缀 | 用途 |
|------|------|
| `feat:` | 新功能 |
| `fix:` | Bug 修复 |
| `docs:` | 文档更新 |
| `refactor:` | 代码重构 |
| `chore:` | 杂项（配置等） |

### 2. 代码规范

- 使用 Python 3.8+
- 使用 FastAPI 框架
- 使用 httpx 调用 AI Hub
- 遵循 PEP 8 代码风格

### 3. 文档维护

| 规则 | 说明 |
|------|------|
| **迭代式更新** | 修改现有内容，而非不断追加 |
| **及时清理** | 确认无价值的旧信息应删除 |
| **同步更新** | 代码改动后同步更新相关文档 |

---

## 敏感文件警告

以下文件**绝对不能提交到 Git**：

| 文件/目录 | 内容 |
|-----------|------|
| `.env` | 环境变量 |
| `data/` | 运行时数据 |
| `logs/` | 日志文件 |

---

## 关键文档索引

| 文档 | 用途 |
|------|------|
| [docs/ORIGINAL_VISION.md](docs/ORIGINAL_VISION.md) | 产品初心（锚点） |
| [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md) | 产品规格文档 |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | API 接口文档 |

---

## 服务管理

```bash
# 查看状态
systemctl status mindlink

# 重启
systemctl restart mindlink

# 查看日志
journalctl -u mindlink -f

# 开发模式
cd /root/MindLink
source venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 7003
```

---

## ⚠️ 重要警告

1. **绝对不修改 /root/ai_hub 的任何代码**
2. MindLink 只是 AI Hub 的调用方
3. 修改核心文件前先 `git commit` 当前状态
4. 任何迭代都应回溯 ORIGINAL_VISION.md 确保不偏离初心

---

**文档版本**: v1.2
**最后更新**: 2025-12-29
