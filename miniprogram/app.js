App({
  globalData: {
    baseUrl: 'https://ml.jibenlizi.net/api',
    userInfo: null,
    token: null
  },

  onLaunch() {
    // 从本地存储读取登录状态
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    if (token && userInfo) {
      this.globalData.token = token
      this.globalData.userInfo = userInfo
    }
  },

  // 保存登录状态
  setLoginState(token, userInfo) {
    this.globalData.token = token
    this.globalData.userInfo = userInfo
    wx.setStorageSync('token', token)
    wx.setStorageSync('userInfo', userInfo)
  },

  // 清除登录状态
  clearLoginState() {
    this.globalData.token = null
    this.globalData.userInfo = null
    wx.removeStorageSync('token')
    wx.removeStorageSync('userInfo')
  },

  // 检查是否已登录
  isLoggedIn() {
    return !!this.globalData.token
  }
})
