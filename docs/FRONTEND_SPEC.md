# MindLink PC 端前端规格文档

> 本文档供前端重构使用，包含所有业务逻辑、API 接口、交互规范。
> 设计者可以自由选择技术栈和 UI 风格，但需遵循本文档的逻辑规范。

---

## 一、产品概述

**MindLink** 是一个 AI 驱动的想法整理助手，帮助用户将零散的想法整理成结构化的认知。

**核心功能：**
- **Mind（想法档案）**：一个主题 = 一个 Mind
- **投喂**：用户输入碎片想法，AI 自动去噪整理
- **结构**：AI 提炼的结构化认知
- **时间轴**：按时间回溯的原始记录
- **对话**：与 AI 讨论当前主题
- **叙事**：AI 生成的连贯思想叙述
- **输出**：按指令生成特定表达（如给投资人的说明）

---

## 二、页面结构

```
┌─────────────────────────────────────────────────────────────┐
│                        整体布局                              │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│   侧边栏      │              主内容区                         │
│   (300px)    │              (flex: 1)                       │
│              │                                              │
│  ┌────────┐  │  ┌────────────────────────────────────────┐  │
│  │ Logo   │  │  │  空状态 / Mind详情                      │  │
│  │ 口号   │  │  │                                        │  │
│  │ 新建   │  │  │  ┌──────────────────────────────────┐  │  │
│  └────────┘  │  │  │  标题 + 概述 + 标签               │  │  │
│              │  │  └──────────────────────────────────┘  │  │
│  ┌────────┐  │  │                                        │  │
│  │ Mind   │  │  │  ┌──────────────────────────────────┐  │  │
│  │ 列表   │  │  │  │  Tab 导航                        │  │  │
│  │        │  │  │  │  投喂|结构|时间轴|对话|叙事|输出  │  │  │
│  │        │  │  │  └──────────────────────────────────┘  │  │
│  └────────┘  │  │                                        │  │
│              │  │  ┌──────────────────────────────────┐  │  │
│  ┌────────┐  │  │  │  Tab 内容区                      │  │  │
│  │ 用户名  │  │  │  │  (根据选中的 Tab 显示不同内容)   │  │  │
│  │ 管理   │  │  │  │                                  │  │  │
│  │ 退出   │  │  │  └──────────────────────────────────┘  │  │
│  └────────┘  │  └────────────────────────────────────────┘  │
└──────────────┴──────────────────────────────────────────────┘
```

### 2.1 侧边栏结构

```html
<aside> 侧边栏容器
  <header> 头部
    <div> Logo + 品牌名 "MindLink"
    <p> 口号文案
    <button> "+ 新建 Mind" 按钮
  </header>

  <section> Mind 列表容器
    <!-- 动态渲染，见第六节 -->
  </section>

  <footer> 底部
    <span> 当前用户名
    <a> "提示词管理" 链接（仅管理员可见）
    <button> "退出登录" 按钮
  </footer>
</aside>
```

### 2.2 主内容区结构

```html
<main> 主内容容器
  <!-- 状态1: 空状态（未选择 Mind） -->
  <section> 空状态
    <div> 图标
    <h2> "选择或创建一个 Mind"
    <p> "开始整理你的碎碎念与洞察"
  </section>

  <!-- 状态2: Mind 详情（选中 Mind 后显示） -->
  <section> Mind 详情（默认隐藏）
    <header> 标题区
      <h2> Mind 标题
    </header>

    <div> 概述区（默认隐藏，有内容时显示）
      <p> AI 生成的一句话概述
      <div> 标签云
    </div>

    <nav> Tab 导航
      <button data-tab="feed"> 投喂
      <button data-tab="structure"> 结构
      <button data-tab="timeline"> 时间轴
      <button data-tab="chat"> 对话
      <button data-tab="narrative"> 叙事
      <button data-tab="output"> 输出
    </nav>

    <div> Tab 内容容器
      <!-- 6 个 Tab 内容区，见下文 -->
    </div>
  </section>
</main>
```

### 2.3 六个 Tab 内容区

#### Tab 1: 投喂 (feed)
```html
<section id="feedTab">
  <div> 输入区
    <textarea> 多行输入框，placeholder="想到什么写什么，AI 会自动去噪处理..."
    <button> "记录思想" 提交按钮
  </div>
  <div> 状态提示区（显示处理状态）
</section>
```

