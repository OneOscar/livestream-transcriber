---
name: livestream-transcriber
description: >-
  Turn live-streamed e-commerce broadcasts (e.g., Li Jiaqi's Taobao live rooms) into
  text. Records the stream in 30-minute segments, transcribes each segment verbatim
  with FunASR/SenseVoice, auto-generates an AI summary (products, upcoming previews,
  coupons/giveaways) via an LLM API, and emails both .txt files to your phone every
  segment. Use when you need a searchable/readable text record of a livestream, want
  automated per-segment transcripts plus summaries, or want deal/preview tracking
  (new products, discounts, red-packet giveaways) pushed to your inbox. Covers the
  tricky bits: Taobao share links must be converted to e.tb.cn with an ?id= param,
  recording needs a login cookie + Node.js, and ASR models should run offline.
---

# Livestream → Transcript + Summary

Record an e-commerce livestream, transcribe it verbatim per 30-minute segment, auto-summarize
with an LLM, and email both files to the user's phone. Fully automated after setup.

## When to use

- User wants a text version of a livestream (product-by-product) or "what did they
  preview/announce and what deals/coupons are coming" tracking.
- User asks to set up automatic recording → transcription → summary → email delivery.

## Architecture

```
recorder (DouyinLiveRecorder) ── 30-min segments ──► transcribe_watch.py
                                                          │ per new segment:
                                                          ├─ verbatim 完整记录_<seg>.txt
                                                          ├─ ai_summary.py → 总结稿_<seg>.txt
                                                          └─ send_live_email.py → QQ email with both .txt
```

Each segment is independent (own transcript + own summary + own email). If no new segment,
nothing runs.

## Quick start

1. **Install environment** (see `references/setup-environment.md`): Python venv, torch (CPU or CUDA),
   `funasr` + `modelscope`, and pre-download the SenseVoice/VAD/punctuation models.
2. **Set up the recorder** (see `references/setup-recording.md`): DouyinLiveRecorder with the
   Taobao share link converted to `e.tb.cn` + `?id=<liveId>`, a login cookie, and Node.js.
3. **Configure** `scripts/config.json` (paths), `scripts/email_config.json` (QQ SMTP),
   `scripts/ai_config.json` (LLM API key). Copy from the `.example.json` templates.
4. **Run**: `python scripts/transcribe_watch.py` (or the recorder + watcher together).
   Every completed segment is transcribed, summarized, and emailed automatically.

## Key pitfalls (learned the hard way)

- **Taobao URL format**: the recorder only accepts `e.tb.cn` links, NOT `m.tb.cn` or
  `tbzb.taobao.com` URLs. Use a share link with the host swapped to `e.tb.cn` AND append
  `?id=<liveId>` (the numeric `liveId` from the web URL) to bypass outdated page parsing.
- **Cookie + Node.js**: Taobao live resolution needs a logged-in cookie (`taobao_cookie`) and
  Node.js at runtime (signs API requests). First recorder run auto-installs Node.js.
- **Offline ASR models**: point FunASR at locally downloaded model snapshots
  (`MODELSCOPE_CACHE/models/<id>/snapshots/...`) to avoid network calls on every load.
- **Encoding**: `.bat` launchers must be GBK on Chinese Windows, not UTF-8, or cmd breaks.
- **Long paths**: use torch 2.6.x (newer torch ships dist-info license trees that exceed
  Windows MAX_PATH and fail pip install).
- **ASR verbatim rule**: the "完整记录" file must never be cleaned; keep fillers/artifacts
  as-is. Only the AI summary is edited.

## Files

- `scripts/transcribe_watch.py` — watcher: detects new stable segments, transcribes, writes
  per-segment verbatim file, triggers summary + email.
- `scripts/ai_summary.py` — calls the LLM (OpenAI-compatible, e.g. DeepSeek) to write the
  per-segment summary including the「预告」and「福利」sections.
- `scripts/send_live_email.py` — sends the segment's two .txt files via QQ SMTP.
- `references/setup-recording.md` — recorder install, URL/cookie/Node setup, 30-min segments.
- `references/setup-environment.md` — Python/venv/torch/funasr/models install (incl. mirrors
  usable in China).

## Security notes for maintainers

- Never commit `config.json`, `email_config.json`, `ai_config.json` (they hold real
  credentials). Use the `.example.json` templates and `.gitignore`.
- Live transcripts/recordings are third-party copyrighted content — do not publish them;
  publish only the tooling and method.
