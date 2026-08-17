# -*- coding: utf-8 -*-
"""调用 AI 为某一片段生成独立总结稿 -> 总结稿_<片段>.md/.txt
配置: scripts/ai_config.json (密钥) + scripts/config.json (路径)"""
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR / "ai_config.json"
MAIN_CONFIG = SCRIPT_DIR / "config.json"

def transcripts_dir():
    if MAIN_CONFIG.exists():
        cfg = json.loads(MAIN_CONFIG.read_text(encoding="utf-8"))
        return Path(cfg.get("transcripts_dir", SCRIPT_DIR.parent / "transcripts"))
    return SCRIPT_DIR.parent / "transcripts"

TRANSCRIPTS = transcripts_dir()
MAX_CHARS = 30000

PROMPT_TEMPLATE = """你是资深的内容编辑。下面是一段电商直播(李佳琦直播间)的语音转写原文，口语化、有重复、有识别小瑕疵。请把它整理成一份结构化总结稿，要求：

1. 按商品/话题分段，每段包含：商品名称、价格与规格、核心卖点、注意事项；不确定的数字/品牌名标注"(以链接为准)"
2. 必须包含这两个重点板块（放在商品分段之后）：
   - 「📅 后续上架/预告」：主播提到未来会上什么品、什么时候上（如具体时间点、"几点"、"几号再播"、"双十一"、"预售"等），用表格列出
   - 「🎁 福利/红包/羊毛」：优惠券、满减、红包雨、赠品、限量小卡、88VIP折扣等，用表格列出
3. 结尾加「📌 本段要点总结」5~8 条
4. 只输出总结稿正文，不要解释过程；用 Markdown 格式

===== 转写原文开始 =====
{content}
===== 转写原文结束 =====
"""

def load_config():
    if not CONFIG_FILE.exists():
        print("缺少配置文件: scripts/ai_config.json (可复制 ai_config.example.json)")
        sys.exit(1)
    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    key = cfg.get("api_key", "")
    if not key or "在此填入" in key:
        print("ai_config.json 还没有填 API Key")
        sys.exit(1)
    return cfg

def is_configured():
    if not CONFIG_FILE.exists():
        return False
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return False
    key = cfg.get("api_key", "")
    return bool(key) and "在此填入" not in key

def call_llm(content):
    cfg = load_config()
    if len(content) > MAX_CHARS:
        content = "（内容较长，以下为最近部分）\n" + content[-MAX_CHARS:]
    import requests
    url = cfg.get("base_url", "https://api.deepseek.com").rstrip("/") + "/v1/chat/completions"
    headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
    payload = {
        "model": cfg.get("model", "deepseek-chat"),
        "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(content=content)}],
        "temperature": 0.3,
        "max_tokens": 4000,
    }
    print("正在调用 AI 生成总结稿...", flush=True)
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    if r.status_code != 200:
        print(f"AI 接口返回错误 {r.status_code}: {r.text[:300]}", flush=True)
        return None
    return r.json()["choices"][0]["message"]["content"].strip()

def generate_summary_for_segment(stem):
    seg_file = TRANSCRIPTS / f"完整记录_{stem}.txt"
    if not seg_file.exists():
        print(f"找不到该片段完整记录: {seg_file}")
        return False
    text = call_llm(seg_file.read_text(encoding="utf-8"))
    if not text:
        return False
    (TRANSCRIPTS / f"总结稿_{stem}.md").write_text(text + "\n", encoding="utf-8")
    (TRANSCRIPTS / f"总结稿_{stem}.txt").write_text(text + "\n", encoding="utf-8")
    print(f"该段总结稿已生成: 总结稿_{stem}.txt ({len(text)} 字)", flush=True)
    return True

def latest_segment_stem():
    files = sorted(TRANSCRIPTS.glob("完整记录_*.txt"))
    return files[-1].name[len("完整记录_"):-len(".txt")] if files else None

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--segment", type=str, default="")
    args = ap.parse_args()
    stem = args.segment or latest_segment_stem()
    if not stem:
        print("还没有任何片段的完整记录")
        sys.exit(1)
    generate_summary_for_segment(stem)
