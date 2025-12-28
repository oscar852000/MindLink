# MindLink

> 一个只会聆听、整理、表达的超能力助手——不加见解，只让你的想法保持清醒。

## 快速开始

```bash
# 1. 进入项目目录
cd /root/MindLink

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动服务
uvicorn api.main:app --reload --host 0.0.0.0 --port 7003
```

访问: https://ml.jibenlizi.net

## 项目结构

```
MindLink/
├── api/                # 后端 API
├── web/                # 前端静态文件
├── data/               # 数据存储
├── logs/               # 日志
├── config/             # 配置
├── scripts/            # 脚本
└── docs/               # 文档
```

## 核心功能

- **投喂**: 输入零散想法
- **整理**: AI 自动归纳更新
- **输出**: 按需求生成不同风格的表达

## 文档

- [产品说明](docs/PRODUCT_SPEC.md)
- [原始想法](docs/ORIGINAL_VISION.md)
- [API 参考](docs/API_REFERENCE.md)

## 技术栈

- 后端: Python + FastAPI
- 前端: HTML + CSS + JavaScript
- AI: Gemini 3 Flash (via AI Hub)

---

**版本**: v0.1.0
