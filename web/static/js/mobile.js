/**
 * ==========================================================================
 * MindLink Mobile - 业务逻辑层
 * ==========================================================================
 * 
 * 此文件为移动端专用，与桌面端 app.js 完全独立
 * API 基础路径: /api
 * 
 * 主要功能:
 * 1. Mind 管理 - 创建、读取、删除
 * 2. Feed 投喂 - 记录想法，AI 自动整理
 * 3. Chat 对话 - 与 AI 讨论当前主题
 * 4. Output 输出 - 按指令生成表达
 * 5. View 查看 - 结构、时间轴、叙事
 */

const API_BASE = '/api';
let currentMindId = null;

// ==================== DOM 元素引用 ====================
const els = {
    mindList: document.getElementById('mindList'),
    emptyState: document.getElementById('emptyState'),
    mindDetail: document.getElementById('mindDetail'),
    mindTitle: document.getElementById('mindTitle'),
    feedInput: document.getElementById('feedInput'),
    feedStatus: document.getElementById('feedStatus'),
    timelineContent: document.getElementById('timelineContent'),
    narrativeContent: document.getElementById('narrativeContent'),
    structureContent: document.getElementById('structureContent'),
    outputInstruction: document.getElementById('outputInstruction'),
    outputResult: document.getElementById('outputResult'),
    chatMessages: document.getElementById('chatMessages'),
    chatInput: document.getElementById('chatInput'),
    chatModel: document.getElementById('chatModel'),
    chatStyle: document.getElementById('chatStyle'),
    drawer: document.getElementById('drawer'),
    drawerOverlay: document.getElementById('drawerOverlay'),
    bottomNav: document.getElementById('bottomNav')
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    loadMinds();
    setupEventListeners();
    setupAutoResize();
    switchTab('feed');
});

// ==================== 事件监听器 ====================
function setupEventListeners() {
    // 导航 & 侧边栏
    document.getElementById('menuBtn').addEventListener('click', () => toggleDrawer(true));
    document.getElementById('closeDrawerBtn').addEventListener('click', () => toggleDrawer(false));
    els.drawerOverlay.addEventListener('click', () => toggleDrawer(false));

    // 创建 Mind
    const showCreate = () => {
        document.getElementById('createMindModal').showModal();
        document.getElementById('newMindTitle').focus();
    };
    document.getElementById('createMindBtn').addEventListener('click', showCreate);
    document.getElementById('emptyCreateBtn').addEventListener('click', showCreate);

    document.getElementById('modalCancelBtn').addEventListener('click', () => document.getElementById('createMindModal').close());
    document.getElementById('modalCreateBtn').addEventListener('click', createMind);
    document.getElementById('newMindTitle').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') createMind();
    });

    // Tab 切换
    document.getElementById('topTabs').addEventListener('click', (e) => {
        if (e.target.classList.contains('top-tab-btn')) switchTab(e.target.dataset.tab);
    });
    els.bottomNav.addEventListener('click', (e) => {
        const btn = e.target.closest('.bottom-nav-btn');
        if (btn) switchTab(btn.dataset.tab);
    });

    // 功能按钮
    document.getElementById('feedBtn').addEventListener('click', submitFeed);
    document.getElementById('generateNarrativeBtn').addEventListener('click', generateNarrative);
    document.getElementById('outputBtn').addEventListener('click', generateOutput);
    document.getElementById('sendChatBtn').addEventListener('click', sendChatMessage);
    document.getElementById('clearChatBtn').addEventListener('click', clearChat);

    // 输入快捷键
    els.feedInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submitFeed();
    });
    els.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
}

// ==================== Mind 管理 ====================

/**
 * 加载 Mind 列表
 * API: GET /api/minds
 */
