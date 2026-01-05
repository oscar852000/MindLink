/**
 * API 封装 - 支持 Token 认证
 */
const app = getApp()

const request = (url, method = 'GET', data = null, requireAuth = true) => {
  return new Promise((resolve, reject) => {
    // 构建请求头
    const header = {
      'Content-Type': 'application/json'
    }

    // 添加 Token 认证
    if (requireAuth && app.globalData.token) {
      header['Authorization'] = `Bearer ${app.globalData.token}`
    }

    wx.request({
      url: `${app.globalData.baseUrl}${url}`,
      method,
      data,
      header,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          // Token 过期或无效，清除登录状态
          app.clearLoginState()
          reject({ code: 401, message: '登录已过期，请重新登录' })
        } else {
          reject(res)
        }
      },
      fail: reject
    })
  })
}

// 认证相关 API
const auth = {
  // 微信登录（检查绑定状态）
  wxLogin: (code) => request('/auth/wx-login', 'POST', { code }, false),

  // 微信绑定账号
  wxBind: (code, username, password) => request('/auth/wx-bind', 'POST', { code, username, password }, false),

  // 获取当前用户信息
  getMe: () => request('/auth/wx-me', 'GET', null, true)
}

// Mind 相关 API
const api = {
  // 获取 Mind 列表
  getMinds: () => request('/minds'),

  // 获取单个 Mind
  getMind: (mindId) => request(`/minds/${mindId}`),

  // 创建 Mind
  createMind: (title) => request('/minds', 'POST', { title }),

  // 删除 Mind
  deleteMind: (mindId) => request(`/minds/${mindId}`, 'DELETE'),

  // 投喂
  feed: (mindId, content) => request(`/minds/${mindId}/feed`, 'POST', { content }),

  // 获取时间轴
  getTimeline: (mindId) => request(`/minds/${mindId}/timeline-view`),

  // 获取结构
  getCrystal: (mindId) => request(`/minds/${mindId}/crystal`),

  // 生成叙事
  generateNarrative: (mindId) => request(`/minds/${mindId}/narrative`, 'POST'),

  // 对话
  chat: (mindId, message, model = 'google_gemini_3_flash', style = 'default') =>
    request(`/minds/${mindId}/chat`, 'POST', { message, model, style }),

  // 获取对话历史
  getChatHistory: (mindId) => request(`/minds/${mindId}/chat/history`),

  // 清空对话
  clearChat: (mindId) => request(`/minds/${mindId}/chat/history`, 'DELETE'),

  // 生成输出
  generateOutput: (mindId, instruction) =>
    request(`/minds/${mindId}/output`, 'POST', { instruction }),

  // 更新 Feed
  updateFeed: (feedId, content) => request(`/feeds/${feedId}`, 'PUT', { content }),

  // 删除 Feed
  deleteFeed: (feedId) => request(`/feeds/${feedId}`, 'DELETE')
}

module.exports = { api, auth }
