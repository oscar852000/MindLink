const api = require('../../utils/api')

Page({
  data: {
    minds: [],
    loading: true,
    showModal: false,
    newTitle: ''
  },

  onLoad() {
    this.loadMinds()
  },

  onShow() {
    // 每次显示页面时刷新列表
    this.loadMinds()
  },

  onPullDownRefresh() {
    this.loadMinds().then(() => {
      wx.stopPullDownRefresh()
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
      wx.showToast({ title: '加载失败', icon: 'none' })
      this.setData({ loading: false })
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
