---
name: frontend
description: 前端多端开发规范。当任务涉及修改 HTML、CSS、JavaScript，或需要检查桌面端/移动端一致性时自动加载。
---

# 前端开发规范

**文档维护声明**：本文档可以修改。如果发现内容与实际不符、过时、或有错误，必须修改。但保持精简，避免臃肿。

---

## 三平台架构

| 平台 | 目录 | 优先级 |
|------|------|--------|
| PC 桌面端 | `web/index.html, style.css, app.js` | **主要** |
| 移动端 | `web/mobile.html, mobile.css, mobile.js` | **同步**（与 PC 保持一致） |
| 小程序端 | `miniprogram/` | **延后**（除非用户特别指令） |

**默认行为**：修改 PC 端时，同步修改移动端。小程序不动。

---

## 品牌规范

### 颜色（必须统一）

| 名称 | 色值 | 用途 |
|------|------|------|
| 晶体青 | `#22D3EE` | 主色调、逻辑元素 |
| 本质黑 | `#0B0C0F` | 背景、画布 |
| 液态灰 | `#E5E7EB` | 叙事窗口、上下文 |

### 字体

| 字体 | 用途 |
|------|------|
| JetBrains Mono | 数据、逻辑流、提示词 |
| Inter | 正文、叙事内容 |

---

## data-logic-id 一致性（关键）

PC 和移动端 HTML 使用**相同的 `data-logic-id`** 标识逻辑元素。

**修改元素 ID 时，必须同步两端。**

常见需要同步的 ID：
- mindList, mindDetail, emptyState
- feedInput, feedBtn, feedStatus
- chatMessages, chatInput, sendChatBtn
- timelineContent, structureContent, narrativeContent

---

## 验证清单

改完前端后，确认：

- [ ] PC 端页面能打开
- [ ] 移动端页面能打开
- [ ] 核心功能可用（列表、详情、投喂、对话）
- [ ] 控制台没有报错
- [ ] 元素 ID 两端一致（如有修改）

---

**最后更新**: 2026-01-12
