# bot.py (ShieldX v3.1 Final Moderate)
# Keep this file as a single module. Replace your existing bot.py with this.
import asyncio
import json
import os
import threading
import time
import tempfile
import shutil
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from flask import Flask
from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, RPCError, ChatWriteForbidden
from dotenv import load_dotenv

# Optional system stats
try:
    import psutil
except Exception:
    psutil = None

# ---------------------------
# CONFIG / ENV
# ---------------------------
load_dotenv()
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", 0)) if os.getenv("OWNER_ID") else 0

# Extra owners
def parse_owner_ids(s: str) -> List[int]:
    if not s:
        return []
    parts = [p.strip() for p in s.split(",") if p.strip()]
    ids: List[int] = []
    for p in parts:
        try:
            ids.append(int(p))
        except:
            continue
    return ids

CO_OWNER_IDS = parse_owner_ids(os.getenv("CO_OWNER_IDS", ""))

RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "")
RENDER_HEALTH_URL = os.getenv("RENDER_HEALTH_URL", "")

HF_API_KEY = os.getenv("HF_API_KEY", "")  # optional for NSFW HF

DATA_FILE = "data.json"  # persistent per-chat settings

# ---------------------------
# DEFAULT MESSAGES / LOCALES
# ---------------------------
MESSAGES = {
    "en-in": {
        "start_dm": "🛡️ *ShieldX Protection*\nI keep your groups clean. Use buttons below.",
        "start_group": "🛡️ ShieldX active in this group.",
        "help_dm": "✨ *ShieldX Commands*\n\n• /clean [time] — enable auto-clean (admins)\n• /clean off — disable auto-clean\n• /cleanall — delete last 24h media (owner)\n• /nsfw on|off|status — NSFW detection\n• /status — system health (DM)\n• /reload — owner only\n\nDefault auto-clean: 30 minutes.",
        "help_group": "📩 Sent you a DM with commands.",
        "auto_on": "✅ Auto-clean enabled — interval: {t}.",
        "auto_off": "🛑 Auto-clean disabled.",
        "auto_set": "✅ Auto-clean set to {t}.",
        "cleanall_start": "🧹 Clearing media from last 24 hours...",
        "cleanall_done": "✅ {n} media items removed (last 24h).",
        "only_admin": "⚠️ Only group admins can use this.",
        "only_owner": "⚠️ Only group owner or co-owner can use this.",
        "status_text": "🧹 Auto-clean: {on} | Interval: {t}",
        "ping_text": "🏓 Pong! {ms}ms",
    },
    "hi": {
        "start_dm": "🛡️ ShieldX — आपका auto-clean सहायक। नीचे बटन्स देखें।",
        "start_group": "🛡️ ShieldX समूह में सक्रिय है।",
        "help_dm": "कमांड:\n/clean [time]\n/clean off\n/cleanall\n/nsfw on|off|status\n/status\n/reload",
        "help_group": "कमांड DM में भेज दी गई हैं।",
        "auto_on": "✅ Auto-clean चालू — अंतराल: {t}.",
        "auto_off": "🛑 Auto-clean बंद किया गया।",
        "auto_set": "✅ Auto-clean सेट किया गया — अंतराल {t}.",
        "cleanall_start": "🧹 पिछले 24 घंटे के मीडिया हटाए जा रहे हैं...",
        "cleanall_done": "✅ {n} मीडिया हटाए गए (पिछले 24 घंटे)।",
        "only_admin": "⚠️ केवल group admins उपयोग कर सकते हैं।",
        "only_owner": "⚠️ केवल group owner या co-owner उपयोग कर सकते हैं।",
        "status_text": "Auto-clean: {on} | Interval: {t}",
        "ping_text": "🏓 Pong! {ms}ms",
    }
}
DEFAULT_LOCALE = "en-in"
SUPPORTED_LOCALES = list(MESSAGES.keys())

# ---------------------------
# STORAGE HANDLING
# ---------------------------
# ---------------------------
# STORAGE HANDLING
# ---------------------------
def save_json(path: str, data: dict):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ShieldX] Error saving {path}: {e}")

def load_json(path: str) -> dict:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[ShieldX] Error loading {path}: {e}")
    return {}
