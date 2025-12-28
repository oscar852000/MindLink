/**
 * MindLink 前端应用
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
const crystalContent = document.getElementById('crystalContent');
const outputInstruction = document.getElementById('outputInstruction');
const outputResult = document.getElementById('outputResult');
const clarifyQuestions = document.getElementById('clarifyQuestions');

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

    // 输出按钮
    document.getElementById('outputBtn').addEventListener('click', generateOutput);

    // 澄清按钮
    document.getElementById('clarifyBtn').addEventListener('click', loadClarifyQuestions);

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

    // 更新列表选中状态
    document.querySelectorAll('.mind-item').forEach(item => {
        item.classList.toggle('active', item.dataset.mindId === mindId);
    });

    // 显示详情
    emptyState.style.display = 'none';
    mindDetail.style.display = 'flex';

    // 加载详情
    try {
        const response = await fetch(`${API_BASE}/minds/${mindId}`);
        const mind = await response.json();

        mindTitle.textContent = mind.title;

        // 加载 Crystal
        await loadCrystal();
    } catch (error) {
        console.error('加载失败:', error);
    }
}

// 加载 Crystal
async function loadCrystal() {
    if (!currentMindId) return;

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/crystal`);
        const data = await response.json();

        if (data.crystal_markdown) {
            crystalContent.innerHTML = `<div class="crystal-text">${markdownToHtml(data.crystal_markdown)}</div>`;
        } else {
            crystalContent.innerHTML = '<p class="placeholder">还没有内容，先投喂一些想法吧</p>';
        }
    } catch (error) {
        console.error('加载 Crystal 失败:', error);
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
    document.getElementById('newMindTitle').value = '';
}

// 提交投喂
async function submitFeed() {
    if (!currentMindId) return;

    const content = feedInput.value.trim();
    if (!content) return;

    const btn = document.getElementById('feedBtn');
    btn.disabled = true;
    btn.textContent = '记录中...';

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/feed`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            feedInput.value = '';
            feedStatus.textContent = '✓ 已记录';
            feedStatus.className = 'feed-status success';

            // 刷新 Crystal
            await loadCrystal();
            await loadMinds();

            // 3秒后清除状态
            setTimeout(() => {
                feedStatus.textContent = '';
                feedStatus.className = 'feed-status';
            }, 3000);
        }
    } catch (error) {
        console.error('投喂失败:', error);
        feedStatus.textContent = '投喂失败，请重试';
        feedStatus.className = 'feed-status error';
    } finally {
        btn.disabled = false;
        btn.textContent = '投喂';
    }
}

// 生成输出
async function generateOutput() {
    if (!currentMindId) return;

    const instruction = outputInstruction.value.trim();
    if (!instruction) return;

    const btn = document.getElementById('outputBtn');
    btn.disabled = true;
    btn.textContent = '生成中...';
    outputResult.textContent = '正在生成...';

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/output`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instruction })
        });

        if (response.ok) {
            const data = await response.json();
            outputResult.textContent = data.content;
        } else {
            const error = await response.json();
            outputResult.textContent = '生成失败: ' + (error.detail || '未知错误');
        }
    } catch (error) {
        console.error('生成失败:', error);
        outputResult.textContent = '生成失败，请重试';
    } finally {
        btn.disabled = false;
        btn.textContent = '生成';
    }
}

// ========== 澄清功能 ==========

// 加载澄清问题
async function loadClarifyQuestions() {
    if (!currentMindId) return;

    const btn = document.getElementById('clarifyBtn');
    btn.disabled = true;
    btn.textContent = '分析中...';
    clarifyQuestions.innerHTML = '<p class="loading">AI 正在分析你的想法...</p>';

    try {
        const response = await fetch(`${API_BASE}/minds/${currentMindId}/clarify`, {
            method: 'POST'
        });

        if (response.ok) {
            const data = await response.json();

            if (!data.has_questions || data.questions.length === 0) {
                clarifyQuestions.innerHTML = `
                    <div class="no-questions">
                        <p>🎉 太棒了！当前想法已经很清晰，没有需要澄清的地方。</p>
                        <p>继续投喂更多想法，或者生成输出吧！</p>
                    </div>
                `;
            } else {
                renderClarifyQuestions(data.questions);
            }
        } else {
            const error = await response.json();
            clarifyQuestions.innerHTML = `<p class="error">加载失败: ${error.detail || '未知错误'}</p>`;
        }
    } catch (error) {
        console.error('加载澄清问题失败:', error);
        clarifyQuestions.innerHTML = '<p class="error">加载失败，请重试</p>';
    } finally {
        btn.disabled = false;
        btn.textContent = '开始澄清';
    }
}

// 渲染澄清问题卡片
function renderClarifyQuestions(questions) {
    clarifyQuestions.innerHTML = questions.map((q, index) => `
        <div class="question-card" data-index="${index}">
            <div class="question-header">
                <h4>${escapeHtml(q.question)}</h4>
                ${q.context ? `<p class="question-context">${escapeHtml(q.context)}</p>` : ''}
            </div>
            <div class="question-options">
                ${q.options.map(opt => `
                    <button class="option-btn" onclick="selectOption(${index}, '${escapeHtml(opt).replace(/'/g, "\\'")}')">
                        ${escapeHtml(opt)}
                    </button>
                `).join('')}
                <button class="option-btn option-custom" onclick="showCustomInput(${index})">
                    其他...
                </button>
            </div>
            <div class="custom-input-wrapper" id="customInput${index}" style="display: none;">
                <input type="text" placeholder="输入你的答案..." class="custom-answer-input" id="customAnswer${index}">
                <button class="btn-primary btn-small" onclick="submitCustomAnswer(${index})">确定</button>
            </div>
        </div>
    `).join('');

    // 存储问题数据供后续使用
    window.clarifyQuestionsData = questions;
}

// 选择选项
async function selectOption(questionIndex, answer) {
    const question = window.clarifyQuestionsData[questionIndex];
    await submitAnswer(question.question, answer, questionIndex);
}

// 显示自定义输入
function showCustomInput(questionIndex) {
    const wrapper = document.getElementById(`customInput${questionIndex}`);
    wrapper.style.display = 'flex';
    document.getElementById(`customAnswer${questionIndex}`).focus();
}

// 提交自定义答案
async function submitCustomAnswer(questionIndex) {
    const input = document.getElementById(`customAnswer${questionIndex}`);
    const answer = input.value.trim();
    if (!answer) return;

    const question = window.clarifyQuestionsData[questionIndex];
    await submitAnswer(question.question, answer, questionIndex);
}

// 提交答案
async function submitAnswer(question, answer, questionIndex) {
    const card = document.querySelector(`.question-card[data-index="${questionIndex}"]`);
    card.classList.add('answered');
    card.innerHTML = `
        <div class="answer-result">
            <p class="answered-question">${escapeHtml(question)}</p>
            <p class="answered-answer">✓ ${escapeHtml(answer)}</p>
        </div>
    `;

    try {
        await fetch(`${API_BASE}/minds/${currentMindId}/answer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, answer })
        });

        // 刷新 Crystal
        await loadCrystal();
        await loadMinds();

    } catch (error) {
        console.error('提交答案失败:', error);
    }
}

// 切换标签页
function switchTab(tabName) {
    // 更新标签状态
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // 更新内容显示
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(tabName + 'Tab').classList.add('active');

    // 刷新 Crystal
    if (tabName === 'crystal') {
        loadCrystal();
    }
}

// 工具函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
    if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
    if (diff < 604800000) return Math.floor(diff / 86400000) + '天前';

    return date.toLocaleDateString('zh-CN');
}

// 简单的 Markdown 转 HTML
function markdownToHtml(md) {
    if (!md) return '';
    return md
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/^/, '<p>')
        .replace(/$/, '</p>')
        .replace(/<p><h3>/g, '<h3>')
        .replace(/<\/h3><\/p>/g, '</h3>')
        .replace(/<p><ul>/g, '<ul>')
        .replace(/<\/ul><\/p>/g, '</ul>');
}
