// MindLink 提示词管理

const API_BASE = '/api/admin';

let currentPromptKey = null;
let prompts = [];

// 分类配置
const CATEGORY_CONFIG = {
    'core': {
        name: '核心功能',
        description: '对应前端主要 Tab',
        icon: '⚙️'
    },
    'chat': {
        name: '对话功能',
        description: '对话 Tab 相关',
        icon: '💬'
    }
};

// HTML 转义函数 - 防止 XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadPrompts();

    // 绑定按钮事件
    document.getElementById('resetPromptBtn').addEventListener('click', resetPrompt);
    document.getElementById('savePromptBtn').addEventListener('click', savePrompt);
});

// 加载提示词列表
async function loadPrompts() {
    try {
        const response = await fetch(`${API_BASE}/prompts`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        prompts = data.prompts;
        renderPromptList();
    } catch (error) {
        console.error('加载提示词失败:', error);
        showToast('加载失败', 'error');
    }
}

// 渲染提示词列表（按分类）
function renderPromptList() {
    const container = document.getElementById('promptList');

    if (prompts.length === 0) {
        container.innerHTML = '<div class="empty-editor">暂无提示词</div>';
        return;
    }

    // 按分类分组
    const grouped = {};
    prompts.forEach(p => {
        const category = p.category || 'other';
        if (!grouped[category]) {
            grouped[category] = [];
        }
        grouped[category].push(p);
    });

    // 渲染分组
    let html = '';

    // 按固定顺序渲染：core, chat
    const categoryOrder = ['core', 'chat'];

    categoryOrder.forEach(category => {
        if (!grouped[category] || grouped[category].length === 0) return;

        const config = CATEGORY_CONFIG[category] || {
            name: '其他',
            description: '',
            icon: '📋'
        };

        html += `
            <div class="prompt-category">
                <div class="category-header">
                    <span class="category-icon">${config.icon}</span>
                    <span class="category-name">${config.name}</span>
                    <span class="category-count">${grouped[category].length}</span>
                </div>
                <div class="category-prompts">
                    ${grouped[category].map(p => `
                        <div class="prompt-item ${p.key === currentPromptKey ? 'active' : ''}"
                             data-key="${escapeHtml(p.key)}"
                             onclick="selectPrompt('${escapeHtml(p.key)}')">
                            <h3>${escapeHtml(p.name)}</h3>
                            <p>${escapeHtml(p.description) || '无描述'}</p>
                            <div class="updated">更新于: ${formatTime(p.updated_at)}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// 选择提示词
function selectPrompt(key) {
    currentPromptKey = key;
    const prompt = prompts.find(p => p.key === key);

    if (!prompt) return;

    // 更新列表选中状态
    document.querySelectorAll('.prompt-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.key === key) {
            item.classList.add('active');
        }
    });

    // 显示编辑器
    const editor = document.getElementById('promptEditor');
    editor.style.display = 'flex';

    document.getElementById('editorTitle').textContent = `编辑: ${prompt.name}`;
    document.getElementById('editorDescription').textContent = prompt.description || '无描述';
    document.getElementById('promptContent').value = prompt.content;
}

// 保存提示词
async function savePrompt() {
    if (!currentPromptKey) return;

    const content = document.getElementById('promptContent').value;

    try {
        const response = await fetch(`${API_BASE}/prompts/${currentPromptKey}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            showToast('保存成功', 'success');
            // 更新本地数据
            const prompt = prompts.find(p => p.key === currentPromptKey);
            if (prompt) {
                prompt.content = content;
                prompt.updated_at = new Date().toISOString();
            }
            renderPromptList();
        } else {
            throw new Error('保存失败');
        }
    } catch (error) {
        console.error('保存失败:', error);
        showToast('保存失败', 'error');
    }
}

// 重置提示词
async function resetPrompt() {
    if (!currentPromptKey) return;

    if (!confirm('确定要重置为默认提示词吗？')) return;

    try {
        const response = await fetch(`${API_BASE}/prompts/reset/${currentPromptKey}`, {
            method: 'POST'
        });

        if (response.ok) {
            const data = await response.json();
            showToast('已重置为默认', 'success');

            // 更新本地数据和编辑器
            const index = prompts.findIndex(p => p.key === currentPromptKey);
            if (index !== -1) {
                prompts[index] = data;
            }
            document.getElementById('promptContent').value = data.content;
            renderPromptList();
        } else {
            throw new Error('重置失败');
        }
    } catch (error) {
        console.error('重置失败:', error);
        showToast('重置失败', 'error');
    }
}

// 格式化时间
function formatTime(isoString) {
    if (!isoString) return '未知';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 显示提示消息
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 2000);
}
