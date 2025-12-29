/**
 * MindLink 前端应用 - 三层架构版本
 */

const API_BASE = '/api';

// 状态
let currentMindId = null;
let chatHistory = []; // 对话历史

// DOM 元素
const mindList = document.getElementById('mindList');
const emptyState = document.getElementById('emptyState');
const mindDetail = document.getElementById('mindDetail');
const mindTitle = document.getElementById('mindTitle');
const feedInput = document.getElementById('feedInput');
const feedStatus = document.getElementById('feedStatus');
const timelineContent = document.getElementById('timelineContent');
const narrativeContent = document.getElementById('narrativeContent');
const structureContent = document.getElementById('structureContent');
const outputInstruction = document.getElementById('outputInstruction');
const outputResult = document.getElementById('outputResult');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const chatModel = document.getElementById('chatModel');
const chatStyle = document.getElementById('chatStyle');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadMinds();
    setupEventListeners();
    // 默认激活第一个Tab
    switchTab('feed');
});

// 设置事件监听
function setupEventListeners() {
    // 创建 Mind 按钮
    document.getElementById('createMindBtn').addEventListener('click', () => {
        document.getElementById('createMindModal').showModal();
        document.getElementById('newMindTitle').focus();
    });

    // 模态框按钮
    document.getElementById('modalCancelBtn').addEventListener('click', closeModal);
    document.getElementById('modalCreateBtn').addEventListener('click', createMind);

    // 移动端返回按钮 - 返回列表
    const mobileBackBtn = document.getElementById('mobileBackBtn');
    if (mobileBackBtn) {
        mobileBackBtn.addEventListener('click', () => {
            goBackToList();
        });
    }

    // 移动端空状态菜单按钮
    const emptyStateMenuBtn = document.getElementById('emptyStateMenuBtn');
    if (emptyStateMenuBtn) {
        emptyStateMenuBtn.addEventListener('click', () => {
            document.querySelector('[data-logic-id="app-container"]').classList.toggle('sidebar-open');
        });
    }

    // 移动端遮罩层点击关闭侧边栏
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', () => {
            document.querySelector('[data-logic-id="app-container"]').classList.remove('sidebar-open');
        });
    }

    // 投喂按钮
    document.getElementById('feedBtn').addEventListener('click', submitFeed);

    // 生成叙事按钮
    document.getElementById('generateNarrativeBtn').addEventListener('click', generateNarrative);

    // 输出按钮
    document.getElementById('outputBtn').addEventListener('click', generateOutput);

    // 刷新导图按钮
    document.getElementById('refreshMindmapBtn').addEventListener('click', loadMindmap);

    // 对话相关
    document.getElementById('sendChatBtn').addEventListener('click', sendChatMessage);
    document.getElementById('clearChatBtn').addEventListener('click', clearChat);

    // 标签页切换
    document.querySelectorAll('[data-tab]').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Enter 键提交
    document.getElementById('newMindTitle').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') createMind();
    });

    feedInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submitFeed();
    });

    outputInstruction.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') generateOutput();
    });

    // 对话输入框 Enter 发送
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
}

