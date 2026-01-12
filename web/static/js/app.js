/**
 * MindLink PC 端应用
 *
 * 架构：IIFE 封装，避免全局污染
 * 状态：currentMindId
 * DOM：集中缓存在 dom 对象
 */

const MindLinkApp = (function () {
    'use strict';

    // ========== 配置 ==========
    const API_BASE = '/api';

    // ========== 状态 ==========
    let currentMindId = null;

    // ========== DOM 缓存 ==========
    const dom = {};

    function cacheDOM() {
        // 侧边栏
        dom.mindList = document.getElementById('mindList');
        dom.createMindBtn = document.getElementById('createMindBtn');
        dom.currentUser = document.getElementById('currentUser');
        dom.adminLink = document.getElementById('adminLink');
        dom.logoutBtn = document.getElementById('logoutBtn');

        // 主内容区
        dom.emptyState = document.getElementById('emptyState');
        dom.mindDetail = document.getElementById('mindDetail');
        dom.mindTitle = document.getElementById('mindTitle');
        dom.summaryArea = document.getElementById('summaryArea');
        dom.aiBrief = document.getElementById('aiBrief');
        dom.tagCloud = document.getElementById('tagCloud');

        // 投喂
        dom.feedInput = document.getElementById('feedInput');
        dom.feedBtn = document.getElementById('feedBtn');
        dom.feedStatus = document.getElementById('feedStatus');

        // 时间轴
        dom.timelineContent = document.getElementById('timelineContent');

        // 结构
        dom.structureContent = document.getElementById('structureContent');

        // 叙事
        dom.narrativeContent = document.getElementById('narrativeContent');
        dom.generateNarrativeBtn = document.getElementById('generateNarrativeBtn');

        // 输出
        dom.outputInstruction = document.getElementById('outputInstruction');
        dom.outputBtn = document.getElementById('outputBtn');
        dom.outputResult = document.getElementById('outputResult');

        // 对话
        dom.chatMessages = document.getElementById('chatMessages');
        dom.chatInput = document.getElementById('chatInput');
        dom.chatModel = document.getElementById('chatModel');
        dom.chatStyle = document.getElementById('chatStyle');
        dom.sendChatBtn = document.getElementById('sendChatBtn');
        dom.clearChatBtn = document.getElementById('clearChatBtn');

        // 模态框 - 创建 Mind
        dom.createMindModal = document.getElementById('createMindModal');
        dom.newMindTitle = document.getElementById('newMindTitle');
        dom.modalCancelBtn = document.getElementById('modalCancelBtn');
        dom.modalCreateBtn = document.getElementById('modalCreateBtn');

        // 模态框 - 编辑记录
        dom.editFeedModal = document.getElementById('editFeedModal');
        dom.editFeedId = document.getElementById('editFeedId');
        dom.editFeedContent = document.getElementById('editFeedContent');
        dom.editCancelBtn = document.getElementById('editCancelBtn');
        dom.editSaveBtn = document.getElementById('editSaveBtn');
    }

    // ========== 事件绑定 ==========
    function bindEvents() {
        // 创建 Mind
        dom.createMindBtn.addEventListener('click', openCreateModal);
        dom.modalCancelBtn.addEventListener('click', closeCreateModal);
        dom.modalCreateBtn.addEventListener('click', createMind);
        dom.newMindTitle.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') createMind();
        });

        // 退出登录
        dom.logoutBtn.addEventListener('click', logout);

        // 投喂
        dom.feedBtn.addEventListener('click', submitFeed);
        dom.feedInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submitFeed();
        });

        // 叙事
        dom.generateNarrativeBtn.addEventListener('click', generateNarrative);

        // 输出
        dom.outputBtn.addEventListener('click', generateOutput);
        dom.outputInstruction.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') generateOutput();
        });

        // 对话
        dom.sendChatBtn.addEventListener('click', sendChatMessage);
        dom.clearChatBtn.addEventListener('click', clearChat);

        // 输入法状态跟踪（解决中文输入法确认候选词误触发发送问题）
        let isComposing = false;
        dom.chatInput.addEventListener('compositionstart', () => {
            isComposing = true;
        });
        dom.chatInput.addEventListener('compositionend', () => {
            isComposing = false;
        });
        dom.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
                e.preventDefault();
                sendChatMessage();
            }
        });

        // 编辑记录模态框
        dom.editCancelBtn.addEventListener('click', () => dom.editFeedModal.close());
        dom.editSaveBtn.addEventListener('click', saveTimelineEdit);

        // Tab 切换
        document.querySelectorAll('.tabs__btn').forEach(btn => {
            btn.addEventListener('click', () => switchTab(btn.dataset.tab));
        });

        // 点击空白处关闭下拉菜单
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.timeline__menu-btn') && !e.target.closest('.timeline__dropdown')) {
                document.querySelectorAll('.timeline__dropdown.is-open').forEach(d => d.classList.remove('is-open'));
            }
        });
    }

    // ========== 用户信息 ==========
    async function loadUserInfo() {
        try {
            const response = await fetch(`${API_BASE}/auth/me`, { credentials: 'same-origin' });
            const data = await response.json();

            if (data.logged_in && data.user) {
                dom.currentUser.textContent = data.user.username;
                if (data.user.is_admin) {
                    dom.adminLink.hidden = false;
                }
            }
        } catch (err) {
            console.error('加载用户信息失败:', err);
        }
    }

    async function logout() {
        try {
            await fetch(`${API_BASE}/auth/logout`, { method: 'POST', credentials: 'same-origin' });
            window.location.href = '/login';
        } catch (err) {
            console.error('退出登录失败:', err);
        }
    }

    // ========== Mind 管理 ==========
    async function loadMinds() {
        try {
            const response = await fetch(`${API_BASE}/minds`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();

            dom.mindList.innerHTML = '';

            if (data.minds.length === 0) {
                dom.mindList.innerHTML = '<p class="text-dim text-center" style="padding: 1rem;">还没有 Mind，创建一个吧</p>';
                return;
            }

            data.minds.forEach(mind => {
                const item = document.createElement('div');
                item.className = 'mind-item' + (mind.id === currentMindId ? ' is-active' : '');
                item.dataset.mindId = mind.id;

                const summaryHtml = mind.summary
                    ? `<p class="mind-item__summary">${escapeHtml(mind.summary)}</p>`
                    : '';

                item.innerHTML = `
                    <div class="mind-item__content">
                        <h3 class="mind-item__title">${escapeHtml(mind.title)}</h3>
                        ${summaryHtml}
                        <span class="mind-item__date">${formatDate(mind.updated_at)}</span>
                    </div>
                    <button class="mind-item__delete" title="删除">×</button>
                `;

                item.querySelector('.mind-item__content').addEventListener('click', () => selectMind(mind.id));
                item.querySelector('.mind-item__delete').addEventListener('click', (e) => {
                    e.stopPropagation();
                    deleteMind(mind.id);
                });

                dom.mindList.appendChild(item);
            });
        } catch (error) {
            console.error('加载失败:', error);
        }
    }

    async function selectMind(mindId) {
        currentMindId = mindId;

        // 更新列表选中状态
        document.querySelectorAll('.mind-item').forEach(item => {
            item.classList.toggle('is-active', item.dataset.mindId === mindId);
        });

        // 显示详情
        dom.emptyState.hidden = true;
        dom.mindDetail.hidden = false;

        // 清空输出内容
        dom.outputResult.innerHTML = '';

        // 显示加载状态
        dom.chatMessages.innerHTML = '<div class="chat__welcome"><p>正在加载对话记录...</p></div>';

        try {
            const response = await fetch(`${API_BASE}/minds/${mindId}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const mind = await response.json();

            dom.mindTitle.textContent = mind.title;
            updateSummaryAndTags(mind.summary, mind.tags);

            // 显示已保存的叙事
            if (mind.narrative) {
                dom.narrativeContent.innerHTML = `<div class="narrative__card">${markdownToHtml(mind.narrative)}</div>`;
            } else {
                dom.narrativeContent.innerHTML = '<p class="text-dim">点击上方"生成叙事"按钮生成内容</p>';
            }

            // 并行加载时间轴、结构和对话历史
            await Promise.all([
                loadTimeline(),
                loadStructure(),
                loadChatHistory()
            ]);
        } catch (error) {
            console.error('加载失败:', error);
        }
    }

    async function createMind() {
        const title = dom.newMindTitle.value.trim();
        if (!title) return;

        try {
            const response = await fetch(`${API_BASE}/minds`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            });

            if (response.ok) {
                const mind = await response.json();
                closeCreateModal();
                dom.newMindTitle.value = '';
                await loadMinds();
                selectMind(mind.id);
            }
        } catch (error) {
            console.error('创建失败:', error);
        }
    }

    async function deleteMind(mindId) {
        const mindItem = document.querySelector(`[data-mind-id="${mindId}"]`);
        const title = mindItem?.querySelector('.mind-item__title')?.textContent || 'Mind';

        if (!confirm(`确定要删除「${title}」吗？\n\n此操作不可恢复，将删除所有相关的记录和数据。`)) {
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/minds/${mindId}`, { method: 'DELETE' });

            if (response.ok) {
                if (currentMindId === mindId) {
                    currentMindId = null;
                    dom.emptyState.hidden = false;
                    dom.mindDetail.hidden = true;
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

    function openCreateModal() {
        dom.createMindModal.showModal();
        dom.newMindTitle.focus();
    }

    function closeCreateModal() {
        dom.createMindModal.close();
    }

    // ========== Tab 切换 ==========
    function switchTab(tabName) {
        // 更新按钮状态
        document.querySelectorAll('.tabs__btn').forEach(btn => {
            btn.classList.toggle('is-active', btn.dataset.tab === tabName);
        });

        // 更新内容显示
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.toggle('is-active', pane.id === `${tabName}Tab`);
        });

        // 懒加载数据
        if (currentMindId) {
            if (tabName === 'structure') loadStructure();
            if (tabName === 'timeline') loadTimeline();
        }
    }

    // ========== 投喂 ==========
    async function submitFeed() {
        if (!currentMindId) return;

        const content = dom.feedInput.value.trim();
        if (!content) return;

        dom.feedBtn.disabled = true;
        dom.feedStatus.textContent = '正在处理...';

        try {
            const response = await fetch(`${API_BASE}/minds/${currentMindId}/feed`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });

            if (response.ok) {
                dom.feedInput.value = '';
                dom.feedStatus.textContent = '已记录，正在去噪和更新结构...';
                setTimeout(() => { dom.feedStatus.textContent = '处理完成'; }, 3000);
                loadMinds();
            } else {
                dom.feedStatus.textContent = '提交失败';
            }
        } catch (error) {
            console.error('投喂失败:', error);
            dom.feedStatus.textContent = '提交失败';
        } finally {
            dom.feedBtn.disabled = false;
        }
    }

    // ========== 时间轴 ==========
    async function loadTimeline() {
        if (!currentMindId) return;

        try {
            const response = await fetch(`${API_BASE}/minds/${currentMindId}/timeline-view`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();

            if (!data.timeline || data.timeline.length === 0) {
                dom.timelineContent.innerHTML = '<p class="text-dim text-center">还没有内容，先投喂一些想法吧</p>';
                return;
            }

            let html = '';
            let isFirst = true;

            data.timeline.forEach(day => {
                html += `<div class="timeline__date">${day.date}</div>`;

                day.items.forEach(item => {
                    const currentTag = isFirst ? '<span class="timeline__tag">当前</span>' : '';

                    html += `
                        <div class="timeline__item" data-feed-id="${item.id}">
                            <div class="timeline__item-card">
                                <div class="timeline__item-header">
                                    <span class="timeline__time">${item.time}${currentTag}</span>
                                    <button class="timeline__menu-btn" data-feed-id="${item.id}">
                                        <svg viewBox="0 0 24 24" width="14" height="14">
                                            <circle cx="12" cy="5" r="1.5" fill="currentColor"/>
                                            <circle cx="12" cy="12" r="1.5" fill="currentColor"/>
                                            <circle cx="12" cy="19" r="1.5" fill="currentColor"/>
                                        </svg>
                                    </button>
                                    <div class="timeline__dropdown" data-dropdown-id="${item.id}">
                                        <button class="timeline__dropdown-btn" data-action="edit" data-feed-id="${item.id}">编辑</button>
                                        <button class="timeline__dropdown-btn timeline__dropdown-btn--danger" data-action="delete" data-feed-id="${item.id}">删除</button>
                                    </div>
                                </div>
                                <div class="timeline__text">${escapeHtml(item.content)}</div>
                            </div>
                        </div>
                    `;
                    isFirst = false;
                });
            });

            dom.timelineContent.innerHTML = html;

            // 绑定菜单事件
            dom.timelineContent.querySelectorAll('.timeline__menu-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    toggleTimelineMenu(btn.dataset.feedId);
                });
            });

            dom.timelineContent.querySelectorAll('.timeline__dropdown-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const feedId = btn.dataset.feedId;
                    if (btn.dataset.action === 'edit') {
                        editTimelineItem(feedId);
                    } else if (btn.dataset.action === 'delete') {
                        deleteTimelineItem(feedId);
                    }
                });
            });

        } catch (error) {
            console.error('加载时间轴失败:', error);
            dom.timelineContent.innerHTML = '<p>加载失败</p>';
        }
    }

    function toggleTimelineMenu(feedId) {
        // 关闭其他菜单
        document.querySelectorAll('.timeline__dropdown.is-open').forEach(d => {
            if (d.dataset.dropdownId !== feedId) d.classList.remove('is-open');
        });

        const dropdown = document.querySelector(`[data-dropdown-id="${feedId}"]`);
        if (dropdown) dropdown.classList.toggle('is-open');
    }

    function editTimelineItem(feedId) {
        document.querySelectorAll('.timeline__dropdown.is-open').forEach(d => d.classList.remove('is-open'));

        const item = document.querySelector(`[data-feed-id="${feedId}"].timeline__item`);
        const content = item?.querySelector('.timeline__text')?.textContent || '';

        dom.editFeedId.value = feedId;
        dom.editFeedContent.value = content;
        dom.editFeedModal.showModal();
    }

    async function saveTimelineEdit() {
        const feedId = dom.editFeedId.value;
        const content = dom.editFeedContent.value.trim();

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
                dom.editFeedModal.close();
                loadTimeline();
            } else {
                alert('保存失败');
            }
        } catch (error) {
            console.error('保存失败:', error);
            alert('保存失败');
        }
    }

    async function deleteTimelineItem(feedId) {
        document.querySelectorAll('.timeline__dropdown.is-open').forEach(d => d.classList.remove('is-open'));

        if (!confirm('确定要删除这条记录吗？')) return;

        try {
            const response = await fetch(`${API_BASE}/feeds/${feedId}`, { method: 'DELETE' });
            if (response.ok) {
                loadTimeline();
            } else {
                alert('删除失败');
            }
        } catch (error) {
            console.error('删除失败:', error);
            alert('删除失败');
        }
    }

    // ========== 结构 ==========
    async function loadStructure() {
        if (!currentMindId) return;

        try {
            const response = await fetch(`${API_BASE}/minds/${currentMindId}/crystal`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();

            if (!data.structure_markdown || data.structure_markdown === '还没有内容，先投喂一些想法吧') {
                dom.structureContent.innerHTML = '<p class="text-dim text-center">还没有内容，先投喂一些想法吧</p>';
                return;
            }

            dom.structureContent.innerHTML = markdownToHtml(data.structure_markdown);
        } catch (error) {
            console.error('加载结构失败:', error);
            dom.structureContent.innerHTML = '<p>加载失败</p>';
        }
    }

    // ========== 叙事 ==========
    async function generateNarrative() {
        if (!currentMindId) return;

        dom.generateNarrativeBtn.disabled = true;
        dom.generateNarrativeBtn.textContent = '生成中...';
        dom.narrativeContent.innerHTML = '<p class="text-dim">正在整合所有记录，生成叙事...</p>';

        try {
            const response = await fetch(`${API_BASE}/minds/${currentMindId}/narrative`, { method: 'POST' });
            const data = await response.json();

            if (data.narrative) {
                dom.narrativeContent.innerHTML = `<div class="narrative__card">${markdownToHtml(data.narrative)}</div>`;

                if (data.summary_changed || data.tags_changed) {
                    updateSummaryAndTags(data.summary, data.tags);
                    loadMinds();
                }
            } else {
                dom.narrativeContent.innerHTML = '<p>暂无内容</p>';
            }
        } catch (error) {
            console.error('生成叙事失败:', error);
            dom.narrativeContent.innerHTML = '<p>生成失败</p>';
        } finally {
            dom.generateNarrativeBtn.disabled = false;
            dom.generateNarrativeBtn.textContent = '生成叙事';
        }
    }

    // ========== 输出 ==========
    async function generateOutput() {
        if (!currentMindId) return;

        const instruction = dom.outputInstruction.value.trim();
        if (!instruction) return;

        dom.outputBtn.disabled = true;
        dom.outputResult.innerHTML = '<p class="text-dim">正在生成...</p>';

        try {
            const response = await fetch(`${API_BASE}/minds/${currentMindId}/output`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ instruction })
            });

            if (response.ok) {
                const data = await response.json();
                dom.outputResult.innerHTML = `<div class="output__card">${escapeHtml(data.content)}</div>`;
            } else {
                const error = await response.json();
                dom.outputResult.innerHTML = `<p>${error.detail || '生成失败'}</p>`;
            }
        } catch (error) {
            console.error('生成失败:', error);
            dom.outputResult.innerHTML = '<p>生成失败</p>';
        } finally {
            dom.outputBtn.disabled = false;
        }
    }

    // ========== 对话 ==========
    async function loadChatHistory() {
        if (!currentMindId) return;

        try {
            const response = await fetch(`${API_BASE}/minds/${currentMindId}/chat/history`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();

            if (data.messages && data.messages.length > 0) {
                dom.chatMessages.innerHTML = '';
                data.messages.forEach(msg => addChatMessage(msg.role, msg.content));
            } else {
                showChatWelcome();
            }
        } catch (error) {
            console.error('加载对话历史失败:', error);
            showChatWelcome();
        }
    }

    function showChatWelcome() {
        dom.chatMessages.innerHTML = `
            <div class="chat__welcome">
                <p>我已经了解了你关于这个主题的所有想法。</p>
                <p>有什么想和我讨论的吗？</p>
            </div>
        `;
    }

    async function sendChatMessage() {
        if (!currentMindId) return;

        const message = dom.chatInput.value.trim();
        if (!message) return;

        dom.sendChatBtn.disabled = true;

        // 添加用户消息
        addChatMessage('user', message);
        dom.chatInput.value = '';

        // 添加加载状态
        const loadingId = addChatMessage('assistant', '思考中...', true);

        try {
            const response = await fetch(`${API_BASE}/minds/${currentMindId}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    model: dom.chatModel.value,
                    style: dom.chatStyle.value
                })
            });

            removeChatMessage(loadingId);

            if (response.ok) {
                const data = await response.json();
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
            dom.sendChatBtn.disabled = false;
            dom.chatInput.focus();
        }
    }

    function addChatMessage(role, content, isLoading = false) {
        // 隐藏欢迎语
        const welcome = dom.chatMessages.querySelector('.chat__welcome');
        if (welcome) welcome.style.display = 'none';

        const messageId = `msg_${Date.now()}`;
        const messageDiv = document.createElement('div');
        messageDiv.id = messageId;
        messageDiv.className = 'chat__message' + (role === 'user' ? ' chat__message--user' : ' chat__message--assistant');

        const contentHtml = role === 'user' ? escapeHtml(content) : markdownToHtml(content);

        if (role === 'user') {
            messageDiv.innerHTML = `<div class="chat__bubble">${contentHtml}</div>`;
        } else {
            messageDiv.innerHTML = `
                <div class="chat__avatar">AI</div>
                <div class="chat__bubble">${contentHtml}</div>
            `;
        }

        dom.chatMessages.appendChild(messageDiv);
        dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;

        return messageId;
    }

    function removeChatMessage(messageId) {
        const message = document.getElementById(messageId);
        if (message) message.remove();
    }

    async function clearChat() {
        if (!currentMindId) return;
        if (!confirm('确定要清空对话记录吗？此操作不可恢复。')) return;

        try {
            const response = await fetch(`${API_BASE}/minds/${currentMindId}/chat/history`, { method: 'DELETE' });
            if (response.ok) {
                showChatWelcome();
            } else {
                alert('清空失败，请重试');
            }
        } catch (error) {
            console.error('清空对话失败:', error);
            alert('清空失败，请重试');
        }
    }

    // ========== 工具函数 ==========
    function updateSummaryAndTags(summary, tags) {
        if (summary || (tags && tags.length > 0)) {
            dom.summaryArea.hidden = false;

            if (summary) {
                dom.aiBrief.textContent = summary;
                dom.aiBrief.hidden = false;
            } else {
                dom.aiBrief.hidden = true;
            }

            if (tags && tags.length > 0) {
                dom.tagCloud.innerHTML = tags.map(tag =>
                    `<span class="tag"># ${escapeHtml(tag)}</span>`
                ).join('');
                dom.tagCloud.hidden = false;
            } else {
                dom.tagCloud.hidden = true;
            }
        } else {
            dom.summaryArea.hidden = true;
        }
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

        let html = markdown
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        html = html
            .replace(/^### (.+)$/gm, '<h4>$1</h4>')
            .replace(/^## (.+)$/gm, '<h3>$1</h3>')
            .replace(/^# (.+)$/gm, '<h2>$1</h2>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/^\* (.+)$/gm, '<li>$1</li>')
            .replace(/^- (.+)$/gm, '<li>$1</li>')
            .replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

        html = html.replace(/(<li>.*<\/li>\n?)+/gs, match => `<ul>${match}</ul>`);

        html = html
            .replace(/<\/h[234]>\n/g, '</h$&>')
            .replace(/<\/ul>\n/g, '</ul>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');

        if (!html.startsWith('<h') && !html.startsWith('<ul')) {
            html = '<p>' + html + '</p>';
        }

        return html;
    }

    // ========== 思维导图模态框 ==========
    function initMindmapModal() {
        const openBtn = document.getElementById('openMindmapBtn');
        const modal = document.getElementById('mindmapModal');
        const closeBtn = document.getElementById('closeMindmapBtn');
        const iframe = document.getElementById('mindmapFrame');

        if (!openBtn || !modal || !closeBtn || !iframe) {
            console.log('思维导图元素未找到');
            return;
        }

        // 打开模态框
        function openMindmap() {
            console.log('打开思维导图');
            const mindId = currentMindId || localStorage.getItem('currentMindId');
            // 添加时间戳防止浏览器缓存
            iframe.src = `/mindmap?mind_id=${mindId}&t=${Date.now()}`;
            modal.showModal();
        }

        // 关闭模态框
        function closeMindmap() {
            console.log('关闭思维导图');
            modal.close();
            iframe.src = '';
        }

        // 绑定事件
        openBtn.addEventListener('click', openMindmap);
        closeBtn.addEventListener('click', closeMindmap);

        // ESC键关闭
        modal.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeMindmap();
        });

        // 点击遮罩层关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeMindmap();
        });

        console.log('思维导图模态框已初始化');
    }

    // ========== 初始化 ==========
    function init() {
        cacheDOM();
        bindEvents();
        loadUserInfo();
        loadMinds();
        switchTab('feed');
        initMindmapModal();
    }

    // 暴露公共接口
    return { init };
})();

// 启动应用
document.addEventListener('DOMContentLoaded', MindLinkApp.init);

