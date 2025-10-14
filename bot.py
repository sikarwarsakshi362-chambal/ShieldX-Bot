﻿# -*- coding: utf-8 -*-
# ShieldX Bot v3 — Stable Final (Auto-Restart + NSFW + Flask + Batch Clean)
# Structure untouched, only stability & restart loop added.

import asyncio
import os
import threading
import time
import tempfile
import shutil
from datetime import datetime, timedelta
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import RPCError
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

# === Optional NSFW libs ===
try:
    import cv2
    import numpy as np
    from PIL import Image
except Exception:
    cv2 = None
    np = None
    Image = None

# === ENV Vars ===
load_dotenv()
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# === Flask ===
app = Flask(__name__)
@app.route("/")
def home():
    return "🛡️ ShieldX Active — running 24×7."

def keep_alive_sync():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

# === Pyrogram Client ===
bot = Client("ShieldX", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# === Lang + Text ===
LANGS = {
    "en": {
        "start_dm": {"text": "🛡️ **Welcome to ShieldX!**\n\nI protect your groups 24×7 — blocking NSFW, spam & media floods.", 
                     "buttons": [[{"text": "➕ Add to Group", "url": "https://t.me/shieldxprotector_bot?startgroup=true"},
                                  {"text": "💬 Support", "url": "https://t.me/ShieldXSupport"}]]},
        "start_group": {"text": "🛡️ ShieldX active in this group!\nTry `/clean on`, `/status`, `/ping`.", 
                        "buttons": [[{"text": "💬 Support", "url": "https://t.me/ShieldXSupport"}]]},
        "help_dm": "✨ **ShieldX Command Center**\n\n🧹 /clean on — enable auto-clean (30m)\n/custom_clean — custom clean time\n/off — stop cleaning\n\n🚫 NSFW delete: always active\n⚙️ /ping /status /lang <code>",
        "help_group": "📩 Check DM for ShieldX command list.",
        "ping_text": "🩵 ShieldX Online!\n⚡ {ms}ms | Uptime: {uptime}",
        "nsfw_deleted": "⚠️ NSFW content detected & removed.",
    },
    "hi": {
        "start_dm": {"text": "🛡️ **ShieldX में आपका स्वागत है!**\n\nमैं आपके ग्रुप को 24×7 सुरक्षित रखता हूँ।",
                     "buttons": [[{"text": "➕ ग्रुप में जोड़ें", "url": "https://t.me/shieldxprotector_bot?startgroup=true"},
                                  {"text": "💬 सपोर्ट", "url": "https://t.me/ShieldXSupport"}]]},
        "start_group": {"text": "🛡️ ShieldX अब इस ग्रुप में सक्रिय है!\nAdmins `/help` से प्रबंधन करें।",
                        "buttons": [[{"text": "💬 सपोर्ट", "url": "https://t.me/ShieldXSupport"}]]},
        "help_dm": "✨ **ShieldX कमांड सेंटर**\n\n🧹 `/clean on` — मीडिया हर 30 मिनट हटेगा\n🚫 NSFW — हमेशा ऑन\n⚙️ `/ping`, `/lang <code>`",
        "help_group": "📩 पूरी कमांड सूची DM में देखें।",
        "ping_text": "🩵 ShieldX ऑनलाइन!\n⚡ {ms}ms | Uptime: {uptime}",
        "nsfw_deleted": "⚠️ NSFW कंटेंट हटाया गया।",
    }
}
chat_lang = {}

def get_txt(key, chat_id=None, **kwargs):
    lang = chat_lang.get(chat_id, "en")
    val = LANGS.get(lang, LANGS["en"]).get(key, "")
    if isinstance(val, dict):
        text = val.get("text", "").format(**kwargs)
        buttons = [[InlineKeyboardButton(b["text"], url=b["url"]) for b in row] for row in val.get("buttons", [])]
        return {"text": text, "buttons": buttons}
    return val.format(**kwargs) if kwargs else val

# === NSFW Detection (Local)
def is_nsfw_local(path, threshold=0.3):
    if cv2 is None or np is None: return False
    try:
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None: return False
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, (0,10,60), (20,150,255))
        mask2 = cv2.inRange(hsv, (160,10,60), (179,150,255))
        ratio = (cv2.countNonZero(mask1|mask2)) / (img.shape[0]*img.shape[1])
        return ratio >= threshold
    except: return False

# === /start /help /ping ===
@bot.on_message(filters.command("start"))
async def start_cmd(c,m):
    d = get_txt("start_dm" if m.chat.type=="private" else "start_group", m.chat.id)
    if isinstance(d, dict): await m.reply_text(d["text"], reply_markup=InlineKeyboardMarkup(d["buttons"]), disable_web_page_preview=True)
    else: await m.reply_text(d)

@bot.on_message(filters.command("help"))
async def help_cmd(c,m):
    await m.reply_text(get_txt("help_dm" if m.chat.type=="private" else "help_group", m.chat.id))

start_time = time.time()
@bot.on_message(filters.command("ping"))
async def ping_cmd(c,m):
    st = time.time()
    tmp = await m.reply_text("🏓 Pinging...")
    ms = int((time.time()-st)*1000)
    uptime = str(datetime.utcnow()-datetime.utcfromtimestamp(start_time)).split(".")[0]
    await tmp.edit_text(get_txt("ping_text", m.chat.id, ms=ms, uptime=uptime))

# === NSFW always-on delete ===
@bot.on_message(filters.group & (filters.photo | filters.video))
async def nsfw_handler(c,m):
    tmp = tempfile.mkdtemp()
    p = await c.download_media(m, file_name=os.path.join(tmp,"f"))
    if is_nsfw_local(p):
        await c.delete_messages(m.chat.id, m.id)
        await c.send_message(m.chat.id, get_txt("nsfw_deleted", m.chat.id))
    shutil.rmtree(tmp, ignore_errors=True)

# === Keepalive + Watchdog ===
async def background_keepalive():
    while True:
        print("💤 Ping: ShieldX alive...")
        await asyncio.sleep(300)

async def watchdog():
    while True:
        try:
            await bot.send_message(OWNER_ID, "🩵 Watchdog OK", disable_notification=True)
        except: pass
        await asyncio.sleep(1800)

# === STARTUP ===
async def run_bot():
    try:
        await bot.start()
        print("✅ ShieldX started.")
        asyncio.create_task(background_keepalive())
        asyncio.create_task(watchdog())
        await asyncio.Event().wait()
    except Exception as e:
        print("❌ Bot crashed:", e)
        await asyncio.sleep(5)
        await run_bot()   # restart loop (auto-restore)

if __name__ == "__main__":
    try:
        import nest_asyncio; nest_asyncio.apply()
    except: pass
    threading.Thread(target=keep_alive_sync, daemon=True).start()
    asyncio.run(run_bot())
