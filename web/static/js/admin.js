// MindLink 提示词管理

const API_BASE = '/api/admin';

let currentPromptKey = null;
let prompts = [];

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadPrompts();
});

// 加载提示词列表
async function loadPrompts() {
    try {
        const response = await fetch(`${API_BASE}/prompts`);
        const data = await response.json();
        prompts = data.prompts;
        renderPromptList();
    } catch (error) {
        console.error('加载提示词失败:', error);
        showToast('加载失败', 'error');
    }
}

// 渲染提示词列表
function renderPromptList() {
    const container = document.getElementById('promptList');

    if (prompts.length === 0) {
        container.innerHTML = '<div class="empty-editor">暂无提示词</div>';
        return;
    }

    container.innerHTML = prompts.map(p => `
        <div class="prompt-item ${p.key === currentPromptKey ? 'active' : ''}"
             onclick="selectPrompt('${p.key}')">
            <h3>${p.name}</h3>
            <p>${p.description || '无描述'}</p>
            <div class="updated">更新于: ${formatTime(p.updated_at)}</div>
        </div>
    `).join('');
}

// 选择提示词
function selectPrompt(key) {
    currentPromptKey = key;
    const prompt = prompts.find(p => p.key === key);

    if (!prompt) return;

    // 更新列表选中状态
    document.querySelectorAll('.prompt-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget.classList.add('active');

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
