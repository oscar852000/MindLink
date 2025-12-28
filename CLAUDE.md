# MindLink - Claude Code 开发指南

> 本文档供 Claude Code 自动读取，包含项目定位、开发规范和重要注意事项。

---

## 项目定位

**MindLink 是一个 AI 驱动的想法整理助手**，帮助用户将零散的想法持续整理成清醒的认知。

### 核心理念

> 一个只会聆听、整理、表达的超能力助手——不加见解，只让你的想法保持清醒。

### 两大核心功能

| 功能 | 说明 |
|------|------|
| **整理** | 用户不断投喂想法 → AI 持续归纳更新 → 想法始终"活着" |
| **输出** | 一个想法 → 多种表达（给投资人/程序员/朋友） |

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
│   ├── routes/            # 路由模块
│   ├── services/          # 业务逻辑层
│   └── models/            # 数据模型
├── web/                    # 前端静态文件
│   ├── index.html
│   └── static/
│       ├── css/
│       └── js/
├── data/                   # 数据存储 (不提交到 Git)
├── logs/                   # 日志 (不提交到 Git)
├── config/                 # 配置
├── scripts/                # 启动脚本
└── docs/                   # 文档
```

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
| [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md) | 产品说明文档 |
| [docs/ORIGINAL_VISION.md](docs/ORIGINAL_VISION.md) | 用户原始想法 |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | API 接口文档 |

---

## 服务管理

```bash
# 启动开发模式
cd /root/MindLink
source venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 7003

# 生产模式
bash scripts/start.sh
```

---

## ⚠️ 重要警告

1. **绝对不修改 /root/ai_hub 的任何代码**
2. MindLink 只是 AI Hub 的调用方
3. 修改核心文件前先 `git commit` 当前状态

---

**文档版本**: v1.0
**最后更新**: 2024-12-28
