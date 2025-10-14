# -*- coding: utf-8 -*-
# ShieldX v4.1 — Advanced moderation + batch-clean + NSFW warn/mute rules
# NOTE: This file is an enhanced drop-in replacement — nothing removed, only additions.

import asyncio
import json
import os
import threading
import time
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List

import aiohttp
import requests
from flask import Flask
from pyrogram import Client, filters, types
from pyrogram.errors import RPCError, ChatWriteForbidden
from dotenv import load_dotenv

# optional pillow for local heuristic
try:
    from PIL import Image
except Exception:
    Image = None

# ---------------------------
# LOAD ENV
# ---------------------------
load_dotenv()
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID_RAW = os.getenv("OWNER_ID", "")  # allow comma-separated list (owner,co-owner,...)
HF_API_KEY = os.getenv("HF_API_KEY", "")  # optional HuggingFace key (free or your key)
RENDER_HEALTH_URL = os.getenv("RENDER_HEALTH_URL", "")  # optional health url
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "") or os.getenv("RENDER_URL", "") or os.getenv("PRIMARY_URL", "")
SUPPORT_URL = os.getenv("SUPPORT_URL", "")  # optional support button URL

# parse owners/co-owners
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

OWNER_IDS = parse_owner_ids(OWNER_ID_RAW)

