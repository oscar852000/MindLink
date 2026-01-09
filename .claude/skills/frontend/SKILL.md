---
name: frontend
description: 前端多端开发规范。当任务涉及修改 HTML、CSS、JavaScript，或需要检查桌面端/移动端一致性时自动加载。
---

# 多端开发规范

**文档维护声明**：本文档可以修改。如果发现内容与实际不符、过时、或有错误，必须修改。但保持精简，避免臃肿。

## 架构说明

MindLink 采用**多端独立架构**：

| 端 | HTML | CSS | JS |
|----|------|-----|-----|
| 桌面端 | `index.html` | `style.css` | `app.js` |
| 移动端 | `mobile.html` | `mobile.css` | `mobile.js` |
| 管理后台 | `admin.html` | `admin.css` | `admin.js` |

**关键点**：桌面端和移动端代码完全独立，改一边不影响另一边。

设备自动检测：`api/main.py` 根据 User-Agent 自动返回对应页面。

---

## 开发规则

| 改动类型 | 桌面端 | 移动端 |
|----------|--------|--------|
| HTML 结构 | 改 `index.html` | 改 `mobile.html` |
| 样式调整 | 改 `style.css` | 改 `mobile.css` |
| 业务逻辑 | 改 `app.js` | 改 `mobile.js` |
| API 变更 | **两边都要改** | **两边都要改** |

---

## data-logic-id 一致性（关键）

两端 HTML 使用**相同的 `data-logic-id` 属性**标识逻辑元素：

```
必须一致的 ID：
- mindList, mindDetail, emptyState
- feedInput, feedBtn, feedStatus
- chatMessages, chatInput, sendChatBtn
- timelineContent, structureContent, narrativeContent
- outputInstruction, outputResult
- createMindModal, newMindTitle, modalCreateBtn, modalCancelBtn
```

---

## 修改前检查

```bash
# 检查两端元素 ID 是否一致
grep -o 'id="[^"]*"' web/index.html | sort > /tmp/pc_ids.txt
grep -o 'id="[^"]*"' web/mobile.html | sort > /tmp/mp_ids.txt
diff /tmp/pc_ids.txt /tmp/mp_ids.txt
```

---

## CSS 注意事项

- `style.css`：桌面端专用，使用 `data-logic-id` 选择器
- `mobile.css`：移动端专用，使用 CSS 类（如 `.tab-pane.active`）
- 移动端 Tab 切换使用 CSS 类控制显示，避免使用内联 `style.display`

---

## 验证清单

改完前端后，确认：

- [ ] 桌面端页面能打开
- [ ] 移动端页面能打开
- [ ] 核心功能可用（列表、详情、投喂、对话）
- [ ] 控制台没有报错
- [ ] 如果改了元素 ID，两端已同步
