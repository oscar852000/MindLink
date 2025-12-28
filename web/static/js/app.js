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
});

// 设置事件监听
function setupEventListeners() {
    // 创建 Mind 按钮
    document.getElementById('createMindBtn').addEventListener('click', () => {
        document.getElementById('createMindModal').classList.add('show');
        document.getElementById('newMindTitle').focus();
    });

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
    document.querySelectorAll('.tab').forEach(tab => {
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
        const data = await response.json();

        mindList.innerHTML = '';

        if (data.minds.length === 0) {
            mindList.innerHTML = '<p style="color: var(--text-secondary); padding: 1rem;">还没有 Mind，创建一个吧</p>';
            return;
        }

        data.minds.forEach(mind => {
            const item = document.createElement('div');
            item.className = 'mind-item' + (mind.id === currentMindId ? ' active' : '');
            item.dataset.mindId = mind.id;
            item.innerHTML = `
                <h3>${escapeHtml(mind.title)}</h3>
                <span class="date">${formatDate(mind.updated_at)}</span>
            `;
            item.addEventListener('click', () => selectMind(mind.id));
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
    document.querySelectorAll('.mind-item').forEach(item => {
        item.classList.toggle('active', item.dataset.mindId === mindId);
    });

    // 显示详情
    emptyState.style.display = 'none';
    mindDetail.style.display = 'flex';

    // 重置对话区
    chatMessages.innerHTML = `
        <div class="chat-welcome">
            <p>我已经了解了你关于这个主题的所有想法。</p>
            <p>有什么想和我讨论的吗？</p>
        </div>
    `;

    // 加载详情
    try {
        const response = await fetch(`${API_BASE}/minds/${mindId}`);
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
        const data = await response.json();

        if (!data.timeline || data.timeline.length === 0) {
            timelineContent.innerHTML = '<p class="placeholder">还没有内容，先投喂一些想法吧</p>';
            return;
        }

        let html = '<div class="timeline-list">';
        data.timeline.forEach(day => {
            html += `<div class="timeline-day">
                <div class="timeline-date">${day.date}</div>`;
            day.items.forEach(item => {
                html += `<div class="timeline-item">
                    <span class="timeline-time">${item.time}</span>
                    <div class="timeline-text">${escapeHtml(item.content)}</div>
                </div>`;
            });
            html += '</div>';
        });
        html += '</div>';

        timelineContent.innerHTML = html;
    } catch (error) {
        console.error('加载时间轴失败:', error);
        timelineContent.innerHTML = '<p class="placeholder">加载失败</p>';
    }
}

// 加载结构视图
async function loadStructure() {
    if (!currentMindId) return;

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/crystal`);
        const data = await response.json();

        if (!data.structure_markdown || data.structure_markdown === '还没有内容，先投喂一些想法吧') {
            structureContent.innerHTML = '<p class="placeholder">还没有内容，先投喂一些想法吧</p>';
            return;
        }

        structureContent.innerHTML = `<div class="structure-text">${markdownToHtml(data.structure_markdown)}</div>`;
    } catch (error) {
        console.error('加载结构失败:', error);
        structureContent.innerHTML = '<p class="placeholder">加载失败</p>';
    }
}

// 生成叙事
async function generateNarrative() {
    if (!currentMindId) return;

    const btn = document.getElementById('generateNarrativeBtn');
    btn.disabled = true;
    btn.textContent = '生成中...';
    narrativeContent.innerHTML = '<p class="loading">正在整合所有记录，生成叙事...</p>';

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/narrative`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.narrative) {
            narrativeContent.innerHTML = `<div class="narrative-text">${escapeHtml(data.narrative)}</div>`;
        } else {
            narrativeContent.innerHTML = '<p class="placeholder">暂无内容</p>';
        }
    } catch (error) {
        console.error('生成叙事失败:', error);
        narrativeContent.innerHTML = '<p class="placeholder">生成失败</p>';
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
    document.getElementById('createMindModal').classList.remove('show');
}

// 提交投喂
async function submitFeed() {
    if (!currentMindId) return;

    const content = feedInput.value.trim();
    if (!content) return;

    const btn = document.getElementById('feedBtn');
    btn.disabled = true;
    feedStatus.textContent = '正在处理...';
    feedStatus.className = 'feed-status';

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/feed`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            feedInput.value = '';
            feedStatus.textContent = '已记录，正在去噪和更新结构...';
            feedStatus.className = 'feed-status success';

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
            feedStatus.className = 'feed-status error';
        }
    } catch (error) {
        console.error('投喂失败:', error);
        feedStatus.textContent = '提交失败';
        feedStatus.className = 'feed-status error';
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
    outputResult.innerHTML = '<p class="loading">正在生成...</p>';

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/output`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instruction })
        });

        if (response.ok) {
            const data = await response.json();
            outputResult.innerHTML = `<div class="output-text">${escapeHtml(data.content)}</div>`;
        } else {
            const error = await response.json();
            outputResult.innerHTML = `<p class="error">${error.detail || '生成失败'}</p>`;
        }
    } catch (error) {
        console.error('生成失败:', error);
        outputResult.innerHTML = '<p class="error">生成失败</p>';
    } finally {
        btn.disabled = false;
    }
}

// 加载思维导图
async function loadMindmap() {
    if (!currentMindId) return;

    const container = document.getElementById('mindmapContainer');
    container.innerHTML = '<div class="mindmap-loading">正在生成思维导图...</div>';

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/mindmap`);
        const data = await response.json();

        if (data.mindmap && data.mindmap.branches && data.mindmap.branches.length > 0) {
            renderMindmap(data.mindmap);
        } else {
            container.innerHTML = '<p class="placeholder">还没有足够的内容生成导图</p>';
        }
    } catch (error) {
        console.error('加载导图失败:', error);
        container.innerHTML = '<p class="placeholder">加载失败</p>';
    }
}

// 渲染思维导图
function renderMindmap(mindmap) {
    const container = document.getElementById('mindmapContainer');

    let html = '<div class="mindmap-tree">';
    html += `<div class="tree-center">${escapeHtml(mindmap.center)}</div>`;
    html += '<div class="tree-branches">';

    mindmap.branches.forEach(branch => {
        const isPending = branch.type === 'pending';
        html += `<div class="tree-branch${isPending ? ' pending' : ''}">
            <div class="branch-label">${escapeHtml(branch.label)}${isPending ? ' ❓' : ''}</div>`;

        if (branch.children && branch.children.length > 0) {
            html += '<ul class="branch-children">';
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
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // 更新内容显示
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');
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
    const welcome = chatMessages.querySelector('.chat-welcome');
    if (welcome) {
        welcome.style.display = 'none';
    }

    const messageId = `msg_${Date.now()}`;
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `chat-message ${role}${isLoading ? ' loading' : ''}`;

    const roleText = role === 'user' ? '你' : 'AI';
    messageDiv.innerHTML = `
        <div class="role">${roleText}</div>
        <div class="content">${escapeHtml(content)}</div>
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
        <div class="chat-welcome">
            <p>我已经了解了你关于这个主题的所有想法。</p>
            <p>有什么想和我讨论的吗？</p>
        </div>
    `;
}

// ========== 工具函数 ==========
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
    return markdown
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
        .replace(/<\/ul>\s*<ul>/g, '')
        .replace(/\n/g, '<br>');
}