async function loadMinds() {
    try {
        const response = await fetch(`${API_BASE}/minds`);
        const data = await response.json();

        els.mindList.innerHTML = '';
        if (!data.minds || data.minds.length === 0) {
            els.mindList.innerHTML = '<p style="color:var(--text-muted);text-align:center;margin-top:20px;">暂无晶体</p>';
            return;
        }

        data.minds.forEach(mind => {
            const item = document.createElement('div');
            item.dataset.mindId = mind.id;
            item.dataset.logicId = 'mind-list-item';
            if (mind.id === currentMindId) item.dataset.active = 'true';

            item.innerHTML = `
                <div class="mind-item-content">
                    <h3>${escapeHtml(mind.title)}</h3>
                    ${mind.summary ? `<p class="mind-summary">${escapeHtml(mind.summary)}</p>` : ''}
                    <span>${formatDate(mind.updated_at)}</span>
                </div>
                <button class="mind-delete-btn" title="删除">
                    <svg class="icon-svg" style="width:20px;height:20px" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
            `;

            item.querySelector('.mind-item-content').addEventListener('click', () => {
                selectMind(mind.id);
                toggleDrawer(false);
            });

            item.querySelector('.mind-delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                deleteMind(mind.id);
            });

            els.mindList.appendChild(item);
        });
    } catch (error) {
        console.error('加载失败:', error);
        els.mindList.innerHTML = '<p style="color:var(--accent-error);text-align:center;">连接失败</p>';
    }
}

/**
 * 选择 Mind
 * @param {string} mindId - Mind ID
 */
async function selectMind(mindId) {
    currentMindId = mindId;

    // 更新列表选中状态
    document.querySelectorAll('[data-logic-id="mind-list-item"]').forEach(item => {
        item.dataset.active = item.dataset.mindId === mindId ? 'true' : '';
    });

    // 显示详情区域
    els.emptyState.style.display = 'none';
    els.mindDetail.style.display = 'flex';
    els.mindDetail.hidden = false;
    els.bottomNav.classList.add('visible');

    // 重置 UI
    els.chatMessages.innerHTML = `
        <div data-logic-id="chat-welcome">
            <p>正在加载对话记录...</p>
        </div>`;
    els.outputResult.innerHTML = '<p style="color:var(--text-muted); text-align:center; padding-top:40px;">结构化输出将显示在这里</p>';

    try {
        const response = await fetch(`${API_BASE}/minds/${mindId}`);
        const mind = await response.json();

        els.mindTitle.textContent = mind.title;
        document.getElementById('pageTitle').textContent = mind.title;

        if (mind.narrative) {
            els.narrativeContent.innerHTML = markdownToHtml(mind.narrative);
        } else {
            els.narrativeContent.innerHTML = '<p style="color:var(--text-muted)">点击生成以构建叙事</p>';
        }

        await Promise.all([loadTimeline(), loadStructure(), loadChatHistory()]);
    } catch (error) {
        console.error('加载 Mind 详情失败:', error);
    }
}

/**
 * 创建 Mind
 * API: POST /api/minds
 */
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
            document.getElementById('createMindModal').close();
            document.getElementById('newMindTitle').value = '';
            await loadMinds();
            selectMind(mind.id);
        }
    } catch (error) {
        console.error('创建失败:', error);
    }
}

/**
 * 删除 Mind
 * API: DELETE /api/minds/{mindId}
 */
async function deleteMind(mindId) {
    if (!confirm('确定要删除这个思维晶体吗？')) return;

    try {
        const response = await fetch(`${API_BASE}/minds/${mindId}`, { method: 'DELETE' });
        if (response.ok) {
            if (currentMindId === mindId) {
                currentMindId = null;
                els.emptyState.style.display = 'flex';
                els.mindDetail.style.display = 'none';
                els.bottomNav.classList.remove('visible');
                document.getElementById('pageTitle').textContent = 'MindLink';
            }
            await loadMinds();
        }
    } catch (error) {
        console.error('删除失败:', error);
    }
}

// ==================== Feed 投喂 ====================

/**
 * 提交投喂
 * API: POST /api/minds/{mindId}/feed
 */