#### Tab 2: 结构 (structure)
```html
<section id="structureTab">
  <header> "提炼核心认知，结构化展示"
  <div> 内容容器（渲染 Markdown）
</section>
```

#### Tab 3: 时间轴 (timeline)
```html
<section id="timelineTab">
  <header> "去噪后的原始记录，按时间轴回溯"
  <div> 内容容器
    <!-- 动态渲染，见第六节 -->
  </div>
</section>
```

#### Tab 4: 对话 (chat)
```html
<section id="chatTab">
  <header> 控制栏
    <select> 模型选择
    <select> 风格选择
    <button> "刷新" 清空对话
  </header>
  <div> 消息列表容器
    <!-- 动态渲染，见第六节 -->
  </div>
  <div> 输入区
    <textarea> 单行输入框
    <button> 发送按钮 "↑"
  </div>
</section>
```

#### Tab 5: 叙事 (narrative)
```html
<section id="narrativeTab">
  <header>
    <p> "整合所有记录，生成连贯的思想叙事"
    <button> "生成叙事" 按钮
  </header>
  <div> 内容容器（渲染 Markdown）
</section>
```

#### Tab 6: 输出 (output)
```html
<section id="outputTab">
  <div> 输入区
    <input type="text"> 指令输入框，placeholder="例如：写一段给投资人看的说明"
    <button> "生成" 按钮
  </div>
  <div> 结果容器
</section>
```

### 2.4 模态框

#### 创建 Mind 模态框
```html
<dialog id="createMindModal">
  <h3> "创建新的 Mind"
  <p> "为一个新的话题、项目或思考方向命名"
  <input type="text"> 标题输入框
  <div> 按钮区
    <button> "取消"
    <button> "创建档案"
  </div>
</dialog>
```

#### 编辑记录模态框
```html
<dialog id="editFeedModal">
  <h3> "编辑记录"
  <input type="hidden"> 记录 ID
  <textarea> 内容编辑框
  <div> 按钮区
    <button> "取消"
    <button> "保存"
  </div>
</dialog>
```

---

## 三、交互元素清单

### 3.1 按钮交互

| 元素 ID | 功能 | 触发事件 | 行为 |
|---------|------|----------|------|
| `createMindBtn` | 新建 Mind | click | 打开创建模态框 |
| `logoutBtn` | 退出登录 | click | 调用登出 API，跳转登录页 |
| `feedBtn` | 提交投喂 | click | 提交内容到 API |
| `generateNarrativeBtn` | 生成叙事 | click | 调用叙事生成 API |
| `outputBtn` | 生成输出 | click | 调用输出生成 API |
| `sendChatBtn` | 发送对话 | click | 发送消息到对话 API |
| `clearChatBtn` | 清空对话 | click | 确认后清空对话历史 |
| `modalCancelBtn` | 取消创建 | click | 关闭模态框 |
| `modalCreateBtn` | 确认创建 | click | 调用创建 API |
| `editCancelBtn` | 取消编辑 | click | 关闭编辑模态框 |
| `editSaveBtn` | 保存编辑 | click | 调用编辑 API |

### 3.2 输入框交互

| 元素 ID | 功能 | 特殊交互 |
|---------|------|----------|
| `feedInput` | 投喂内容输入 | Ctrl+Enter 提交 |
| `chatInput` | 对话消息输入 | Enter 发送（Shift+Enter 换行） |
| `outputInstruction` | 输出指令输入 | Enter 生成 |
| `newMindTitle` | 新 Mind 标题 | Enter 创建 |

### 3.3 选择器

| 元素 ID | 功能 | 选项 |
|---------|------|------|
| `chatModel` | AI 模型选择 | Gemini 3 Flash / Gemini 3 Pro / GPT-5.2 Plato |
| `chatStyle` | 对话风格选择 | 理性分析 / 苏格拉底式 / 创意发散 |

### 3.4 Tab 切换

| data-tab 值 | 对应内容区 ID | 功能 |
|-------------|---------------|------|
| `feed` | `feedTab` | 投喂 |
| `structure` | `structureTab` | 结构 |
| `timeline` | `timelineTab` | 时间轴 |
| `chat` | `chatTab` | 对话 |
| `narrative` | `narrativeTab` | 叙事 |
| `output` | `outputTab` | 输出 |