// 加载 Mind 列表
async function loadMinds() {
    try {
        const response = await fetch(`${API_BASE}/minds`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();

        mindList.innerHTML = '';

        if (data.minds.length === 0) {
            mindList.innerHTML = '<p style="color: var(--text-dim); padding: 1rem; text-align: center;">还没有 Mind，创建一个吧</p>';
            return;
        }

        data.minds.forEach(mind => {
            const item = document.createElement('div');
            item.dataset.mindId = mind.id;
            item.dataset.logicId = 'mind-list-item';
            if (mind.id === currentMindId) {
                item.dataset.active = 'true';
            }
            item.innerHTML = `
                <h3>${escapeHtml(mind.title)}</h3>
                <span>${formatDate(mind.updated_at)}</span>
            `;
            item.addEventListener('click', () => {
                selectMind(mind.id);
            });
            mindList.appendChild(item);
        });
    } catch (error) {
        console.error('加载失败:', error);
    }
}

// 选择 Mind
async function selectMind(mindId) {
    currentMindId = mindId;
    chatHistory = []; // 切换 Mind 时清空对话历史

    // 更新列表选中状态
    document.querySelectorAll('[data-mind-id]').forEach(item => {
        if (item.dataset.mindId === mindId) {
            item.dataset.active = 'true';
        } else {
            delete item.dataset.active;
        }
    });

    // 显示详情
    emptyState.style.display = 'none';
    mindDetail.style.display = 'flex';

    // 移动端：添加 show-detail 类，自动隐藏侧边栏
    const appContainer = document.querySelector('[data-logic-id="app-container"]');
    appContainer.classList.add('show-detail');
    appContainer.classList.remove('sidebar-open');

    // 重置对话区
    chatMessages.innerHTML = `
        <div data-logic-id="chat-welcome">
            <p>我已经了解了你关于这个主题的所有想法。</p>
            <p>有什么想和我讨论的吗？</p>
        </div>
    `;

    // 加载详情
    try {
        const response = await fetch(`${API_BASE}/minds/${mindId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const mind = await response.json();
        mindTitle.textContent = mind.title;

        // 加载时间轴和结构
        await Promise.all([
            loadTimeline(),
            loadStructure()
        ]);
    } catch (error) {
        console.error('加载失败:', error);
    }
}

// 加载时间轴
async function loadTimeline() {
    if (!currentMindId) return;

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/timeline-view`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();

        if (!data.timeline || data.timeline.length === 0) {
            timelineContent.innerHTML = '<p style="color: var(--text-dim); text-align: center;">还没有内容，先投喂一些想法吧</p>';
            return;
        }

        let html = '<div data-logic-id="timeline-list">';
        data.timeline.forEach(day => {
            html += `<div data-logic-id="timeline-day">
                <div data-logic-id="timeline-date">${day.date}</div>`;
            day.items.forEach(item => {
                html += `<div data-logic-id="timeline-item">
                    <span data-logic-id="timeline-time">${item.time}</span>
                    <div data-logic-id="timeline-text">${escapeHtml(item.content)}</div>
                </div>`;
            });
            html += '</div>';
        });
        html += '</div>';

        timelineContent.innerHTML = html;
    } catch (error) {
        console.error('加载时间轴失败:', error);
        timelineContent.innerHTML = '<p>加载失败</p>';
    }
}

// 加载结构视图
async function loadStructure() {
    if (!currentMindId) return;

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/crystal`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();

        if (!data.structure_markdown || data.structure_markdown === '还没有内容，先投喂一些想法吧') {
            structureContent.innerHTML = '<p style="color: var(--text-dim); text-align: center;">还没有内容，先投喂一些想法吧</p>';
            return;
        }

        structureContent.innerHTML = `<div data-logic-id="structure-text">${markdownToHtml(data.structure_markdown)}</div>`;
    } catch (error) {
        console.error('加载结构失败:', error);
        structureContent.innerHTML = '<p>加载失败</p>';
    }
}

// 生成叙事
async function generateNarrative() {
    if (!currentMindId) return;

    const btn = document.getElementById('generateNarrativeBtn');
    btn.disabled = true;
    btn.textContent = '生成中...';
    narrativeContent.innerHTML = '<p style="color: var(--text-dim);">正在整合所有记录，生成叙事...</p>';

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/narrative`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.narrative) {
            narrativeContent.innerHTML = `<div data-logic-id="narrative-text">${markdownToHtml(data.narrative)}</div>`;
        } else {
            narrativeContent.innerHTML = '<p>暂无内容</p>';
        }
    } catch (error) {
        console.error('生成叙事失败:', error);
        narrativeContent.innerHTML = '<p>生成失败</p>';
    } finally {
        btn.disabled = false;
        btn.textContent = '生成叙事';
    }
}

// 创建 Mind
async function createMind() {
    const title = document.getElementById('newMindTitle').value.trim();
    if (!title) return;

    try {
        const response = await fetch(`${API_BASE}/minds`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title })
        });

        if (response.ok) {
            const mind = await response.json();
            closeModal();
            document.getElementById('newMindTitle').value = '';
            await loadMinds();
            selectMind(mind.id);
        }
    } catch (error) {
        console.error('创建失败:', error);
    }
}

