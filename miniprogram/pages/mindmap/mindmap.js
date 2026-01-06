Page({
  data: {
    url: ''
  },

  onLoad(options) {
    const mindId = options.mind_id || '';
    // 去掉 /api 后缀得到根域名
    const apiUrl = getApp().globalData.baseUrl || '';
    const baseUrl = apiUrl.replace('/api', '');
    const url = `${baseUrl}/mindmap?mind_id=${mindId}&t=${Date.now()}`;
    this.setData({ url });
  }
});