**切换逻辑：**
1. 点击 Tab 按钮
2. 更新按钮激活状态
3. 显示对应内容区，隐藏其他
4. 切换到 structure/timeline 时，自动刷新数据

---

## 四、API 端点清单

### 4.1 认证相关

| 方法 | 端点 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | `/api/auth/me` | 获取当前用户信息 | - | `{logged_in, user: {username, is_admin}}` |
| POST | `/api/auth/logout` | 退出登录 | - | - |

### 4.2 Mind 管理

| 方法 | 端点 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | `/api/minds` | 获取 Mind 列表 | - | `{minds: [{id, title, summary, updated_at}]}` |
| POST | `/api/minds` | 创建 Mind | `{title}` | `{id, title, ...}` |
| GET | `/api/minds/{id}` | 获取 Mind 详情 | - | `{id, title, summary, tags, narrative}` |
| DELETE | `/api/minds/{id}` | 删除 Mind | - | - |

### 4.3 投喂与内容

| 方法 | 端点 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | `/api/minds/{id}/feed` | 投喂内容 | `{content}` | `{success}` |
| GET | `/api/minds/{id}/timeline-view` | 获取时间轴 | - | `{timeline: [{date, items: [{id, time, content}]}]}` |
| GET | `/api/minds/{id}/crystal` | 获取结构 | - | `{structure_markdown}` |
| PUT | `/api/feeds/{id}` | 编辑记录 | `{content}` | - |
| DELETE | `/api/feeds/{id}` | 删除记录 | - | - |

### 4.4 AI 功能

| 方法 | 端点 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | `/api/minds/{id}/narrative` | 生成叙事 | - | `{narrative, summary, tags, summary_changed, tags_changed}` |
| POST | `/api/minds/{id}/output` | 生成输出 | `{instruction}` | `{content}` |
| POST | `/api/minds/{id}/chat` | 对话 | `{message, model, style}` | `{reply}` |
| GET | `/api/minds/{id}/chat/history` | 获取对话历史 | - | `{messages: [{role, content}]}` |
| DELETE | `/api/minds/{id}/chat/history` | 清空对话历史 | - | - |

---

## 五、状态管理

### 5.1 全局状态

```javascript
state = {
    currentMindId: null  // 当前选中的 Mind ID
}
```

### 5.2 状态转换

```
初始状态
    ↓
[加载 Mind 列表]
    ↓
┌─────────────────────────────────────┐
│  无 Mind          有 Mind           │
│    ↓                ↓               │
│  显示空状态     显示 Mind 列表      │
│                     ↓               │
│              [用户点击 Mind]        │
│                     ↓               │
│              currentMindId = id     │
│                     ↓               │
│              隐藏空状态             │
│              显示 Mind 详情         │
│              加载详情数据           │
└─────────────────────────────────────┘
```

### 5.3 显示/隐藏逻辑

| 条件 | 空状态 | Mind 详情 | 概述区 | 管理链接 |
|------|--------|-----------|--------|----------|
| 未选中 Mind | 显示 | 隐藏 | - | - |
| 选中 Mind | 隐藏 | 显示 | 有内容则显示 | - |
| 用户是管理员 | - | - | - | 显示 |

---

## 六、动态渲染模板

### 6.1 Mind 列表项

```html
<div class="mind-item" data-mind-id="{mind.id}">
  <div class="mind-item__content">
    <h3 class="mind-item__title">{mind.title}</h3>
    <!-- 可选：如果有 summary -->
    <p class="mind-item__summary">{mind.summary}</p>
    <span class="mind-item__date">{格式化日期}</span>
  </div>
  <button class="mind-item__delete" title="删除">×</button>
</div>
```

**交互：**
- 点击内容区 → 选中该 Mind
- 点击删除按钮 → 确认后删除
- 选中状态 → 添加 `.is-active` 类

### 6.2 时间轴

