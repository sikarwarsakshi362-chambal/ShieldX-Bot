# bot.py  — ShieldX Final (stable old-format with Flask + restart loop)
# Put this file in C:\TelegramBot\MediaCleanerBot\bot.py
# Make sure .env exists in same folder with BOT_TOKEN, API_ID, API_HASH, OWNER_ID, CO_OWNER_ID, SHIELDX_DB

import os
import re
import json
import time
import logging
import sqlite3
from datetime import datetime
from threading import Thread
from flask import Flask
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions

# -------------------------
# Load environment
# -------------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH")
OWNER_ID = int(os.getenv("OWNER_ID") or 0) if os.getenv("OWNER_ID") else None
CO_OWNER_ID = int(os.getenv("CO_OWNER_ID") or 0) if os.getenv("CO_OWNER_ID") else None
DB_PATH = os.getenv("SHIELDX_DB", "shieldx_features.db")

if not BOT_TOKEN or not API_ID or not API_HASH:
    print("❌ Missing BOT_TOKEN / API_ID / API_HASH in environment. Exiting.")
    raise SystemExit(1)

# -------------------------
# Logging
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# -------------------------
# Defaults & patterns
# -------------------------
DEFAULTS = {
    "media_delete": True,
    "nsfw_auto_delete": True,
    "auto_mute": True,
    "abuse_filter": True,
    "daily_start": "00:00",
    "daily_end": "23:59",
    "nsfw_threshold": 5,
    "warn_limit": 3
}

# Basic vulgar patterns (en + common translit). Expand as needed.
VULGAR_WORDS = [
    r"\b(?:fuck|shit|bitch|asshole|slut)\b",
    r"\b(?:chutiya|madarchod|bhosdike|randi|gandu|bsdk|mc|bc)\b"
]

