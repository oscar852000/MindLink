/**
 * MindLink 前端应用 - 三层架构版本
 */

const API_BASE = '/api';

// 状态
let currentMindId = null;

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
    loadUserInfo();
    loadMinds();
    setupEventListeners();
    // 默认激活第一个Tab
    switchTab('feed');

    // 点击空白处关闭下拉菜单
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.timeline-menu-btn') && !e.target.closest('.timeline-dropdown')) {
            document.querySelectorAll('.timeline-dropdown.show').forEach(d => d.classList.remove('show'));
        }
    });
});

// 加载用户信息
async function loadUserInfo() {
    try {
        const response = await fetch(`${API_BASE}/auth/me`, { credentials: 'same-origin' });
        const data = await response.json();

        if (data.logged_in && data.user) {
            document.getElementById('currentUser').textContent = data.user.username;
            // 管理员显示提示词管理链接
            if (data.user.is_admin) {
                document.getElementById('adminLink').style.display = 'block';
            }
        }
    } catch (err) {
        console.error('加载用户信息失败:', err);
    }
}

// 设置事件监听
function setupEventListeners() {
    // 创建 Mind 按钮
    document.getElementById('createMindBtn').addEventListener('click', () => {
        document.getElementById('createMindModal').showModal();
        document.getElementById('newMindTitle').focus();
    });

    // 退出登录按钮
    document.getElementById('logoutBtn').addEventListener('click', async () => {
        try {
            await fetch(`${API_BASE}/auth/logout`, { method: 'POST', credentials: 'same-origin' });
            window.location.href = '/login';
        } catch (err) {
            console.error('退出登录失败:', err);
        }
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

            // 构建概述显示（如果有）
            const summaryHtml = mind.summary
                ? `<p class="mind-summary">${escapeHtml(mind.summary)}</p>`
                : '';

            item.innerHTML = `
                <div class="mind-item-content">
                    <h3>${escapeHtml(mind.title)}</h3>
                    ${summaryHtml}
                    <span>${formatDate(mind.updated_at)}</span>
                </div>
                <button class="mind-delete-btn" title="删除">×</button>
            `;

            // 点击内容区选择 Mind
            item.querySelector('.mind-item-content').addEventListener('click', () => {
                selectMind(mind.id);
            });

            // 点击删除按钮
            item.querySelector('.mind-delete-btn').addEventListener('click', (e) => {
                e.stopPropagation(); // 阻止冒泡到父元素
                deleteMind(mind.id);
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

    // 桌面端：添加 show-detail 类，自动隐藏侧边栏
    const appContainer = document.querySelector('[data-logic-id="app-container"]');
    if (appContainer) {
        appContainer.classList.add('show-detail');
        appContainer.classList.remove('sidebar-open');
    }

    // 先显示加载状态
    chatMessages.innerHTML = `
        <div data-logic-id="chat-welcome">
            <p>正在加载对话记录...</p>
        </div>
    `;

    // 清空输出内容（避免显示其他 Mind 的内容）
    document.getElementById('outputResult').innerHTML = '';

    // 加载详情
    try {
        const response = await fetch(`${API_BASE}/minds/${mindId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const mind = await response.json();
        mindTitle.textContent = mind.title;

        // 显示概述和标签
        updateSummaryAndTags(mind.summary, mind.tags);

        // 显示已保存的叙事（如果有）
        if (mind.narrative) {
            narrativeContent.innerHTML = `<div data-logic-id="narrative-text">${markdownToHtml(mind.narrative)}</div>`;
        } else {
            narrativeContent.innerHTML = '<p style="color: var(--text-dim);">点击上方"生成叙事"按钮生成内容</p>';
        }

        // 加载时间轴、结构和对话历史
        await Promise.all([
            loadTimeline(),
            loadStructure(),
            loadChatHistory()
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
        let isFirst = true;
        data.timeline.forEach(day => {
            html += `<div data-logic-id="timeline-day">
                <div data-logic-id="timeline-date">${day.date}</div>`;
            day.items.forEach(item => {
                const currentTag = isFirst ? '<span data-logic-id="timeline-current-tag">当前</span>' : '';
                html += `<div data-logic-id="timeline-item" data-feed-id="${item.id}"${isFirst ? ' data-current="true"' : ''}>
                    <div class="timeline-item-header">
                        <span data-logic-id="timeline-time">${item.time}${currentTag}</span>
                        <button class="timeline-menu-btn" onclick="toggleTimelineMenu(event, '${item.id}')">
                            <svg viewBox="0 0 24 24" width="16" height="16">
                                <circle cx="12" cy="5" r="1.5" fill="currentColor"/>
                                <circle cx="12" cy="12" r="1.5" fill="currentColor"/>
                                <circle cx="12" cy="19" r="1.5" fill="currentColor"/>
                            </svg>
                        </button>
                        <div class="timeline-dropdown" id="dropdown-${item.id}">
                            <button onclick="editTimelineItem('${item.id}')">编辑</button>
                            <button onclick="deleteTimelineItem('${item.id}')" class="delete-btn">删除</button>
                        </div>
                    </div>
                    <div data-logic-id="timeline-text">${escapeHtml(item.content)}</div>
                </div>`;
                isFirst = false;
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

// 切换时间轴菜单显示
function toggleTimelineMenu(event, feedId) {
    event.stopPropagation();

    // 关闭所有其他菜单
    document.querySelectorAll('.timeline-dropdown.show').forEach(d => {
        if (d.id !== `dropdown-${feedId}`) d.classList.remove('show');
    });

    const dropdown = document.getElementById(`dropdown-${feedId}`);
    dropdown.classList.toggle('show');
}

// 编辑时间轴项
function editTimelineItem(feedId) {
    // 关闭菜单
    document.querySelectorAll('.timeline-dropdown.show').forEach(d => d.classList.remove('show'));

    // 获取当前内容
    const item = document.querySelector(`[data-feed-id="${feedId}"]`);
    const content = item.querySelector('[data-logic-id="timeline-text"]').textContent;

    // 填充编辑弹窗
    document.getElementById('editFeedId').value = feedId;
    document.getElementById('editFeedContent').value = content;
    document.getElementById('editFeedModal').showModal();
}

// 保存编辑
async function saveTimelineEdit() {
    const feedId = document.getElementById('editFeedId').value;
    const content = document.getElementById('editFeedContent').value.trim();

    if (!content) {
        alert('内容不能为空');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/feeds/${feedId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            document.getElementById('editFeedModal').close();
            loadTimeline();  // 刷新时间轴
        } else {
            alert('保存失败');
        }
    } catch (error) {
        console.error('保存失败:', error);
        alert('保存失败');
    }
}

// 删除时间轴项
async function deleteTimelineItem(feedId) {
    // 关闭菜单
    document.querySelectorAll('.timeline-dropdown.show').forEach(d => d.classList.remove('show'));

    if (!confirm('确定要删除这条记录吗？')) return;

    try {
        const response = await fetch(`${API_BASE}/feeds/${feedId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadTimeline();  // 刷新时间轴
        } else {
            alert('删除失败');
        }
    } catch (error) {
        console.error('删除失败:', error);
        alert('删除失败');
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

            // 如果概述或标签有更新，刷新显示
            if (data.summary_changed || data.tags_changed) {
                updateSummaryAndTags(data.summary, data.tags);
                // 同时刷新列表（更新概述显示）
                loadMinds();
            }
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

// 删除 Mind
async function deleteMind(mindId) {
    if (!mindId) return;

    // 获取 Mind 标题用于确认
    const mindItem = document.querySelector(`[data-mind-id="${mindId}"]`);
    const title = mindItem ? mindItem.querySelector('h3')?.textContent : 'Mind';

    if (!confirm(`确定要删除「${title}」吗？\n\n此操作不可恢复，将删除所有相关的记录和数据。`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/minds/${mindId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // 如果删除的是当前选中的 Mind，重置状态
            if (currentMindId === mindId) {
                currentMindId = null;
                emptyState.style.display = 'flex';
                mindDetail.style.display = 'none';

                // 移动端：隐藏底部导航
                const bottomNav = document.getElementById('bottomNav');
                if (bottomNav) {
                    bottomNav.style.display = 'none';
                }

                // 移动端：重置标题
                const pageTitle = document.getElementById('pageTitle');
                if (pageTitle) {
                    pageTitle.textContent = 'MindLink';
                }
            }
            await loadMinds();
        } else {
            const error = await response.json();
            alert('删除失败: ' + (error.detail || '未知错误'));
        }
    } catch (error) {
        console.error('删除失败:', error);
        alert('删除失败，请重试');
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

            // 延迟更新状态文本
            setTimeout(() => {
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

// 切换标签页
function switchTab(tabName) {
    // 更新标签按钮状态（同时支持 data-active 和 class）
    document.querySelectorAll('[data-tab]').forEach(tab => {
        if (tab.dataset.tab === tabName) {
            tab.dataset.active = 'true';
            tab.classList.add('active');
        } else {
            delete tab.dataset.active;
            tab.classList.remove('active');
        }
    });

    // 更新内容显示（同时支持 style.display 和 CSS 类）
    const allTabs = ['feed', 'chat', 'timeline', 'narrative', 'structure', 'output'];
    allTabs.forEach(tab => {
        const element = document.getElementById(`${tab}Tab`);
        if (element) {
            if (tab === tabName) {
                // Chat Tab 需要 flex 布局
                element.style.display = (tab === 'chat') ? 'flex' : 'block';
                element.classList.add('active');
            } else {
                element.style.display = 'none';
                element.classList.remove('active');
            }
        }
    });

    // 切换到结构/时间轴 Tab 时，总是刷新最新数据
    if (currentMindId) {
        if (tabName === 'structure') {
            loadStructure();
        } else if (tabName === 'timeline') {
            loadTimeline();
        }
    }
}

// ========== 对话功能 ==========

// 加载对话历史
async function loadChatHistory() {
    if (!currentMindId) return;

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/chat/history`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();

        if (data.messages && data.messages.length > 0) {
            // 清空欢迎语，显示历史消息
            chatMessages.innerHTML = '';
            data.messages.forEach(msg => {
                addChatMessage(msg.role, msg.content);
            });
        } else {
            // 没有历史，显示欢迎语
            chatMessages.innerHTML = `
                <div data-logic-id="chat-welcome">
                    <p>我已经了解了你关于这个主题的所有想法。</p>
                    <p>有什么想和我讨论的吗？</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('加载对话历史失败:', error);
        chatMessages.innerHTML = `
            <div data-logic-id="chat-welcome">
                <p>我已经了解了你关于这个主题的所有想法。</p>
                <p>有什么想和我讨论的吗？</p>
            </div>
        `;
    }
}

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
async function clearChat() {
    if (!currentMindId) return;

    if (!confirm('确定要清空对话记录吗？此操作不可恢复。')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/chat/history`, {
            method: 'DELETE'
        });

        if (response.ok) {
            chatMessages.innerHTML = `
                <div data-logic-id="chat-welcome">
                    <p>我已经了解了你关于这个主题的所有想法。</p>
                    <p>有什么想和我讨论的吗？</p>
                </div>
            `;
        } else {
            alert('清空失败，请重试');
        }
    } catch (error) {
        console.error('清空对话失败:', error);
        alert('清空失败，请重试');
    }
}

// ========== 工具函数 ==========

// 更新概述和标签显示
function updateSummaryAndTags(summary, tags) {
    const summaryArea = document.getElementById('summaryArea');
    const aiBrief = document.getElementById('aiBrief');
    const tagCloud = document.getElementById('tagCloud');

    // 如果元素不存在（如移动端独立处理），跳过
    if (!summaryArea || !aiBrief || !tagCloud) return;

    // 如果有概述或标签，显示区域
    if (summary || (tags && tags.length > 0)) {
        summaryArea.style.display = 'block';

        // 显示概述
        if (summary) {
            aiBrief.textContent = summary;
            aiBrief.style.display = 'block';
        } else {
            aiBrief.style.display = 'none';
        }

        // 显示标签
        if (tags && tags.length > 0) {
            tagCloud.innerHTML = tags.map(tag =>
                `<span class="crystal-tag"># ${escapeHtml(tag)}</span>`
            ).join('');
            tagCloud.style.display = 'flex';
        } else {
            tagCloud.style.display = 'none';
        }
    } else {
        summaryArea.style.display = 'none';
    }
}

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
