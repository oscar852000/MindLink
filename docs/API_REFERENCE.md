# MindLink API 参考文档

> 本文档描述 MindLink 的 API 接口

---

## 基础信息

- **服务地址**: `https://ml.jibenlizi.net`
- **本地端口**: `7003`

---

## 1. Mind 管理

### 1.1 创建 Mind

```http
POST /api/minds
```

**请求体**:
```json
{
    "title": "AI 想法助手"
}
```

**响应**:
```json
{
    "id": "mind_20241228120000",
    "title": "AI 想法助手",
    "crystal": null,
    "created_at": "2024-12-28T12:00:00",
    "updated_at": "2024-12-28T12:00:00"
}
```

### 1.2 获取 Mind 列表

```http
GET /api/minds
```

**响应**:
```json
{
    "minds": [
        {
            "id": "mind_20241228120000",
            "title": "AI 想法助手",
            "crystal": "...",
            "created_at": "2024-12-28T12:00:00",
            "updated_at": "2024-12-28T12:00:00"
        }
    ]
}
```

### 1.3 获取 Mind 详情

```http
GET /api/minds/{mind_id}
```

### 1.4 获取 Crystal（总览）

```http
GET /api/minds/{mind_id}/crystal
```

**响应**:
```json
{
    "mind_id": "mind_20241228120000",
    "crystal": "## 核心目标\n...",
    "updated_at": "2024-12-28T12:00:00"
}
```

---

## 2. 投喂

### 2.1 添加投喂

```http
POST /api/minds/{mind_id}/feed
```

**请求体**:
```json
{
    "content": "我觉得这个功能应该更简单一些..."
}
```

**响应**:
```json
{
    "status": "ok",
    "message": "已记录",
    "feed_id": "feed_20241228120000123456"
}
```

---

## 3. 输出

### 3.1 生成输出

```http
POST /api/minds/{mind_id}/output
```

**请求体**:
```json
{
    "instruction": "写一段给程序员看的需求说明"
}
```

**响应**:
```json
{
    "content": "# 需求说明\n\n## 功能概述\n...",
    "mind_id": "mind_20241228120000"
}
```

---

## 4. 健康检查

```http
GET /health
```

**响应**:
```json
{
    "status": "ok",
    "service": "MindLink"
}
```

---

**文档版本**: v1.0
**最后更新**: 2024-12-28
