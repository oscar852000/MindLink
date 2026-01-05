const { api, auth } = require('../../utils/api')
const app = getApp()

Page({
  data: {
    minds: [],
    loading: true,
    showModal: false,
    newTitle: '',
    isLoggedIn: false,
    userInfo: null
  },

  onLoad() {
    this.checkLoginAndLoad()
  },

  onShow() {
    // 每次显示页面时检查登录状态并刷新
    this.checkLoginAndLoad()
  },

  onPullDownRefresh() {
    this.checkLoginAndLoad().then(() => {
      wx.stopPullDownRefresh()
    })
  },

  async checkLoginAndLoad() {
    // 检查是否已登录
    if (!app.isLoggedIn()) {
      // 尝试自动登录
      await this.tryAutoLogin()
    }

    if (app.isLoggedIn()) {
      this.setData({
        isLoggedIn: true,
        userInfo: app.globalData.userInfo
      })
      this.loadMinds()
    } else {
      this.setData({
        isLoggedIn: false,
        loading: false
      })
    }
  },

  async tryAutoLogin() {
    try {
      // 获取微信登录 code
      const { code } = await new Promise((resolve, reject) => {
        wx.login({
          success: resolve,
          fail: reject
        })
      })

      // 尝试自动登录
      const res = await auth.wxLogin(code)

      if (res.success && res.token) {
        // 已绑定，保存登录状态
        app.setLoginState(res.token, res.user)
        return true
      }
      // 未绑定，需要手动绑定
      return false
    } catch (err) {
      console.log('自动登录失败:', err)
      return false
    }
  },

  goToLogin() {
    wx.navigateTo({
      url: '/pages/login/login'
    })
  },

  async loadMinds() {
    this.setData({ loading: true })
    try {
      const res = await api.getMinds()
      this.setData({
        minds: res.minds || [],
        loading: false
      })
    } catch (err) {
      console.error('加载失败:', err)
      if (err.code === 401) {
        this.setData({ isLoggedIn: false, loading: false })
      } else {
        wx.showToast({ title: '加载失败', icon: 'none' })
        this.setData({ loading: false })
      }
    }
  },

  goToMind(e) {
    const mindId = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/mind/mind?id=${mindId}`
    })
  },

  showCreateModal() {
    this.setData({ showModal: true, newTitle: '' })
  },

  hideCreateModal() {
    this.setData({ showModal: false })
  },

  stopPropagation() {
    // 阻止冒泡
  },

  onTitleInput(e) {
    this.setData({ newTitle: e.detail.value })
  },

  async createMind() {
    const title = this.data.newTitle.trim()
    if (!title) {
      wx.showToast({ title: '请输入名称', icon: 'none' })
      return
    }

    try {
      wx.showLoading({ title: '创建中...' })
      const res = await api.createMind(title)
      wx.hideLoading()
      this.setData({ showModal: false })

      // 跳转到新创建的 Mind
      wx.navigateTo({
        url: `/pages/mind/mind?id=${res.id}`
      })
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '创建失败', icon: 'none' })
    }
  },

  showDeleteConfirm(e) {
    const mindId = e.currentTarget.dataset.id
    const mind = this.data.minds.find(m => m.id === mindId)

    wx.showModal({
      title: '删除确认',
      content: `确定要删除「${mind.title}」吗？`,
      confirmColor: '#ff4444',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.deleteMind(mindId)
            wx.showToast({ title: '已删除', icon: 'success' })
            this.loadMinds()
          } catch (err) {
            wx.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  }
})