```html
<!-- 日期分组 -->
<div class="timeline__date">{日期，如 "2024年12月30日"}</div>

<!-- 时间轴项 -->
<div class="timeline__item" data-feed-id="{item.id}">
  <div class="timeline__item-header">
    <span class="timeline__time">
      {时间，如 "14:30"}
      <!-- 第一条显示"当前"标签 -->
      <span class="timeline__tag">当前</span>
    </span>
    <button class="timeline__menu-btn">⋮</button>
    <div class="timeline__dropdown">
      <button data-action="edit">编辑</button>
      <button data-action="delete">删除</button>
    </div>
  </div>
  <div class="timeline__text">{item.content}</div>
</div>
```

**交互：**
- 点击菜单按钮 → 显示/隐藏下拉菜单
- 点击编辑 → 打开编辑模态框
- 点击删除 → 确认后删除
- 第一条记录添加 `--current` 修饰符

### 6.3 对话消息

```html
<!-- AI 消息 -->
<div class="chat__message">
  <div class="chat__role">AI</div>
  <div class="chat__bubble">{渲染后的 Markdown 内容}</div>
</div>

<!-- 用户消息 -->
<div class="chat__message chat__message--user">
  <div class="chat__role">你</div>
  <div class="chat__bubble">{纯文本，需转义}</div>
</div>
```

**交互：**
- 新消息添加到底部
- 自动滚动到最新消息
- AI 消息需渲染 Markdown
- 用户消息需 HTML 转义

### 6.4 标签云

```html
<span class="tag"># {tag}</span>
```

---

## 七、关键业务逻辑

### 7.1 投喂流程

```
用户输入内容
    ↓
点击"记录思想"
    ↓
禁用按钮，显示"正在处理..."
    ↓
POST /api/minds/{id}/feed
    ↓
成功 → 清空输入框
    → 显示"已记录，正在去噪和更新结构..."
    → 3秒后显示"处理完成"
    → 刷新 Mind 列表（更新时间）
失败 → 显示"提交失败"
    ↓
恢复按钮
```

### 7.2 对话流程

```
用户输入消息
    ↓
点击发送 / Enter
    ↓
添加用户消息到界面
清空输入框
禁用发送按钮
添加 AI "思考中..." 占位消息
    ↓
POST /api/minds/{id}/chat
    ↓
移除占位消息
成功 → 添加 AI 回复消息
失败 → 添加错误提示消息
    ↓
恢复按钮，聚焦输入框
```

### 7.3 选择 Mind 流程

```
用户点击 Mind 列表项
    ↓
更新 currentMindId
更新列表选中状态
隐藏空状态，显示详情区
    ↓
GET /api/minds/{id} 获取详情
    ↓
更新标题
更新概述和标签（如有）
更新叙事内容（如有）
    ↓
并行加载：
- GET /timeline-view → 渲染时间轴
- GET /crystal → 渲染结构
- GET /chat/history → 渲染对话历史
```

---

## 八、工具函数需求

### 8.1 HTML 转义

```javascript
// 防止 XSS，用于显示用户输入的纯文本
escapeHtml(text) → string
```

### 8.2 日期格式化

```javascript
// 将 ISO 日期转为 "12月30日" 格式
formatDate(isoString) → string
```

### 8.3 Markdown 转 HTML

```javascript
// 支持：标题、粗体、斜体、代码、列表
// AI 返回的内容需要渲染
markdownToHtml(markdown) → string
```

---

## 九、设计建议（非强制）

### 9.1 视觉风格参考

- **暗色主题**：深色背景，亮色文字
- **主色调**：青色/蓝绿色 (#00F5FF)
- **卡片式布局**：内容区域用圆角卡片
- **极简设计**：减少视觉噪音

### 9.2 交互建议

- 按钮点击有反馈（缩放/变色）
- 加载状态有明确提示
- 删除操作需要确认
- 输入框有 focus 状态

---

## 十、注意事项

1. **所有 API 请求**需携带 Cookie（credentials: 'same-origin'）
2. **Mind ID 格式**：`mind_` 前缀 + 时间戳，如 `mind_20251229020358458289`
3. **Feed ID 格式**：`feed_` 前缀 + 时间戳
4. **Tab 默认激活**：投喂 (feed)
5. **对话 Tab 布局**：需要 flex 纵向布局，消息区可滚动
6. **管理员判断**：通过 `/api/auth/me` 返回的 `is_admin` 字段

---

**文档版本**：v1.0
**生成时间**：2026-01-05
