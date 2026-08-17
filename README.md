# 直播转文字 · Livestream Transcriber

把电商直播（以淘宝/李佳琦直播间为例）自动转成**文字**：每 30 分钟一段，
每段产出「完整讲话稿（一字未改）」+「AI 总结稿（含商品、预告、福利）」，自动发到你的 QQ 邮箱。

> 本项目是 Codex skill，也是可直接运行的脚本集。供学习参考。

## 功能

- 📹 直播录制（DouyinLiveRecorder，淘宝直播，每 30 分钟自动分段）
- 🎙️ 逐段转写（FunASR + 通义 SenseVoice，GPU/CPU 均可，比实时快几十倍）
- 🤖 自动总结（DeepSeek 等 LLM，含「后续上架/预告」「福利/红包/羊毛」两个重点板块）
- 📧 自动推送（每段完成后，完整记录 + 总结稿以 .txt 附件发到 QQ 邮箱）
- 🔒 每段独立：没有新片段就什么都不做

## 架构

```
录制器 ──30分钟分段──► transcribe_watch.py
                        ├─ 完整记录_<片段>.txt（原话）
                        ├─ ai_summary.py → 总结稿_<片段>.txt
                        └─ send_live_email.py → QQ邮箱（两个附件）
```

## 快速开始

1. 看 `references/setup-environment.md` 装 Python/模型环境
2. 看 `references/setup-recording.md` 配录制器（含淘宝链接/ Cookie / Node.js 的坑）
3. 复制 `scripts/*.example.json` 为 `config.json` / `ai_config.json` / `email_config.json` 并填写
4. `python scripts/transcribe_watch.py` 启动（或配合录制器一起跑）

## 踩坑经验（重点）

- 淘宝链接必须转成 `e.tb.cn` 且加 `?id=<liveId>`，否则录制器不认
- 淘宝录制需要登录 Cookie + Node.js（接口签名）
- 转写模型走本地快照，离线可用
- `.bat` 启动器在中文 Windows 上要用 GBK 编码
- torch 用 2.6.x，避免 Windows 长路径安装失败

详见 `SKILL.md` 与 `references/`。

## ⚠️ 注意

- 本仓库不含任何真实凭据与直播内容；`config*.json` 已加入 `.gitignore`
- 直播回放/转写稿属于主播与平台内容，请仅用于个人学习，勿公开传播
- 请遵守目标平台的服务条款与当地法律

## License

待定（建议 MIT，需在发布前确认）
