const { auth } = require('../../utils/api')
const app = getApp()

Page({
  data: {
    username: '',
    password: '',
    loading: false,
    error: ''
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value, error: '' })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value, error: '' })
  },

  async bindAccount() {
    const { username, password } = this.data

    if (!username.trim()) {
      this.setData({ error: '请输入用户名' })
      return
    }

    if (!password) {
      this.setData({ error: '请输入密码' })
      return
    }

    this.setData({ loading: true, error: '' })

    try {
      // 获取微信登录 code
      const { code } = await new Promise((resolve, reject) => {
        wx.login({
          success: resolve,
          fail: reject
        })
      })

      // 调用绑定接口
      const res = await auth.wxBind(code, username.trim(), password)

      if (res.success && res.token) {
        // 保存登录状态
        app.setLoginState(res.token, res.user)

        wx.showToast({
          title: '绑定成功',
          icon: 'success',
          duration: 1500
        })

        // 返回上一页
        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        this.setData({
          error: res.message || '绑定失败',
          loading: false
        })
      }
    } catch (err) {
      console.error('绑定失败:', err)
      let errorMsg = '绑定失败，请重试'

      if (err.data && err.data.detail) {
        errorMsg = err.data.detail
      } else if (err.statusCode === 401) {
        errorMsg = '用户名或密码错误'
      } else if (err.statusCode === 400) {
        errorMsg = err.data?.detail || '此微信已绑定其他账号'
      }

      this.setData({
        error: errorMsg,
        loading: false
      })
    }
  },

  goBack() {
    wx.navigateBack()
  }
})