async function submitFeed() {
    if (!currentMindId) return;
    const content = els.feedInput.value.trim();
    if (!content) return;

    const btn = document.getElementById('feedBtn');
    btn.style.opacity = '0.5';
    els.feedStatus.textContent = '正在晶体化...';

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/feed`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            els.feedInput.value = '';
            els.feedInput.style.height = 'auto';
            els.feedStatus.textContent = '已存入晶体网络';
            setTimeout(() => els.feedStatus.textContent = '', 2000);
            loadMinds();
        } else {
            els.feedStatus.textContent = '提交失败';
        }
    } catch (error) {
        els.feedStatus.textContent = '网络错误';
    } finally {
        btn.style.opacity = '1';
    }
}

// ==================== 查看功能 ====================

/**
 * 加载时间轴
 * API: GET /api/minds/{mindId}/timeline-view
 */
async function loadTimeline() {
    if (!currentMindId) return;

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/timeline-view`);
        const data = await response.json();

        if (!data.timeline || data.timeline.length === 0) {
            els.timelineContent.innerHTML = '<p style="color:var(--text-muted)">暂无记录</p>';
            return;
        }

        let html = '';
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
        els.timelineContent.innerHTML = html;
    } catch (error) {
        els.timelineContent.innerHTML = '<p>加载失败</p>';
    }
}

/**
 * 加载结构视图
 * API: GET /api/minds/{mindId}/crystal
 */
async function loadStructure() {
    if (!currentMindId) return;

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/crystal`);
        const data = await response.json();
        els.structureContent.innerHTML = data.structure_markdown
            ? markdownToHtml(data.structure_markdown)
            : '<p style="color:var(--text-muted)">等待生成结构...</p>';
    } catch (error) {
        els.structureContent.innerHTML = '<p>加载失败</p>';
    }
}

/**
 * 生成叙事
 * API: POST /api/minds/{mindId}/narrative
 */
async function generateNarrative() {
    if (!currentMindId) return;

    const btn = document.getElementById('generateNarrativeBtn');
    btn.disabled = true;
    btn.textContent = '计算中...';
    els.narrativeContent.classList.add('loading-pulse');

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/narrative`, { method: 'POST' });
        const data = await response.json();
        els.narrativeContent.innerHTML = markdownToHtml(data.narrative || '生成为空');
        loadMinds();
    } catch (error) {
        els.narrativeContent.innerHTML = '生成失败';
    } finally {
        btn.disabled = false;
        btn.textContent = '重新生成';
        els.narrativeContent.classList.remove('loading-pulse');
    }
}

/**
 * 生成输出
 * API: POST /api/minds/{mindId}/output
 */
async function generateOutput() {
    if (!currentMindId) return;
    const instruction = els.outputInstruction.value.trim();
    if (!instruction) return;

    const btn = document.getElementById('outputBtn');
    btn.disabled = true;
    btn.textContent = '...';
    els.outputResult.classList.add('loading-pulse');

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/output`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instruction })
        });
        const data = await response.json();
        els.outputResult.innerHTML = `<div>${markdownToHtml(data.content)}</div>`;
    } catch (error) {
        els.outputResult.innerHTML = '生成失败';
    } finally {
        btn.disabled = false;
        btn.textContent = '生成';
        els.outputResult.classList.remove('loading-pulse');
    }
}

// ==================== Chat 对话 ====================

/**
 * 加载对话历史
 * API: GET /api/minds/{mindId}/chat/history
 */
async function loadChatHistory() {
    if (!currentMindId) return;

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/chat/history`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        if (data.messages && data.messages.length > 0) {
            els.chatMessages.innerHTML = '';
            data.messages.forEach(msg => {
                addChatMessage(msg.role, msg.content);
            });
        } else {
            els.chatMessages.innerHTML = `
                <div data-logic-id="chat-welcome">
                    <p>思维网络已连接。</p><p>准备好进行深层链接。</p>
                </div>`;
        }
    } catch (error) {
        console.error('加载对话历史失败:', error);
        els.chatMessages.innerHTML = `
            <div data-logic-id="chat-welcome">
                <p>思维网络已连接。</p><p>准备好进行深层链接。</p>
            </div>`;
    }
}