// 关闭弹窗
function closeModal() {
    document.getElementById('createMindModal').close();
}

// 提交投喂
async function submitFeed() {
    if (!currentMindId) return;

    const content = feedInput.value.trim();
    if (!content) return;

    const btn = document.getElementById('feedBtn');
    btn.disabled = true;
    feedStatus.textContent = '正在处理...';

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/feed`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            feedInput.value = '';
            feedStatus.textContent = '已记录，正在去噪和更新结构...';

            // 延迟刷新，等待后台处理
            setTimeout(async () => {
                await Promise.all([
                    loadTimeline(),
                    loadStructure()
                ]);
                feedStatus.textContent = '处理完成';
            }, 3000);

            loadMinds();
        } else {
            feedStatus.textContent = '提交失败';
        }
    } catch (error) {
        console.error('投喂失败:', error);
        feedStatus.textContent = '提交失败';
    } finally {
        btn.disabled = false;
    }
}

// 生成输出
async function generateOutput() {
    if (!currentMindId) return;

    const instruction = outputInstruction.value.trim();
    if (!instruction) return;

    const btn = document.getElementById('outputBtn');
    btn.disabled = true;
    outputResult.innerHTML = '<p style="color: var(--text-dim);">正在生成...</p>';

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/output`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instruction })
        });

        if (response.ok) {
            const data = await response.json();
            outputResult.innerHTML = `<div data-logic-id="output-text">${escapeHtml(data.content)}</div>`;
        } else {
            const error = await response.json();
            outputResult.innerHTML = `<p>${error.detail || '生成失败'}</p>`;
        }
    } catch (error) {
        console.error('生成失败:', error);
        outputResult.innerHTML = '<p>生成失败</p>';
    } finally {
        btn.disabled = false;
    }
}

