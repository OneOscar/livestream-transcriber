# 录制端搭建（淘宝直播）

## 工具
- [DouyinLiveRecorder](https://github.com/ihmily/DouyinLiveRecorder)（v4.0.7，支持淘宝）
- 或同作者的 [StreamCap](https://github.com/ihmily/StreamCap)（图形界面）
- 需 FFmpeg（录制器自带）

## 淘宝链接的正确格式（关键坑）

软件只认 **`e.tb.cn`** 开头的链接，`m.tb.cn` / `tbzb.taobao.com` 都会被判为"未知链接"跳过。
另外它的解析逻辑依赖老页面里的 `var url='...'` 跳转代码，新版淘宝页面已没有，会报
`list index out of range`。解决办法：**手动把 liveId 拼进链接**：

```
https://e.tb.cn/h.xxxxxx?id=<liveId>
```

- `h.xxxxxx`：手机淘宝/点淘 App 分享直播间的短链码
- `id=` 后面的数字：网页版直播链接里的 `liveId` 参数值

## Cookie
- 淘宝直播流必须登录：浏览器登录 taobao.com，按 F12 → 网络 → 找 taobao.com 请求，
  复制 `Cookie:` 的值，填进 `config/config.ini` 的 `taobao_cookie =`
- Cookie 会过期，失效时重新复制

## Node.js
- 淘宝接口签名需要 Node.js。录制器首次运行会自动从国内镜像下载安装；
  也可手动装 Node.js LTS（nodejs.org）或便携版加入 PATH

## 分段录制（配合每 30 分钟推送）
`config/config.ini` 里：
- `分段录制是否开启 = 是`
- `视频分段时间(秒) = 1800`（30 分钟一段）
- `视频保存格式 = ts`
- `循环时间(秒) = 60`（监测频率）
- 录像输出到软件目录下的 `downloads\平台\主播\`

## 停止
- 录制窗口按 `Ctrl + C` 正常收尾；别直接点右上角 X（会损坏文件）
- 只停某个直播间：在 `URL_config.ini` 对应行前加 `#`
