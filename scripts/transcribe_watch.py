# -*- coding: utf-8 -*-
"""
直播转写监听器: 监视录制器输出目录, 发现新录完的片段就转成文字,
每段生成独立的完整记录, 并触发 AI 总结 + 邮件推送。

配置: 本文件同目录的 config.json (首次运行会从 config.example.json 复制)
用法:
  python transcribe_watch.py              # 持续监听
  python transcribe_watch.py --once       # 处理完当前已有片段后退出
  python transcribe_watch.py --test 视频   # 直接转写指定视频
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent

DEFAULT_CONFIG = {
    "watch_dir": str(BASE_DIR / "downloads"),
    "ffmpeg": "ffmpeg",
    "transcripts_dir": str(BASE_DIR / "transcripts"),
    "models_cache": str(BASE_DIR / "models_cache"),
    "poll_seconds": 60,
    "stable_seconds": 30,
    "segment_min_mb": 2,
}

def load_config():
    cfg_file = SCRIPT_DIR / "config.json"
    if not cfg_file.exists():
        example = SCRIPT_DIR / "config.example.json"
        if example.exists():
            import shutil
            shutil.copyfile(example, cfg_file)
            print(f"已从模板生成 {cfg_file}，请先按实际路径修改后再运行。", flush=True)
        else:
            cfg_file.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"已生成默认配置 {cfg_file}，请先按实际路径修改后再运行。", flush=True)
        sys.exit(1)
    cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
    return {**DEFAULT_CONFIG, **cfg}

CONFIG = load_config()
WATCH_DIR = Path(CONFIG["watch_dir"])
FFMPEG = CONFIG["ffmpeg"]
TRANSCRIPT_DIR = Path(CONFIG["transcripts_dir"])
MODELSCOPE_CACHE = Path(CONFIG["models_cache"])
STATE_FILE = TRANSCRIPT_DIR / "processed.json"

os.environ.setdefault("MODELSCOPE_HOME", str(BASE_DIR / "modelscope_home"))
os.environ.setdefault("MODELSCOPE_CACHE", str(MODELSCOPE_CACHE))
os.environ.setdefault("HF_HOME", str(BASE_DIR / "hf_cache"))

DEVICE = os.environ.get("TRANSCRIBE_DEVICE", "cuda" if os.environ.get("TRANSCRIBE_USE_CPU") != "1" else "cpu")
POLL_SECONDS = int(CONFIG["poll_seconds"])
STABLE_SECONDS = int(CONFIG["stable_seconds"])
SEGMENT_MIN_MB = int(CONFIG["segment_min_mb"])

# ---------- 工具 ----------
def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(TRANSCRIPT_DIR / "watch.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"processed": []}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def file_stable(path, seconds):
    try:
        s1 = os.path.getsize(path)
        time.sleep(3)
        s2 = os.path.getsize(path)
        return s1 == s2 and (time.time() - os.path.getmtime(path)) > seconds
    except OSError:
        return False

def find_new_segments(state):
    exts = {".ts", ".mp4", ".flv", ".mkv"}
    processed_stems = {Path(r).stem for r in state["processed"]}
    candidates = []
    for p in WATCH_DIR.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            rel = str(p.relative_to(WATCH_DIR))
            if rel in state["processed"]:
                continue
            if p.stem in processed_stems:
                continue
            if p.stat().st_size < SEGMENT_MIN_MB * 1024 * 1024:
                continue
            candidates.append(p)
    return candidates

def extract_audio(video_path, wav_path):
    cmd = [FFMPEG, "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000",
           "-c:a", "pcm_s16le", str(wav_path)]
    r = subprocess.run(cmd, capture_output=True)
    return r.returncode == 0 and wav_path.exists()

# ---------- 转录(FunASR, 延迟导入, 优先本地模型) ----------
_asr = None

def local_model_path(model_id):
    cache_root = Path(os.environ.get("MODELSCOPE_CACHE", "")) / "models" / model_id.replace("/", "--")
    if cache_root.exists():
        snaps = sorted(cache_root.glob("snapshots/*"))
        if snaps:
            return str(snaps[0])
    return model_id

ASR_MODEL = os.environ.get("ASR_MODEL", "iic/SenseVoiceSmall")
VAD_MODEL = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
PUNC_MODEL = "iic/punc_ct-transformer_cn-en-common-vocab471067-large"

def get_asr():
    global _asr
    if _asr is None:
        from funasr import AutoModel
        log(f"加载语音识别模型... (设备: {DEVICE})")
        _asr = AutoModel(
            model=local_model_path(ASR_MODEL),
            vad_model=local_model_path(VAD_MODEL),
            vad_kwargs={"max_single_segment_time": 30000},
            punc_model=local_model_path(PUNC_MODEL),
            device=DEVICE,
            disable_update=True,
        )
        log("模型加载完成")
    return _asr

def transcribe_wav(wav_path):
    asr = get_asr()
    res = asr.generate(input=str(wav_path), cache={}, language="auto",
                       use_itn=True, batch_size_s=60, merge_vad=True, merge_length_s=15)
    return res[0]["text"]

# ---------- 主流程 ----------
def process_segment(video_path, state):
    rel = str(video_path.relative_to(WATCH_DIR))
    log(f"发现新片段: {rel} ({video_path.stat().st_size/1024/1024:.1f} MB), 开始转写...")
    tmp_wav = TRANSCRIPT_DIR / (video_path.stem + ".wav")
    try:
        if not extract_audio(video_path, tmp_wav):
            log(f"  [FAIL] 音频提取失败: {video_path.name}")
            return False
        text = transcribe_wav(tmp_wav)
        stem = video_path.stem
        seg_full = TRANSCRIPT_DIR / f"完整记录_{stem}.txt"
        seg_full.write_text(text, encoding="utf-8")
        append_to_master(rel, text)
        state["processed"].append(rel)
        save_state(state)
        log(f"  [OK] 完成, 文字 {len(text)} 字")
        try:
            from ai_summary import generate_summary_for_segment, is_configured as ai_configured
            if ai_configured():
                generate_summary_for_segment(stem)
                log("  [AI] 该段总结稿已生成")
        except Exception as e:
            log(f"  [AI] 总结稿生成失败: {e}")
        try:
            from send_live_email import send_segment_files, is_configured
            if is_configured():
                send_segment_files(stem)
                log("  [EMAIL] 已发送该段到邮箱")
        except Exception as e:
            log(f"  [EMAIL] 发送失败: {e}")
        return True
    finally:
        if tmp_wav.exists():
            try:
                tmp_wav.unlink()
            except OSError:
                pass

def append_to_master(rel, text):
    master = TRANSCRIPT_DIR / "1-完整直播记录.md"
    if not master.exists():
        master.write_text("# 完整直播记录(本场累计, 本地回看用)\n", encoding="utf-8")
    header = f"\n\n## 片段: {rel}  ({time.strftime('%Y-%m-%d %H:%M')})\n\n"
    with open(master, "a", encoding="utf-8") as f:
        f.write(header)
        f.write(text)
        f.write("\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--test", type=str, default="")
    args = ap.parse_args()

    if args.test:
        state = load_state()
        ok = process_segment(Path(args.test), state)
        sys.exit(0 if ok else 1)

    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    log(f"开始监听: {WATCH_DIR}")
    while True:
        try:
            state = load_state()
            for video in find_new_segments(state):
                if file_stable(video, STABLE_SECONDS):
                    process_segment(video, state)
        except Exception as e:
            log(f"  [ERR] {e}")
        if args.once:
            break
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