# ---------------------------
# STORAGE
# ---------------------------
DATA_FILE = "data.json"
def load_data() -> Dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}
def save_data(d: Dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except:
        pass

DATA = load_data()
if "_global" not in DATA:
    DATA["_global"] = {"clean_enabled": True}

def ensure_chat(chat_id):
    cid = str(chat_id)
    if cid not in DATA:
        DATA[cid] = {"clean_on": False, "delete_minutes": 30, "lang": "en-in"}
        save_data(DATA)
    return DATA[cid]

def is_clean_enabled_global():
    return DATA.get("_global", {}).get("clean_enabled", True)

def set_clean_enabled_global(val: bool):
    DATA.setdefault("_global", {})["clean_enabled"] = bool(val)
    save_data(DATA)

# ---------------------------
# MESSAGES / LOCALES (kept bilingual)
# ---------------------------
MESSAGES = {
    "en-in": {
        "start_dm": "🛡️ *ShieldX Protection*\nI keep your groups clean. Use buttons below.",
        "start_group": "🛡️ ShieldX active in this group.",
        "help_dm": "✨ *ShieldX Commands*\n\n• /clean [time] — enable auto-clean (admins)\n• /cleanoff — disable auto-clean (owner)\n• /cleanon — enable auto-clean (owner)\n• /cleanstatus — show status\n• /cleanall — delete media (owner/co-owner only, last 24h)\n• /warnreset <user_id> — reset warns (owner/admin)\n• /lang <code> — set language\n• /status — show current status\n\nDefault auto-clean: 30 minutes.",
        "help_group": "📩 Sent you a DM with commands.",
        "auto_on": "✅ Auto-clean enabled — media will be cleared every {t}.",
        "auto_off": "🛑 Auto-clean disabled.",
        "auto_set": "✅ Auto-clean enabled — interval set to {t}.",
        "cleanall_start": "🧹 Starting safe media purge for last {t} ... This may take a while.",
        "cleanall_done": "✅ Media purge complete — removed {n} media items from last {t}.",
        "clean_done": "✅ Media purge complete — removed {n} media items from last {t}.",
        "only_admin": "⚠️ Only group admins can use this.",
        "only_owner": "⚠️ Only group owner or configured co-owners can use this.",
        "status_text": "🧹 Auto-clean: {on} | Interval: {t}",
        "ping_text": "🏓 Pong! {ms}ms",
        "nsfw_deleted": "⚠️ NSFW content detected and removed. Follow group rules.",
        "nsfw_warn": "⚠️ NSFW content auto-deleted. User {name} warned ({count}/5).",
        "nsfw_muted": "🚫 User {name} muted permanently for rapid NSFW spam.",
        "need_admin_bot": "⚠️ I need admin permissions with *delete messages* to perform this action. Please grant admin and try again.",
        "no_media_found": "ℹ️ No media messages found in the requested range.",
        "clean_in_progress": "🧹 Cleaning media from last {t} — running in safe batch mode. Please wait...",
        "clean_batch": "🧹 Cleaning batch {i}/{total_batches} — deleted {n} so far...",
        "clean_summary": "✅ Cleaned {n} media items across {batches} batches (last {t}).",
    },
    "hi": {
        "start_dm": "🛡️ *ShieldX सुरक्षा*\nमैं आपके ग्रुप्स को साफ़ रखता हूँ। नीचे बटन देखें।",
        "start_group": "🛡️ ShieldX समूह में सक्रिय है।",
        "help_dm": "कमांड:\n/clean [time]\n/cleanoff\n/cleanon\n/cleanstatus\n/cleanall\n/warnreset <user_id>\n/lang <code>\n/status",
        "help_group": "कमांड DM में भेज दी गई हैं।",
        "auto_on": "✅ Auto-clean चालू — हर {t} पर साफ़ करेगा।",
        "auto_off": "🛑 Auto-clean बंद किया गया।",
        "auto_set": "✅ Auto-clean सेट किया गया — अंतराल {t}.",
        "cleanall_start": "🧹 पिछले {t} की मीडिया हटाई जा रही है... कृपया प्रतीक्षा करें।",
        "cleanall_done": "✅ मीडिया हटाई पूरी हुई — हटाए गए आइटम: {n}.",
        "clean_done": "✅ मीडिया हटाई पूरी हुई — हटाए गए आइटम: {n}.",
        "only_admin": "⚠️ केवल group admins उपयोग कर सकते हैं।",
        "only_owner": "⚠️ केवल group owner या configured co-owners उपयोग कर सकते हैं।",
        "status_text": "🧹 Auto-clean: {on} | Interval: {t}",
        "ping_text": "🏓 Pong! {ms}ms",
        "nsfw_deleted": "⚠️ NSFW सामग्री मिली और हटा दी गई। नियमों का पालन करें।",
        "nsfw_warn": "⚠️ NSFW मिली और हटा दी गई। उपयोगकर्ता {name} को चेतावनी दी गई ({count}/5)।",
        "nsfw_muted": "🚫 उपयोगकर्ता {name} को तेज़ NSFW स्पैम के लिए स्थायी रूप से म्यूट किया गया।",
        "need_admin_bot": "⚠️ मुझे admin पर *delete messages* की अनुमति चाहिए ताकि मैं यह कर सकूँ। कृपया अनुमति दे और दोबारा कोशिश करें।",
        "no_media_found": "ℹ️ अनुरोधित समय सीमा में कोई मीडिया संदेश नहीं मिला।",
        "clean_in_progress": "🧹 पिछले {t} की मीडिया हटाई जा रही है... कृपया प्रतीक्षा करें...",
        "clean_batch": "🧹 बैच {i}/{total_batches} साफ हो रहा है — अब तक हटाए गए: {n}...",
        "clean_summary": "✅ कुल {n} मीडिया हटाए गए {batches} बैचों में (पिछले {t})।",
    },
}

DEFAULT_LOCALE = "en-in"
def get_msg(key: str, chat_id, **kwargs):
    cfg = ensure_chat(chat_id)
    lang = cfg.get("lang", DEFAULT_LOCALE)
    template = MESSAGES.get(lang, MESSAGES.get(DEFAULT_LOCALE)).get(key, "")
    return template.format(**kwargs)

# ---------------------------
# APP INIT
# ---------------------------
app = Flask(__name__)
bot = Client("ShieldXBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------------------
# Utilities: time parsing, fmt
# ---------------------------
def fmt_timespan(minutes: int) -> str:
    if minutes % 1440 == 0 and minutes != 0:
        days = minutes // 1440
        return f"{days} day(s)"
    if minutes >= 60 and minutes % 60 == 0:
        hours = minutes // 60
        return f"{hours} hour(s)"
    return f"{minutes} minute(s)"

def parse_time_token(token: str):
    token = token.strip().lower()
    try:
        if token.endswith("m"):
            val = int(token[:-1])
            return val
        if token.endswith("h"):
            val = int(token[:-1]) * 60
            return val
        if token.endswith("d"):
            val = int(token[:-1]) * 1440
            return val
        if token.isdigit():
            return int(token)
    except:
        return None
    return None

# ---------------------------
# NSFW settings
# ---------------------------
HF_MODEL = "Falconsai/nsfw_image_detection"
HF_API = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}

NSFW_CONF_THRESHOLD = 0.8
NSFW_WINDOW_SEC = 3         # rapid spam window for instant mute
NSFW_SPAM_COUNT = 5        # count threshold
WARNING_TTL = 60           # seconds to auto-delete normal warn message
WARNING_RESET_TTL = 3600   # 1 hour -> warn counters age out after 1 hour

NSFW_TRACKERS: Dict[str, Dict[str, List[float]]] = {}

# ---------------------------
# Helper: HF call (if key present)
# ---------------------------
async def call_hf_nsfw(file_path: str):
    if not HF_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                data = f.read()
            async with session.post(HF_API, data=data, headers=HF_HEADERS, timeout=30) as resp:
                if resp.status == 200:
                    try:
                        return await resp.json()
                    except:
                        return None
                else:
                    txt = await resp.text()
                    print("HF NSFW error:", resp.status, txt)
                    return None
    except Exception as e:
        print("HF request exception:", e)
        return None

# ---------------------------
# Local lightweight NSFW heuristic (Pillow-based)
# ---------------------------
def is_image_path(path: str) -> bool:
    if not path:
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif")

def is_probably_nsfw_local(image_path: str) -> bool:
    if Image is None or not is_image_path(image_path):
        return False
    try:
        img = Image.open(image_path).convert("RGB")
        img = img.resize((160, 160))
        pixels = img.getdata()
        total = 0
        skin = 0
        for r,g,b in pixels:
            total += 1
            if r > 95 and g > 40 and b > 20 and (max(r,g,b)-min(r,g,b)) > 15 and r > g and r > b:
                skin += 1
            elif r > 60 and g > 40 and b > 30 and r > g:
                skin += 1
        if total == 0:
            return False
        return (skin/total) >= 0.30
    except Exception as e:
        print("Local NSFW heuristic failed:", e)
        return False

# ---------------------------
# Flask keep-alive endpoints
# ---------------------------
@app.route("/")
def index():
    return "🩵 ShieldX Bot — alive"

@app.route("/healthz")
def healthz():
    return "OK", 200

def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ---------------------------
# COMMANDS (enhanced UI)
# ---------------------------
@bot.on_message(filters.command("start", prefixes=["/", "!"]))
async def start_cmd(client, message):
    cfg = ensure_chat(message.chat.id if message.chat else message.from_user.id)
    if message.chat and message.chat.type == "private":
        text = get_msg("start_dm", message.chat.id)
        me = await client.get_me()
        buttons = [
            [types.InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{me.username}?startgroup=new")],
            [types.InlineKeyboardButton("📘 Commands", callback_data="sx_help")],
        ]
        if SUPPORT_URL:
            buttons.append([types.InlineKeyboardButton("🛠️ Support", url=SUPPORT_URL)])
        header = text + "\n\n✅ *Status:* Active & protecting groups.\n⏱️ *Keepalive:* 5s ping enabled (Render)."
        await message.reply_text(header, reply_markup=types.InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        # nicer group message (keeps original)
        await message.reply(get_msg("start_group", message.chat.id) + " — ShieldX protecting this group 24x7.", quote=False)

@bot.on_message(filters.command("help", prefixes=["/", "!"]))
async def help_cmd(client, message):
    if message.chat and message.chat.type == "private":
        base = get_msg("help_dm", message.chat.id)
        extra = "\n\nℹ️ Tip: Add me to your group and give me *delete messages* admin to enable cleaning."
        await message.reply_text(base + extra, disable_web_page_preview=True)
    else:
        try:
            await message.reply(get_msg("help_group", message.chat.id), quote=False)
        except ChatWriteForbidden:
            pass

@bot.on_callback_query(filters.regex(r"^sx_help$"))
async def cb_help(client, query):
    await query.answer()
    try:
        await query.message.edit_text(get_msg("help_dm", query.message.chat.id))
    except:
        pass

@bot.on_message(filters.command("ping", prefixes=["/", "!"]))
async def ping_cmd(client, message):
    t0 = time.time()
    m = await message.reply("🏓 Checking latency...")
    ms = int((time.time() - t0) * 1000)
    bot_user = await client.get_me()
    txt = get_msg("ping_text", message.chat.id, ms=ms)
    txt += f"\n\n🔹 Bot: @{bot_user.username}\n🔹 Uptime check: OK"
    await m.edit_text(txt)

# status/lang/cleanstatus/cleanon/cleanoff unchanged (kept original behavior)
@bot.on_message(filters.command("status", prefixes=["/", "!"]) & filters.group)
async def status_cmd(client, message):
    cfg = ensure_chat(message.chat.id)
    on = "On" if cfg.get("clean_on") else "Off"
    t = fmt_timespan(cfg.get("delete_minutes", 30))
    await message.reply(get_msg("status_text", message.chat.id, on=on, t=t), quote=False)

@bot.on_message(filters.command("lang", prefixes=["/", "!"]) & filters.group)
async def lang_cmd(client, message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /lang <locale_code> (eg. en-in, hi)", quote=False)
        return
    code = args[1].lower()
    if code not in MESSAGES:
        await message.reply(f"Unsupported. Supported: {', '.join(MESSAGES.keys())}", quote=False)
        return
    cfg = ensure_chat(message.chat.id)
    cfg["lang"] = code
    save_data(DATA)
    await message.reply(get_msg("start_group", message.chat.id) + f"\n🌐 Language: {code}", quote=False)

@bot.on_message(filters.command("cleanstatus", prefixes=["/", "!"]) & filters.group)
async def cleanstatus_cmd(client, message):
    cfg = ensure_chat(message.chat.id)
    global_state = is_clean_enabled_global()
    chat_on = cfg.get("clean_on", False)
    await message.reply(f"Global clean: {'ON' if global_state else 'OFF'}\nChat auto-clean: {'ON' if chat_on else 'OFF'}\nInterval: {fmt_timespan(cfg.get('delete_minutes',30))}", quote=False)

@bot.on_message(filters.command("cleanon", prefixes=["/", "!"]))
async def cleanon_cmd(client, message):
    user_id = message.from_user.id
    if user_id not in OWNER_IDS:
        await message.reply("❌ Only owner can enable cleaning globally.", quote=False)
        return
    set_clean_enabled_global(True)
    await message.reply("✅ Global cleaning ENABLED.", quote=False)

@bot.on_message(filters.command("cleanoff", prefixes=["/", "!"]))
async def cleanoff_cmd(client, message):
    user_id = message.from_user.id
    if user_id not in OWNER_IDS:
        await message.reply("❌ Only owner can disable cleaning globally.", quote=False)
        return
    set_clean_enabled_global(False)
    await message.reply("🛑 Global cleaning DISABLED.", quote=False)

# ---------------------------
# Batch delete with progress
# ---------------------------
async def batch_delete_media_in_range_with_progress(client, chat_id: int, minutes: int, progress_msg=None, batch_size=100):
    deleted = 0
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    # collect media message ids in range first (to compute batches)
    msg_ids = []
    try:
        async for msg in client.get_chat_history(chat_id, limit=5000):
            if msg.date < cutoff:
                break
            if msg.media:
                msg_ids.append(msg.message_id)
    except Exception as e:
        print("Error collecting media ids:", e)
        return 0

    if not msg_ids:
        return 0

    total = len(msg_ids)
    batches = (total + batch_size - 1) // batch_size
    for i in range(batches):
        start = i * batch_size
        end = min(start + batch_size, total)
        batch = msg_ids[start:end]
        try:
            # delete as list where supported
            await client.delete_messages(chat_id, batch)
            deleted += len(batch)
        except Exception as e:
            # fallback: delete one-by-one if bulk fails
            for mid in batch:
                try:
                    await client.delete_messages(chat_id, mid)
                    deleted += 1
                except Exception:
                    pass
        # update progress message if provided
        if progress_msg:
            try:
                await progress_msg.edit_text(get_msg("clean_batch", chat_id, i+1, batches, n=deleted))
            except:
                pass
        # small delay to avoid flood waits
        await asyncio.sleep(1)
    return deleted

# /clean (batch + progress)
@bot.on_message(filters.command("clean", prefixes=["/", "!"]) & filters.group)
async def clean_cmd(client, message):
    if not is_clean_enabled_global():
        await message.reply("⚠️ Media clean system is currently disabled. Owner can enable with /cleanon.", quote=False)
        return
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ("administrator", "creator"):
            await message.reply(get_msg("only_admin", message.chat.id), quote=False)
            return
    except:
        await message.reply(get_msg("only_admin", message.chat.id), quote=False)
        return

    # ensure bot admin permissions
    try:
        me = await client.get_me()
        bot_member = await client.get_chat_member(message.chat.id, me.id)
        if bot_member.status not in ("administrator", "creator"):
            await message.reply(get_msg("need_admin_bot", message.chat.id), quote=False)
            return
    except:
        pass

    args = message.text.split()
    if len(args) > 1:
        mins = parse_time_token(args[1].lower())
        if mins is None or mins < 20 or mins > 1440:
            await message.reply("⚠️ Provide time between 20m and 24h (e.g. 20m, 2h, 1d).", quote=False)
            return
    else:
        mins = 30

    cfg = ensure_chat(message.chat.id)
    cfg["clean_on"] = True
    cfg["delete_minutes"] = mins
    save_data(DATA)

    human = fmt_timespan(mins)
    start_msg = await message.reply(get_msg("clean_in_progress", message.chat.id, t=human), quote=False)
    deleted = await batch_delete_media_in_range_with_progress(client, message.chat.id, mins, progress_msg=start_msg, batch_size=100)
    if deleted == 0:
        await start_msg.edit_text(get_msg("no_media_found", message.chat.id), quote=False)
    else:
        batches = (deleted + 100 - 1) // 100
        await start_msg.edit_text(get_msg("clean_summary", message.chat.id, n=deleted, batches=batches, t=human), quote=False)

# /cleanall similar to clean but for 1440 minutes
@bot.on_message(filters.command("cleanall", prefixes=["/", "!"]) & filters.group)
async def cleanall_cmd(client, message):
    user_id = message.from_user.id
    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        is_owner = (member.status == "creator")
    except:
        is_owner = False

    if not (is_owner or user_id in OWNER_IDS):
        await message.reply(get_msg("only_owner", message.chat.id), quote=False)
        return
    if not is_clean_enabled_global():
        await message.reply("⚠️ Media clean system is currently disabled. Owner can enable with /cleanon.", quote=False)
        return
    try:
        me = await client.get_me()
        bot_member = await client.get_chat_member(message.chat.id, me.id)
        if bot_member.status not in ("administrator", "creator"):
            await message.reply(get_msg("need_admin_bot", message.chat.id), quote=False)
            return
    except:
        pass

    human = fmt_timespan(1440)
    start_msg = await message.reply(get_msg("cleanall_start", message.chat.id, t=human), quote=False)
    deleted = await batch_delete_media_in_range_with_progress(client, message.chat.id, 1440, progress_msg=start_msg, batch_size=100)
    if deleted == 0:
        await start_msg.edit_text(get_msg("no_media_found", message.chat.id), quote=False)
    else:
        batches = (deleted + 100 - 1) // 100
        await start_msg.edit_text(get_msg("cleanall_done", message.chat.id, n=deleted, t=human), quote=False)

# warnreset unchanged
@bot.on_message(filters.command("warnreset", prefixes=["/", "!"]))
async def warnreset_cmd(client, message):
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ("administrator", "creator") and message.from_user.id not in OWNER_IDS:
            await message.reply(get_msg("only_admin", message.chat.id), quote=False)
            return
    except:
        await message.reply(get_msg("only_admin", message.chat.id), quote=False)
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /warnreset <user_id>", quote=False)
        return
    try:
        uid = str(int(args[1]))
    except:
        await message.reply("Invalid user id.", quote=False)
        return
    for chat_map in NSFW_TRACKERS.values():
        chat_map.pop(uid, None)
    await message.reply("✅ Warn counters reset for user.", quote=False)

# ---------------------------
# NSFW counters helper
# ---------------------------
def prune_nsfw_counters(chat_id: str, user_id: str):
    now = time.time()
    chat_map = NSFW_TRACKERS.setdefault(str(chat_id), {})
    arr = chat_map.setdefault(str(user_id), [])
    # keep timestamps within WARNING_RESET_TTL (1 hour) to allow warn counting
    arr[:] = [t for t in arr if now - t <= WARNING_RESET_TTL]
    chat_map[str(user_id)] = arr
    NSFW_TRACKERS[str(chat_id)] = chat_map
    return arr

# main media & NSFW handler
@bot.on_message(filters.group & (filters.photo | filters.video | filters.sticker | filters.animation | filters.document))
async def media_nsfw_handler(client, message):
    if message.from_user is None:
        return
    chat_id = message.chat.id
    uid = message.from_user.id
    tmpdir = None
    try:
        tmpdir = tempfile.mkdtemp()
        path = await client.download_media(message, file_name=os.path.join(tmpdir, "media"))
        if not path or not os.path.exists(path):
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
            return

        # HF remote attempt
        res = await call_hf_nsfw(path)
        is_nsfw = False
        try:
            if res:
                if isinstance(res, list) and len(res)>0 and isinstance(res[0], dict):
                    item = res[0]
                    label = str(item.get("label","")).lower()
                    score = float(item.get("score",0) or 0)
                    if "nsfw" in label or score >= NSFW_CONF_THRESHOLD:
                        is_nsfw = True
                elif isinstance(res, dict):
                    if "label" in res and "score" in res:
                        lab = str(res.get("label","")).lower()
                        sc = float(res.get("score",0) or 0)
                        if "nsfw" in lab or sc >= NSFW_CONF_THRESHOLD:
                            is_nsfw = True
                    else:
                        def find_any(d):
                            if isinstance(d, dict):
                                if "label" in d and "score" in d:
                                    return d
                                for v in d.values():
                                    r = find_any(v)
                                    if r:
                                        return r
                            elif isinstance(d, list):
                                for el in d:
                                    r = find_any(el)
                                    if r:
                                        return r
                            return None
                        f = find_any(res)
                        if f:
                            lab = str(f.get("label","")).lower()
                            sc = float(f.get("score",0) or 0)
                            if "nsfw" in lab or sc >= NSFW_CONF_THRESHOLD:
                                is_nsfw = True
        except Exception as e:
            print("NSFW parse error:", e, res)

        # fallback to local heuristic if HF unavailable
        if not is_nsfw and (res is None):
            try:
                if is_image_path(path) and is_probably_nsfw_local(path):
                    is_nsfw = True
            except Exception as e:
                print("Local NSFW heuristic error:", e)

        # cleanup temp file
        try:
            os.remove(path)
        except:
            pass
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)

        if not is_nsfw:
            cfg = ensure_chat(chat_id)
            if cfg.get("clean_on") and is_clean_enabled_global():
                mins = cfg.get("delete_minutes",30)
                delay = int(mins) * 60
                if delay == 0:
                    try:
                        await client.delete_messages(chat_id, message.message_id)
                    except:
                        pass
                else:
                    asyncio.create_task(schedule_delete(client, chat_id, message.message_id, delay))
            return

        # NSFW detected -> delete message
        try:
            await client.delete_messages(chat_id, message.message_id)
        except:
            pass

        # warn logic: prune, append, check rapid spam window
        arr = prune_nsfw_counters(str(chat_id), str(uid))
        arr.append(time.time())
        NSFW_TRACKERS[str(chat_id)][str(uid)] = arr

        # check rapid spam condition: if last NSFW_SPAM_COUNT timestamps exist and fit within NSFW_WINDOW_SEC
        if len(arr) >= NSFW_SPAM_COUNT:
            # check time window between earliest of last N and latest
            last_n = arr[-NSFW_SPAM_COUNT:]
            if (last_n[-1] - last_n[0]) <= NSFW_WINDOW_SEC:
                # rapid spam -> permanent mute
                try:
                    me = await client.get_me()
                    bot_member = await client.get_chat_member(chat_id, me.id)
                    if bot_member.status not in ("administrator", "creator"):
                        await client.send_message(chat_id, get_msg("need_admin_bot", chat_id))
                    else:
                        perm = types.ChatPermissions(
                            can_send_messages=False,
                            can_send_media_messages=False,
                            can_send_other_messages=False,
                            can_add_web_page_previews=False,
                        )
                        until_ts = int(time.time()) + 10*365*24*3600
                        await client.restrict_chat_member(chat_id, uid, permissions=perm, until_date=until_ts)
                        name = message.from_user.first_name or str(uid)
                        await client.send_message(chat_id, get_msg("nsfw_muted", chat_id, name=name))
                        # DM owners
                        for o in OWNER_IDS:
                            try:
                                await client.send_message(o, f"🚨 User {name} ({uid}) muted in {chat_id} for rapid NSFW spam.")
                            except:
                                pass
                        # clear counters for that user
                        NSFW_TRACKERS.setdefault(str(chat_id), {}).pop(str(uid), None)
                except Exception as e:
                    print("Failed to mute user for NSFW spam:", e)
                    try:
                        await client.send_message(chat_id, "⚠️ Failed to mute the user automatically. Ensure I have restrict permissions.")
                    except:
                        pass
                return
            else:
                # reached N warns but not rapid - send warn and reset counter (per request: warn, not mute)
                try:
                    name = message.from_user.first_name or str(uid)
                    await client.send_message(chat_id, get_msg("nsfw_warn", chat_id, name=name, count=len(arr)))
                    # schedule deletion of warn
                    warn_msg = await client.send_message(chat_id, '')  # placeholder to get msg for deletion scheduling (we already sent above)
                except:
                    pass
                # reset counters after reached N (to avoid indefinite accumulation)
                NSFW_TRACKERS.setdefault(str(chat_id), {}).pop(str(uid), None)
                return

        # otherwise (less than threshold) -> warn with count
        try:
            name = message.from_user.first_name or str(uid)
            count = len(arr)
            warn = await client.send_message(chat_id, get_msg("nsfw_warn", chat_id, name=name, count=count))
            # schedule auto-delete of warning after WARNING_TTL
            asyncio.create_task(schedule_warning_delete(client, warn.chat.id, warn.message_id, WARNING_TTL))
        except Exception:
            pass

    except Exception as e:
        print("media_nsfw_handler error:", e)
        try:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass

async def schedule_warning_delete(client, chat_id, msg_id, delay):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, msg_id)
    except:
        pass

# ---------------------------
# Background keep-alive + Watchdog (unchanged)
# ---------------------------
async def background_keepalive():
    while True:
        try:
            if RENDER_HEALTH_URL:
                try:
                    async with aiohttp.ClientSession() as s:
                        await s.get(RENDER_HEALTH_URL, timeout=10)
                except:
                    pass
            await asyncio.sleep(280)
        except Exception:
            await asyncio.sleep(60)

async def watchdog_task(client):
    while True:
        try:
            await client.get_me()
        except Exception as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg = f"⚠️ ShieldX Crash Detected at {now}\nError: {e}"
            print(msg)
            for o in OWNER_IDS:
                try:
                    await client.send_message(o, msg)
                except:
                    pass
            os._exit(1)
        await asyncio.sleep(60)

def keep_alive_sync():
    url = RENDER_HEALTH_URL or RENDER_EXTERNAL_URL or None
    if not url:
        print("⚠️ No render keepalive URL provided in env (RENDER_HEALTH_URL or RENDER_EXTERNAL_URL). Skipping 5s pings.")
        return
    while True:
        try:
            requests.get(url, timeout=10)
        except Exception as e:
            print("⚠️ Render keepalive ping failed:", e)
        time.sleep(5)

# ---------------------------
# MAIN
# ---------------------------
async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    print("🩵 ShieldX starting...")
    try:
        await bot.start()
        me = await bot.get_me()
        print(f"🩵 ShieldX started (Pyrogram OK). Bot: @{me.username} ({me.id})")
    except Exception as e:
        print("❌ Failed to start Pyrogram client:", e)
        return
    asyncio.create_task(background_keepalive())
    asyncio.create_task(watchdog_task(bot))
    print("🩵 Background keepalive + watchdog running.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except Exception:
        print("⚠️ nest_asyncio not available or failed to apply — continuing.")
    try:
        threading.Thread(target=keep_alive_sync, daemon=True).start()
    except Exception as e:
        print("⚠️ Failed to start keep_alive_sync thread:", e)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown requested, exiting...")