/**
 * 发送对话消息
 * API: POST /api/minds/{mindId}/chat
 */
async function sendChatMessage() {
    if (!currentMindId) return;
    const message = els.chatInput.value.trim();
    if (!message) return;

    els.chatInput.value = '';
    els.chatInput.style.height = 'auto';
    addChatMessage('user', message);

    const loadingId = addChatMessage('assistant', '<span class="loading-pulse">Thinking...</span>', true);

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                model: els.chatModel.value,
                style: els.chatStyle.value
            })
        });

        removeChatMessage(loadingId);

        if (response.ok) {
            const data = await response.json();
            addChatMessage('assistant', data.reply);
        } else {
            addChatMessage('assistant', '连接断开');
        }
    } catch (error) {
        removeChatMessage(loadingId);
        addChatMessage('assistant', '网络异常');
    }
}

function addChatMessage(role, content, isHtml = false) {
    const welcome = els.chatMessages.querySelector('[data-logic-id="chat-welcome"]');
    if (welcome) welcome.style.display = 'none';

    const div = document.createElement('div');
    div.dataset.logicId = 'chat-message';
    div.dataset.role = role;
    div.innerHTML = isHtml ? content : (role === 'user' ? escapeHtml(content) : markdownToHtml(content));
    div.id = `msg_${Date.now()}`;

    els.chatMessages.appendChild(div);
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    return div.id;
}

function removeChatMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

async function clearChat() {
    if (!currentMindId) return;
    if (!confirm('确定要清空对话记录吗？此操作不可恢复。')) return;

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/chat/history`, {
            method: 'DELETE'
        });

        if (response.ok) {
            els.chatMessages.innerHTML = `
                <div data-logic-id="chat-welcome">
                    <p>记忆已重置。</p>
                </div>`;
        } else {
            alert('清空失败，请重试');
        }
    } catch (error) {
        console.error('清空对话失败:', error);
        alert('清空失败，请重试');
    }
}

// ==================== UI 控制 ====================

/**
 * 切换分页
 * @param {string} tabName - feed/chat/output/structure/timeline/narrative
 */
function switchTab(tabName) {
    // 更新顶部 Tab 按钮
    document.querySelectorAll('.top-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // 更新底部导航按钮
    document.querySelectorAll('.bottom-nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // 显示对应内容
    ['feed', 'chat', 'timeline', 'narrative', 'structure', 'output'].forEach(t => {
        const el = document.getElementById(`${t}Tab`);
        if (el) {
            const wasActive = el.classList.contains('active');
            if (t === tabName && !wasActive) {
                el.classList.add('active');
                if (t === 'feed') setTimeout(() => els.feedInput.focus(), 100);
            } else if (t !== tabName) {
                el.classList.remove('active');
            }
        }
    });

    // 切换到查看类 Tab 时自动加载数据
    if (currentMindId) {
        if (tabName === 'structure') loadStructure();
        else if (tabName === 'timeline') loadTimeline();
    }
}

/**
 * 切换侧边栏
 * @param {boolean} open - 是否打开
 */
function toggleDrawer(open) {
    if (open) {
        els.drawer.classList.add('open');
        els.drawerOverlay.classList.add('show');
    } else {
        els.drawer.classList.remove('open');
        els.drawerOverlay.classList.remove('show');
    }
}

/**
 * 输入框自动调整高度
 */
function setupAutoResize() {
    const resize = (el) => {
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 150) + 'px';
    };
    els.feedInput.addEventListener('input', () => resize(els.feedInput));
    els.chatInput.addEventListener('input', () => resize(els.chatInput));
}

// ==================== 工具函数 ====================

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

function markdownToHtml(md) {
    if (!md) return '';
    return md
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/\n\n/g, '<br><br>')
        .replace(/\n/g, '<br>');
}