// 加载思维导图
async function loadMindmap() {
    if (!currentMindId) return;

    const container = document.getElementById('mindmapContainer');
    container.innerHTML = '<div style="text-align: center; color: var(--text-dim);">正在生成思维导图...</div>';

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/mindmap`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();

        if (data.mindmap && data.mindmap.branches && data.mindmap.branches.length > 0) {
            renderMindmap(data.mindmap);
        } else {
            container.innerHTML = '<p style="color: var(--text-dim); text-align: center;">还没有足够的内容生成导图</p>';
        }
    } catch (error) {
        console.error('加载导图失败:', error);
        container.innerHTML = '<p>加载失败</p>';
    }
}

// 渲染思维导图
function renderMindmap(mindmap) {
    const container = document.getElementById('mindmapContainer');

    let html = '<div data-logic-id="mindmap-tree">';
    html += `<div data-logic-id="tree-center">${escapeHtml(mindmap.center)}</div>`;
    html += '<div data-logic-id="tree-branches">';

    mindmap.branches.forEach(branch => {
        const isPending = branch.type === 'pending';
        html += `<div data-logic-id="tree-branch" data-pending="${isPending}">
            <div data-logic-id="branch-label">${escapeHtml(branch.label)}${isPending ? ' ❓' : ''}</div>`;

        if (branch.children && branch.children.length > 0) {
            html += '<ul data-logic-id="branch-children">';
            branch.children.forEach(child => {
                html += `<li>${escapeHtml(child)}</li>`;
            });
            html += '</ul>';
        }
        html += '</div>';
    });

    html += '</div></div>';
    container.innerHTML = html;
}

// 切换标签页
function switchTab(tabName) {
    // 更新标签按钮状态
    document.querySelectorAll('[data-tab]').forEach(tab => {
        if (tab.dataset.tab === tabName) {
            tab.dataset.active = 'true';
        } else {
            delete tab.dataset.active;
        }
    });

    // 更新内容显示
    const allTabs = ['feed', 'chat', 'timeline', 'narrative', 'structure', 'mindmap', 'output'];
    allTabs.forEach(tab => {
        const element = document.getElementById(`${tab}Tab`);
        if (element) {
            if (tab === tabName) {
                // Chat Tab 需要 flex 布局
                element.style.display = (tab === 'chat') ? 'flex' : 'block';
            } else {
                element.style.display = 'none';
            }
        }
    });
}

// ========== 对话功能 ==========

// 发送对话消息
async function sendChatMessage() {
    if (!currentMindId) return;

    const message = chatInput.value.trim();
    if (!message) return;

    const btn = document.getElementById('sendChatBtn');
    btn.disabled = true;

    // 添加用户消息到界面
    addChatMessage('user', message);
    chatInput.value = '';

    // 添加加载状态
    const loadingId = addChatMessage('assistant', '思考中...', true);

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                history: chatHistory,
                model: chatModel.value,
                style: chatStyle.value
            })
        });

        // 移除加载状态
        removeChatMessage(loadingId);

        if (response.ok) {
            const data = await response.json();
            // 添加 AI 回复
            addChatMessage('assistant', data.reply);
            // 更新历史
            chatHistory.push({ role: 'user', content: message });
            chatHistory.push({ role: 'assistant', content: data.reply });
        } else {
            const error = await response.json();
            addChatMessage('assistant', `抱歉，出错了：${error.detail || '请稍后重试'}`);
        }
    } catch (error) {
        console.error('对话失败:', error);
        removeChatMessage(loadingId);
        addChatMessage('assistant', '网络错误，请稍后重试');
    } finally {
        btn.disabled = false;
        chatInput.focus();
    }
}

// 添加对话消息到界面
function addChatMessage(role, content, isLoading = false) {
    // 隐藏欢迎语
    const welcome = chatMessages.querySelector('[data-logic-id="chat-welcome"]');
    if (welcome) {
        welcome.style.display = 'none';
    }

    const messageId = `msg_${Date.now()}`;
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.dataset.logicId = 'chat-message';
    messageDiv.dataset.role = role;

    const roleText = role === 'user' ? '你' : 'AI';
    // 用户消息用 escapeHtml，AI 消息用 markdownToHtml
    const contentHtml = role === 'user' ? escapeHtml(content) : markdownToHtml(content);

    messageDiv.innerHTML = `
        <div data-logic-id="chat-role">${roleText}</div>
        <div data-logic-id="chat-content">${contentHtml}</div>
    `;

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageId;
}

// 移除对话消息
function removeChatMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

// 清空对话
function clearChat() {
    if (!confirm('确定要刷新对话吗？当前对话记录将被清空。')) {
        return;
    }

    chatHistory = [];
    chatMessages.innerHTML = `
        <div data-logic-id="chat-welcome">
            <p>我已经了解了你关于这个主题的所有想法。</p>
            <p>有什么想和我讨论的吗？</p>
        </div>
    `;
}

// ========== 工具函数 ==========

// 返回列表（移动端）
function goBackToList() {
    const appContainer = document.querySelector('[data-logic-id="app-container"]');
    appContainer.classList.remove('show-detail');
    appContainer.classList.remove('sidebar-open');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

function markdownToHtml(markdown) {
    if (!markdown) return '';

    // 先转义 HTML 特殊字符（保留换行）
    let html = markdown
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Markdown 转换
    html = html
        // 标题
        .replace(/^### (.+)$/gm, '<h4>$1</h4>')
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        .replace(/^# (.+)$/gm, '<h2>$1</h2>')
        // 粗体和斜体
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // 代码块
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // 列表项
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // 处理连续的列表项，包裹成 ul
    html = html.replace(/(<li>.*<\/li>\n?)+/gs, match => `<ul>${match}</ul>`);

    // 换行转 <br>（但不在标签内部）
    html = html
        .replace(/<\/h[234]>\n/g, '</h$&>')  // 标题后不加 br
        .replace(/<\/ul>\n/g, '</ul>')        // 列表后不加 br
        .replace(/\n\n/g, '</p><p>')          // 双换行分段
        .replace(/\n/g, '<br>');              // 单换行

    // 包裹成段落
    if (!html.startsWith('<h') && !html.startsWith('<ul')) {
        html = '<p>' + html + '</p>';
    }

    return html;
}
