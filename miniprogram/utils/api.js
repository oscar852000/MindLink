/**
 * API 封装
 */
const app = getApp()

const request = (url, method = 'GET', data = null) => {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${app.globalData.baseUrl}${url}`,
      method,
      data,
      header: {
        'Content-Type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res)
        }
      },
      fail: reject
    })
  })
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

module.exports = api