# -------------------------
# Database helper
# -------------------------
class DB:
    def __init__(self, path=DB_PATH):
        self.path = path
        # ensure folder exists
        base = os.path.dirname(os.path.abspath(path))
        if base and not os.path.exists(base):
            os.makedirs(base, exist_ok=True)
        # sqlite connection with safe options
        self.conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
        self._init()

    def _init(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS config(k TEXT PRIMARY KEY, v TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS nsfw_counts(chat_id INTEGER, user_id INTEGER, count INTEGER, last_ts INTEGER,
                       PRIMARY KEY(chat_id, user_id))''')
        cur.execute('''CREATE TABLE IF NOT EXISTS warns(chat_id INTEGER, user_id INTEGER, warns INTEGER, last_ts INTEGER,
                       PRIMARY KEY(chat_id, user_id))''')
        self.conn.commit()
        # set defaults if missing
        for k, v in DEFAULTS.items():
            if self.get(k) is None:
                self.set(k, v)

    def get(self, k):
        cur = self.conn.cursor()
        cur.execute("SELECT v FROM config WHERE k=?", (k,))
        r = cur.fetchone()
        return json.loads(r[0]) if r else None

    def set(self, k, v):
        cur = self.conn.cursor()
        cur.execute("REPLACE INTO config(k,v) VALUES(?,?)", (k, json.dumps(v)))
        self.conn.commit()

    def incr_nsfw(self, chat_id, user_id):
        cur = self.conn.cursor()
        cur.execute("SELECT count FROM nsfw_counts WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        r = cur.fetchone()
        if r:
            cnt = r[0] + 1
            cur.execute("UPDATE nsfw_counts SET count=?, last_ts=? WHERE chat_id=? AND user_id=?", (cnt, int(time.time()), chat_id, user_id))
        else:
            cnt = 1
            cur.execute("INSERT INTO nsfw_counts(chat_id,user_id,count,last_ts) VALUES(?,?,?,?)", (chat_id, user_id, cnt, int(time.time())))
        self.conn.commit()
        return cnt

    def reset_nsfw(self, chat_id, user_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM nsfw_counts WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        self.conn.commit()

    def add_warn(self, chat_id, user_id):
        cur = self.conn.cursor()
        cur.execute("SELECT warns FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        r = cur.fetchone()
        if r:
            w = r[0] + 1
            cur.execute("UPDATE warns SET warns=?, last_ts=? WHERE chat_id=? AND user_id=?", (w, int(time.time()), chat_id, user_id))
        else:
            w = 1
            cur.execute("INSERT INTO warns(chat_id,user_id,warns,last_ts) VALUES(?,?,?,?)", (chat_id, user_id, w, int(time.time())))
        self.conn.commit()
        return w

    def reset_warns(self, chat_id, user_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        self.conn.commit()

db = DB()

# -------------------------
# Utility functions
# -------------------------
def in_enforce_window():
    try:
        start = db.get("daily_start") or DEFAULTS["daily_start"]
        end = db.get("daily_end") or DEFAULTS["daily_end"]
        fmt = "%H:%M"
        now = datetime.utcnow().time()
        s = datetime.strptime(start, fmt).time()
        e = datetime.strptime(end, fmt).time()
        if s <= e:
            return s <= now <= e
        else:
            return now >= s or now <= e
    except Exception:
        return True

def is_vulgar(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    for pat in VULGAR_WORDS:
        if re.search(pat, t):
            return True
    return False

def is_nsfw(file_path: str) -> bool:
    """
    Placeholder NSFW detector.
    Replace this with a real model or API call for production.
    Current heuristic: filename contains keywords.
    """
    if not file_path:
        return False
    fname = os.path.basename(file_path).lower()
    if "nsfw" in fname or "porn" in fname or "xxx" in fname:
        return True
    return False

# safe tmp folder
TMP_DIR = os.path.join(os.getcwd(), "tmp")
os.makedirs(TMP_DIR, exist_ok=True)

# -------------------------
# Flask keepalive (background)
# -------------------------
web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "✅ ShieldX Bot is running (stable)!"

def run_web():
    # Use port 8080 (Render/Koyeb default)
    web_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# Run Flask in background thread
Thread(target=run_web, daemon=True).start()

# -------------------------
# Pyrogram client
# -------------------------
client = Client("shieldx", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# start-up cleanup: try removing stale session files (best-effort)
def try_remove_session_files():
    sess_files = ["shieldx.session", "shieldx_bot.session", "shieldx_bot.session-journal", "shieldx.session-journal"]
    for f in sess_files:
        p = os.path.join(os.getcwd(), f)
        try:
            if os.path.exists(p):
                os.remove(p)
                logging.info(f"Removed stale session file: {p}")
        except Exception:
            # ignore if locked — restart loop will handle after earlier processes die
            logging.debug(f"Could not remove session file (ignored): {p}")

try_remove_session_files()

# -------------------------
# Commands & moderation
# -------------------------
@client.on_message(filters.command("start"))
async def start_cmd(_, message):
    await message.reply_text(
        "🤖 ShieldX Media Protector (stable)\n\n"
        "Auto-moderation is active. Owner controls: only owner/co-owner can change settings.\n"
        "Use /help in group or DM to see admin commands (owner-only).",
        quote=True
    )

@client.on_message(filters.command("help"))
async def help_cmd(_, message):
    txt = (
        "ShieldX commands (owner only):\n"
        "/shieldx_status - show configuration\n"
        "/shieldx_set <feature> <on|off> - toggle\n"
        "/shieldx_time <HH:MM> <HH:MM> - set UTC active window\n"
        "/shieldx_set_threshold <n> - nsfw threshold\n        (owner/co-owner only)\n"
    )
    await message.reply_text(txt, quote=True)

# owner-only check helper
def is_owner_id(uid):
    return uid and (uid == OWNER_ID or uid == CO_OWNER_ID)

@client.on_message(filters.command("shieldx_status") & filters.user(lambda _, m: is_owner_id(m.from_user.id if m.from_user else None)))
async def status_cmd(_, message):
    conf = {k: db.get(k) for k in DEFAULTS.keys()}
    msg = "ShieldX status:\n" + "\n".join(f"{k}: {v}" for k, v in conf.items())
    await message.reply_text(msg, quote=True)

@client.on_message(filters.command("shieldx_set") & filters.user(lambda _, m: is_owner_id(m.from_user.id if m.from_user else None)))
async def set_cmd(_, message):
    try:
        _, key, val = message.text.split(maxsplit=2)
    except Exception:
        return await message.reply_text("Usage: /shieldx_set <feature> <on|off>", quote=True)
    if key not in DEFAULTS:
        return await message.reply_text("Unknown feature: " + ", ".join(DEFAULTS.keys()), quote=True)
    newv = val.lower() in ("on", "true", "1")
    db.set(key, newv)
    await message.reply_text(f"✅ {key} set to {newv}", quote=True)

@client.on_message(filters.command("shieldx_time") & filters.user(lambda _, m: is_owner_id(m.from_user.id if m.from_user else None)))
async def time_cmd(_, message):
    try:
        _, s, e = message.text.split()
    except Exception:
        return await message.reply_text("Usage: /shieldx_time HH:MM HH:MM (UTC)", quote=True)
    db.set("daily_start", s)
    db.set("daily_end", e)
    await message.reply_text(f"✅ Window set: {s} - {e} (UTC)", quote=True)

@client.on_message(filters.command("shieldx_set_threshold") & filters.user(lambda _, m: is_owner_id(m.from_user.id if m.from_user else None)))
async def threshold_cmd(_, message):
    try:
        _, n = message.text.split(maxsplit=1)
        n = int(n)
    except Exception:
        return await message.reply_text("Usage: /shieldx_set_threshold <number>", quote=True)
    db.set("nsfw_threshold", n)
    await message.reply_text(f"✅ NSFW threshold set to {n}", quote=True)

@client.on_message(filters.command("shieldx_unmute") & filters.user(lambda _, m: is_owner_id(m.from_user.id if m.from_user else None)))
async def unmute_cmd(_, message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to the user's message to unmute.", quote=True)
    target = message.reply_to_message.from_user.id
    try:
        await client.unban_chat_member(message.chat.id, target)
    except Exception:
        pass
    db.reset_warns(message.chat.id, target) if hasattr(db, "reset_warns") else None
    db.reset_nsfw(message.chat.id, target)
    await message.reply_text("✅ User unmuted and counters reset.", quote=True)

# core moderation (applies to groups)
@client.on_message(filters.chat_type.groups & ~filters.user(lambda _, m: is_owner_id(m.from_user.id if m.from_user else None)))
async def mod_handler(_, message):
    try:
        # enforcement window
        if not in_enforce_window():
            return

        media_delete = db.get("media_delete")
        nsfw_auto = db.get("nsfw_auto_delete")
        abuse = db.get("abuse_filter")
        auto_mute = db.get("auto_mute")
        threshold = db.get("nsfw_threshold") or DEFAULTS["nsfw_threshold"]

        # text abuse check
        if abuse and message.text:
            if is_vulgar(message.text):
                # delete + warn
                try:
                    await message.delete()
                except Exception:
                    pass
                w = db.add_warn(message.chat.id, message.from_user.id)
                await message.reply_text(f"⚠️ {message.from_user.first_name} warned for vulgar language. ({w})", quote=True)
                if w >= db.get("warn_limit"):
                    try:
                        await client.restrict_chat_member(message.chat.id, message.from_user.id, ChatPermissions())
                        await message.reply_text("🔇 User muted due to repeated warnings.", quote=True)
                    except Exception:
                        pass
                return

        # media handling
        if message.media and media_delete:
            # download to tmp
            fp = None
            try:
                fp = await client.download_media(message, file_name=os.path.join(TMP_DIR, f"{message.message_id}_"))
            except Exception:
                fp = None

            nsfw_flag = False
            try:
                nsfw_flag = is_nsfw(fp) if nsfw_auto else False
            except Exception:
                nsfw_flag = False

            if nsfw_flag and nsfw_auto:
                try:
                    await message.delete()
                except Exception:
                    pass
                cnt = db.incr_nsfw(message.chat.id, message.from_user.id)
                await message.reply_text(f"🚫 NSFW detected. Count: {cnt}/{threshold}", quote=True)
                if cnt >= threshold and auto_mute:
                    try:
                        await client.restrict_chat_member(message.chat.id, message.from_user.id, ChatPermissions())
                        await message.reply_text("🔒 User muted permanently due to repeated NSFW uploads.", quote=True)
                        db.reset_nsfw(message.chat.id, message.from_user.id)
                    except Exception:
                        pass
                # cleanup file
                try:
                    if fp and os.path.exists(fp):
                        os.remove(fp)
                except Exception:
                    pass
                return

            # otherwise delete media (policy)
            try:
                await message.delete()
                await message.reply_text("📥 Media removed (policy).", quote=True)
            except Exception:
                pass
            try:
                if fp and os.path.exists(fp):
                    os.remove(fp)
            except Exception:
                pass
            return

    except Exception as ex:
        logging.exception("Error in mod_handler: %s", ex)

# -------------------------
# Main run loop (old-format stable)
# -------------------------
if __name__ == "__main__":
    logging.info("🚀 ShieldX Final starting (stable loop + Flask keepalive).")
    # infinite restart loop — keeps bot alive on crash
    while True:
        try:
            client.run()
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received — exiting cleanly.")
            break
        except Exception as e:
            logging.exception("⚠️ Bot crashed. Restarting in 5s... %s", e)
            time.sleep(5)
            continue
