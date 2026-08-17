# -*- coding: utf-8 -*-
"""把某一片段的完整记录 + 总结稿 (.txt) 发到 QQ 邮箱
配置: scripts/email_config.json (密钥) + scripts/config.json (路径)"""
import argparse
import json
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR / "email_config.json"
MAIN_CONFIG = SCRIPT_DIR / "config.json"

def transcripts_dir():
    if MAIN_CONFIG.exists():
        cfg = json.loads(MAIN_CONFIG.read_text(encoding="utf-8"))
        return Path(cfg.get("transcripts_dir", SCRIPT_DIR.parent / "transcripts"))
    return SCRIPT_DIR.parent / "transcripts"

TRANSCRIPTS = transcripts_dir()

def load_config():
    if not CONFIG_FILE.exists():
        print("缺少配置文件: scripts/email_config.json (可复制 email_config.example.json)")
        sys.exit(1)
    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if not cfg.get("qq_email") or not cfg.get("auth_code") or not cfg.get("recipient"):
        print("email_config.json 还没有填完整")
        sys.exit(1)
    return cfg

def is_configured():
    if not CONFIG_FILE.exists():
        return False
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(cfg.get("qq_email") and cfg.get("auth_code") and cfg.get("recipient"))

def send(subject, body, attachments):
    cfg = load_config()
    msg = MIMEMultipart()
    msg["From"] = formataddr((str(Header("直播文字版", "utf-8")), cfg["qq_email"]))
    msg["To"] = cfg["recipient"]
    msg["Subject"] = Header(subject, "utf-8")
    msg.attach(MIMEText(body, "plain", "utf-8"))
    for att in attachments:
        part = MIMEText(att.read_text(encoding="utf-8"), "plain", "utf-8")
        part.add_header("Content-Disposition", "attachment", filename=("utf-8", "", att.name))
        msg.attach(part)
    print(f"正在发送邮件 -> {cfg['recipient']} (附件: {[a.name for a in attachments]})", flush=True)
    with smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=60) as server:
        server.login(cfg["qq_email"], cfg["auth_code"])
        server.sendmail(cfg["qq_email"], [cfg["recipient"]], msg.as_string())
    print("发送成功", flush=True)
    return True

def send_segment_files(stem):
    full = TRANSCRIPTS / f"完整记录_{stem}.txt"
    summary = TRANSCRIPTS / f"总结稿_{stem}.txt"
    attachments = [p for p in (full, summary) if p.exists()]
    if not attachments:
        print(f"该片段还没有文件: {stem}")
        return False
    now = datetime.now().strftime("%m-%d %H:%M")
    subject = f"【直播文字版】{stem}（{now}）"
    body = (f"片段：{stem}\n"
            "附件1) 完整记录.txt —— 原话一字未改\n"
            "附件2) 总结稿.txt —— 整理版(含预告/福利)\n"
            f"生成时间：{now}\n")
    return send(subject, body, attachments)

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
    send_segment_files(stem)
