const { api } = require('../../utils/api')

Page({
  data: {
    mindId: '',
    mind: null,
    currentTab: 'feed',

    // 投喂
    feedContent: '',
    feedStatus: '',

    // 对话
    models: [
      { id: 'google_gemini_3_flash', name: 'Gemini Flash' },
      { id: 'google_gemini_3_pro', name: 'Gemini Pro' }
    ],
    modelIndex: 0,
    chatMessages: [],
    chatInput: '',
    chatLoading: false,
    scrollToView: '',

    // 结构
    structureHtml: '',

    // 时间轴
    timeline: [],

    // 叙事
    narrativeHtml: '',

    // 输出
    outputInstruction: '',
    outputHtml: '',

    // 编辑
    showEditModal: false,
    editFeedId: '',
    editContent: ''
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ mindId: options.id })
      this.loadMind()
    }
  },

  async loadMind() {
    try {
      const mind = await api.getMind(this.data.mindId)
      this.setData({ mind })
    } catch (err) {
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  goBack() {
    wx.navigateBack()
  },

  openMindmap() {
    const mindId = this.data.mindId
    if (!mindId) {
      wx.showToast({ title: '请先选择 Mind', icon: 'none' })
      return
    }
    wx.navigateTo({
      url: `/pages/mindmap/mindmap?mind_id=${mindId}`
    })
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ currentTab: tab })

    // 切换时加载数据
    if (tab === 'structure') this.loadStructure()
    if (tab === 'timeline') this.loadTimeline()
    if (tab === 'narrative') this.loadNarrative()
    if (tab === 'chat') this.loadChatHistory()
  },

  // ========== 投喂 ==========
  onFeedInput(e) {
    this.setData({ feedContent: e.detail.value })
  },

  async submitFeed() {
    const content = this.data.feedContent.trim()
    if (!content) return

    this.setData({ feedStatus: '正在晶体化...' })

    try {
      await api.feed(this.data.mindId, content)
      this.setData({
        feedContent: '',
        feedStatus: '已存入晶体网络'
      })
      setTimeout(() => this.setData({ feedStatus: '' }), 2000)
    } catch (err) {
      this.setData({ feedStatus: '提交失败' })
    }
  },

  // ========== 对话 ==========
  async loadChatHistory() {
    try {
      const res = await api.getChatHistory(this.data.mindId)
      if (res.messages && res.messages.length > 0) {
        this.setData({ chatMessages: res.messages })
        this.scrollToBottom()
      }
    } catch (err) {
      console.error('加载对话历史失败:', err)
    }
  },

  onModelChange(e) {
    this.setData({ modelIndex: e.detail.value })
  },

  onChatInput(e) {
    this.setData({ chatInput: e.detail.value })
  },

  async sendChat() {
    const message = this.data.chatInput.trim()
    if (!message || this.data.chatLoading) return

    const messages = [...this.data.chatMessages, { role: 'user', content: message }]
    this.setData({
      chatMessages: messages,
      chatInput: '',
      chatLoading: true
    })
    this.scrollToBottom()

    try {
      const model = this.data.models[this.data.modelIndex].id
      const res = await api.chat(this.data.mindId, message, model)

      messages.push({ role: 'assistant', content: res.reply })
      this.setData({ chatMessages: messages, chatLoading: false })
      this.scrollToBottom()
    } catch (err) {
      this.setData({ chatLoading: false })
      wx.showToast({ title: '发送失败', icon: 'none' })
    }
  },

  scrollToBottom() {
    const len = this.data.chatMessages.length
    this.setData({ scrollToView: `msg-${len - 1}` })
  },

  async clearChat() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空对话记录吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.clearChat(this.data.mindId)
            this.setData({ chatMessages: [] })
            wx.showToast({ title: '已清空', icon: 'success' })
          } catch (err) {
            wx.showToast({ title: '清空失败', icon: 'none' })
          }
        }
      }
    })
  },

  // ========== 结构 ==========
  async loadStructure() {
    try {
      const res = await api.getCrystal(this.data.mindId)
      const html = this.mdToHtml(res.structure_markdown || '等待生成结构...')
      this.setData({ structureHtml: html })
    } catch (err) {
      console.error('加载结构失败:', err)
    }
  },

  // ========== 时间轴 ==========
  async loadTimeline() {
    try {
      const res = await api.getTimeline(this.data.mindId)
      this.setData({ timeline: res.timeline || [] })
    } catch (err) {
      console.error('加载时间轴失败:', err)
    }
  },

  // ========== 叙事 ==========
  async loadNarrative() {
    try {
      const res = await api.getMind(this.data.mindId)
      if (res.narrative) {
        const html = this.mdToHtml(res.narrative)
        this.setData({ narrativeHtml: html })
      }
    } catch (err) {
      console.error('加载叙事失败:', err)
    }
  },

  async generateNarrative() {
    wx.showLoading({ title: '生成中...' })
    try {
      const res = await api.generateNarrative(this.data.mindId)
      const html = this.mdToHtml(res.narrative || '')
      this.setData({ narrativeHtml: html })
      wx.hideLoading()
      wx.showToast({ title: '已更新', icon: 'success' })
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '生成失败', icon: 'none' })
    }
  },

  showEditMenu(e) {
    const { id, content } = e.currentTarget.dataset
    this.setData({
      showEditModal: true,
      editFeedId: id,
      editContent: content
    })
  },

  hideEditModal() {
    this.setData({ showEditModal: false })
  },

  stopPropagation() {},

  onEditInput(e) {
    this.setData({ editContent: e.detail.value })
  },

  async saveFeed() {
    const content = this.data.editContent.trim()
    if (!content) {
      wx.showToast({ title: '内容不能为空', icon: 'none' })
      return
    }

    try {
      await api.updateFeed(this.data.editFeedId, content)
      this.setData({ showEditModal: false })
      wx.showToast({ title: '已保存', icon: 'success' })
      this.loadTimeline()
    } catch (err) {
      wx.showToast({ title: '保存失败', icon: 'none' })
    }
  },

  async deleteFeed() {
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条记录吗？',
      confirmColor: '#ff4444',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.deleteFeed(this.data.editFeedId)
            this.setData({ showEditModal: false })
            wx.showToast({ title: '已删除', icon: 'success' })
            this.loadTimeline()
          } catch (err) {
            wx.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  },

  // ========== 输出 ==========
  onOutputInput(e) {
    this.setData({ outputInstruction: e.detail.value })
  },

  async generateOutput() {
    const instruction = this.data.outputInstruction.trim()
    if (!instruction) {
      wx.showToast({ title: '请输入指令', icon: 'none' })
      return
    }

    wx.showLoading({ title: '生成中...' })

    try {
      const res = await api.generateOutput(this.data.mindId, instruction)
      const html = this.mdToHtml(res.content)
      this.setData({ outputHtml: html })
      wx.hideLoading()
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '生成失败', icon: 'none' })
    }
  },

  // ========== 工具函数 ==========
  mdToHtml(md) {
    if (!md) return ''
    return md
      .replace(/^### (.+)$/gm, '<h3 style="color:#00E5FF;font-size:16px;margin:20rpx 0 10rpx;">$1</h3>')
      .replace(/^## (.+)$/gm, '<h2 style="color:#00E5FF;font-size:18px;margin:30rpx 0 15rpx;">$1</h2>')
      .replace(/\*\*(.+?)\*\*/g, '<strong style="color:#00E5FF;">$1</strong>')
      .replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.1);padding:2px 6px;border-radius:4px;">$1</code>')
      .replace(/^- (.+)$/gm, '<div style="margin:8rpx 0;padding-left:20rpx;">• $1</div>')
      .replace(/\n\n/g, '<br/><br/>')
      .replace(/\n/g, '<br/>')
  }
})
