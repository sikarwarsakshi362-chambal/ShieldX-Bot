# -*- coding: utf-8 -*-
# ShieldX v4.5 — Moderation edition (preserves original structure, adds stable NSFW + batch clean + locales)
# NOTE: Do NOT hardcode secrets here — set API_ID, API_HASH, BOT_TOKEN, OWNER_ID, HF_API_KEY, RENDER_* in your .env

import asyncio
import json
import os
import threading
import time
import tempfile
import shutil
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import aiohttp
import requests
from flask import Flask
from pyrogram import Client, filters, types
from pyrogram.errors import RPCError, ChatWriteForbidden
from dotenv import load_dotenv

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
# also allow common alternate env names for external url
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "") or os.getenv("RENDER_URL", "") or os.getenv("PRIMARY_URL", "")

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

OWNER_IDS = parse_owner_ids(OWNER_ID_RAW)  # list of ints; first one considered primary owner if needed

# ---------------------------
# STORAGE (persistent)
# ---------------------------
DATA_FILE = "data.json"
# Format:
# {
#   "_global": {"clean_enabled": true},
#   "<chat_id>": {"clean_on": bool, "delete_minutes": int, "lang": "en-in", "nsfw_on": bool}
# }

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
        DATA[cid] = {"clean_on": False, "delete_minutes": 30, "lang": "en-in", "nsfw_on": True}
        save_data(DATA)
    return DATA[cid]

def is_clean_enabled_global():
    return DATA.get("_global", {}).get("clean_enabled", True)

def set_clean_enabled_global(val: bool):
    DATA.setdefault("_global", {})["clean_enabled"] = bool(val)
    save_data(DATA)

# ---------------------------
# MESSAGES / LOCALES
# Add many locale keys (fallback to English if no custom translation provided)
# ---------------------------
BASE_MESSAGES = {
    "start_dm": "🛡️ *ShieldX Protection*\nI keep your groups clean. Use buttons below.",
    "start_group": "🛡️ ShieldX active in this group.",
    "help_dm": "✨ *ShieldX Commands*\n\n• /clean [time] — enable auto-clean (admins)\n• /cleanoff — disable auto-clean (owner)\n• /cleanon — enable auto-clean (owner)\n• /cleanstatus — show status\n• /cleanall — delete media (owner/co-owner only, last 24h)\n• /warnreset <user_id> — reset warns (owner/admin)\n• /lang <code> — set language\n• /nsfw <on|off> — toggle NSFW detection (admins)\n• /status — show current status\n\nDefault auto-clean: 30 minutes.",
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
    "ping_text": "🩵 ShieldX Online!\n⚡ {ms}ms | Uptime: {uptime}",
    "nsfw_deleted": "⚠️ NSFW content detected and removed. Follow group rules.",
    "nsfw_muted": "🚫 User {name} muted permanently for repeated NSFW spam.",
    "nsfw_on": "🚫 NSFW detection ENABLED for this chat.",
    "nsfw_off": "✅ NSFW detection DISABLED for this chat.",
}

# Add multiple locale codes (for now they fallback to BASE_MESSAGES)
LOCALES = [
    "en-in","en","hi","bn","mr","pa","gu","or","ta","te","kn","ml","as","ks","ne","sd","ur","si","kok","mai","bh"
]
MESSAGES = {}
for code in LOCALES:
    MESSAGES[code] = BASE_MESSAGES.copy()

DEFAULT_LOCALE = "en-in"

def get_msg(key: str, chat_id, **kwargs):
    cfg = ensure_chat(chat_id)
    lang = cfg.get("lang", DEFAULT_LOCALE)
    template = MESSAGES.get(lang, MESSAGES.get(DEFAULT_LOCALE)).get(key, "")
    # uptime support
    if key == "ping_text":
        # ensure uptime passed
        kwargs.setdefault("uptime", "0:00:00")
    return template.format(**kwargs)

# ---------------------------
# APP INIT
# ---------------------------
app = Flask(__name__)
bot = Client("ShieldXBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# track start time for uptime
START_TIME = datetime.now(timezone.utc)

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

def format_uptime() -> str:
    delta = datetime.now(timezone.utc) - START_TIME
    # format H:MM:SS
    total = int(delta.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h}:{m:02d}:{s:02d}"

# ---------------------------
# NSFW (HuggingFace free model) settings
# ---------------------------
HF_MODEL = "Falconsai/nsfw_image_detection"
HF_API = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}

NSFW_CONF_THRESHOLD = 0.8
NSFW_WINDOW_SEC = 3
NSFW_SPAM_COUNT = 5
WARNING_TTL = 60  # seconds to auto-delete normal warning

# track per-chat per-user nsfw timestamps
NSFW_TRACKERS: Dict[str, Dict[str, List[float]]] = {}

# ---------------------------
# Helper: call HF NSFW model async
# ---------------------------
async def call_hf_nsfw(file_path: str):
    # If HF headers empty, HF may still accept anonymous inference but often rate-limited.
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
    # Note: Flask dev server is fine for Render keepalive purpose
    app.run(host="0.0.0.0", port=port)

# ---------------------------
# COMMANDS
# ---------------------------

# /start
@bot.on_message(filters.command("start", prefixes=["/", "!"]))
async def start_cmd(client, message):
    # Single clear response; if private -> show buttons; if group -> simple group active text.
    cfg = ensure_chat(message.chat.id if message.chat else message.from_user.id)
    if message.chat and message.chat.type == "private":
        text = get_msg("start_dm", message.chat.id)
        me = await client.get_me()
        buttons = [
            [types.InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{me.username}?startgroup=new")],
            [types.InlineKeyboardButton("💬 Support", url=f"https://t.me/{me.username}?start=help")],
        ]
        await message.reply_text(text, reply_markup=types.InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        await message.reply(get_msg("start_group", message.chat.id), quote=False)

# /help
@bot.on_message(filters.command("help", prefixes=["/", "!"]))
async def help_cmd(client, message):
    if message.chat and message.chat.type == "private":
        await message.reply_text(get_msg("help_dm", message.chat.id), disable_web_page_preview=True)
    else:
        # group: notify that DM has been sent (single reply)
        try:
            await message.reply(get_msg("help_group", message.chat.id), quote=False)
        except ChatWriteForbidden:
            pass
        # also attempt to DM the user (best-effort)
        try:
            await client.send_message(message.from_user.id, get_msg("help_dm", message.from_user.id), disable_web_page_preview=True)
        except:
            pass

# callback for help button
@bot.on_callback_query(filters.regex(r"^sx_help$"))
async def cb_help(client, query):
    await query.answer()
    try:
        await query.message.edit_text(get_msg("help_dm", query.message.chat.id))
    except:
        pass

# /ping
@bot.on_message(filters.command("ping", prefixes=["/", "!"]))
async def ping_cmd(client, message):
    t0 = time.time()
    m = await message.reply("🏓 ...")
    ms = int((time.time() - t0) * 1000)
    uptime = format_uptime()
    await m.edit_text(get_msg("ping_text", message.chat.id, ms=ms, uptime=uptime))

# /status (group)
@bot.on_message(filters.command("status", prefixes=["/", "!"]) & filters.group)
async def status_cmd(client, message):
    cfg = ensure_chat(message.chat.id)
    on = "On" if cfg.get("clean_on") else "Off"
    t = fmt_timespan(cfg.get("delete_minutes", 30))
    nsfw_on = cfg.get("nsfw_on", True)
    await message.reply(get_msg("status_text", message.chat.id, on=on, t=t) + f"\nNSFW: {'ON' if nsfw_on else 'OFF'}", quote=False)

# /lang (group)
@bot.on_message(filters.command("lang", prefixes=["/", "!"]) & (filters.group | filters.private))
async def lang_cmd(client, message):
    args = message.text.split()
    if len(args) < 2:
        # show current and supported codes
        cfg = ensure_chat(message.chat.id if message.chat else message.from_user.id)
        code = cfg.get("lang", DEFAULT_LOCALE)
        await message.reply(f"Current language: {code}\nSupported: {', '.join(LOCALES)}", quote=False)
        return
    code = args[1].lower()
    if code not in MESSAGES:
        await message.reply(f"Unsupported. Supported: {', '.join(MESSAGES.keys())}", quote=False)
        return
    cfg = ensure_chat(message.chat.id if message.chat else message.from_user.id)
    cfg["lang"] = code
    save_data(DATA)
    await message.reply(get_msg("start_group", message.chat.id if message.chat else message.from_user.id) + f"\n🌐 Language: {code}", quote=False)

# /cleanstatus (anyone)
@bot.on_message(filters.command("cleanstatus", prefixes=["/", "!"]) & filters.group)
async def cleanstatus_cmd(client, message):
    cfg = ensure_chat(message.chat.id)
    global_state = is_clean_enabled_global()
    chat_on = cfg.get("clean_on", False)
    await message.reply(f"Global clean: {'ON' if global_state else 'OFF'}\nChat auto-clean: {'ON' if chat_on else 'OFF'}\nInterval: {fmt_timespan(cfg.get('delete_minutes',30))}", quote=False)

# /cleanon (owner only)
@bot.on_message(filters.command("cleanon", prefixes=["/", "!"]))
async def cleanon_cmd(client, message):
    user_id = message.from_user.id
    if user_id not in OWNER_IDS:
        await message.reply("❌ Only owner can enable cleaning globally.", quote=False)
        return
    set_clean_enabled_global(True)
    await message.reply("✅ Global cleaning ENABLED.", quote=False)

# /cleanoff (owner only)
@bot.on_message(filters.command("cleanoff", prefixes=["/", "!"]))
async def cleanoff_cmd(client, message):
    user_id = message.from_user.id
    if user_id not in OWNER_IDS:
        await message.reply("❌ Only owner can disable cleaning globally.", quote=False)
        return
    set_clean_enabled_global(False)
    await message.reply("🛑 Global cleaning DISABLED.", quote=False)

# /nsfw (admins) -> toggle per chat
@bot.on_message(filters.command("nsfw", prefixes=["/", "!"]) & filters.group)
async def nsfw_cmd(client, message):
    args = message.text.split()
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ("administrator", "creator"):
            await message.reply(get_msg("only_admin", message.chat.id), quote=False)
            return
    except:
        await message.reply(get_msg("only_admin", message.chat.id), quote=False)
        return
    if len(args) < 2:
        cfg = ensure_chat(message.chat.id)
        await message.reply(f"NSFW is {'ON' if cfg.get('nsfw_on', True) else 'OFF'}. Use /nsfw on or /nsfw off.", quote=False)
        return
    cmd = args[1].lower()
    cfg = ensure_chat(message.chat.id)
    if cmd in ("on","true","1"):
        cfg["nsfw_on"] = True
        save_data(DATA)
        await message.reply(get_msg("nsfw_on", message.chat.id), quote=False)
    elif cmd in ("off","false","0"):
        cfg["nsfw_on"] = False
        save_data(DATA)
        await message.reply(get_msg("nsfw_off", message.chat.id), quote=False)
    else:
        await message.reply("Usage: /nsfw on|off", quote=False)

# /clean [time] - admins can run in group
@bot.on_message(filters.command("clean", prefixes=["/", "!"]) & filters.group)
async def clean_cmd(client, message):
    # check global enabled
    if not is_clean_enabled_global():
        await message.reply("⚠️ Media clean system is currently disabled. Owner can enable with /cleanon.", quote=False)
        return

    # check admin
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ("administrator", "creator"):
            await message.reply(get_msg("only_admin", message.chat.id), quote=False)
            return
    except:
        await message.reply(get_msg("only_admin", message.chat.id), quote=False)
        return

    args = message.text.split()
    if len(args) > 1:
        tkn = args[1].lower()
        mins = parse_time_token(tkn)
        if mins is None or mins < 20 or mins > 1440:
            await message.reply("⚠️ Provide time between 20m and 24h (e.g. 20m, 2h, 1d).", quote=False)
            return
    else:
        mins = 30  # default

    # set per-chat config and save
    cfg = ensure_chat(message.chat.id)
    cfg["clean_on"] = True
    cfg["delete_minutes"] = mins
    save_data(DATA)

    # reply and run batch clean for that time
    human = fmt_timespan(mins)
    start_msg = await message.reply(f"🧹 Clean mode enabled — will delete media older than {human}. Running initial batch now...", quote=False)
    deleted = await batch_delete_media_in_range(client, message.chat.id, mins)
    await start_msg.edit_text(get_msg("clean_done", message.chat.id, n=deleted, t=human), quote=False)

# /cleanoff (per-chat) - admins can run in group (same name as global earlier; keep both: if owner uses without group context global, above handled)
@bot.on_message(filters.command("cleanoff", prefixes=["/", "!"]) & filters.group)
async def cleanoff_chat_cmd(client, message):
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ("administrator", "creator"):
            await message.reply(get_msg("only_admin", message.chat.id), quote=False)
            return
    except:
        await message.reply(get_msg("only_admin", message.chat.id), quote=False)
        return
    cfg = ensure_chat(message.chat.id)
    cfg["clean_on"] = False
    save_data(DATA)
    await message.reply(get_msg("auto_off", message.chat.id), quote=False)

# /cleanall - only owner or co-owner(s)
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

    human = fmt_timespan(1440)
    start_msg = await message.reply(get_msg("cleanall_start", message.chat.id, t=human), quote=False)
    deleted = await batch_delete_media_in_range(client, message.chat.id, 1440)
    await start_msg.edit_text(get_msg("cleanall_done", message.chat.id, n=deleted, t=human), quote=False)

# /warnreset <user_id> - admin only
@bot.on_message(filters.command("warnreset", prefixes=["/", "!"]))
async def warnreset_cmd(client, message):
    # admin check
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

    # remove from nsfw counters
    for chat_map in NSFW_TRACKERS.values():
        chat_map.pop(uid, None)
    await message.reply("✅ Warn counters reset for user.", quote=False)

# ---------------------------
# Batch delete helper (chunked safe deletes)
# ---------------------------
async def batch_delete_media_in_range(client, chat_id: int, minutes: int) -> int:
    """
    Delete media-only messages in last `minutes` minutes in safe batches.
    Returns number deleted.
    """
    deleted = 0
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    # We'll fetch messages in pages; Pyrogram returns newest first
    # Delete in chunks to reduce floodwait risk.
    try:
        batch = []
        async for msg in client.get_chat_history(chat_id, limit=5000):
            msg_date = msg.date
            # ensure timezone-aware comparison (pyrogram returns tz-aware)
            if isinstance(msg_date, datetime):
                if msg_date.tzinfo is None:
                    # assume UTC
                    msg_date = msg_date.replace(tzinfo=timezone.utc)
            if msg_date < cutoff:
                break
            if msg.media:
                batch.append(msg.message_id)
                # when batch large enough, delete in one call
                if len(batch) >= 30:
                    try:
                        # delete in chunk (Pyrogram supports list)
                        await client.delete_messages(chat_id, batch)
                        deleted += len(batch)
                    except RPCError as e:
                        # fall back to individual deletes
                        for mid in batch:
                            try:
                                await client.delete_messages(chat_id, mid)
                                deleted += 1
                            except:
                                pass
                    batch = []
                    await asyncio.sleep(1)  # short sleep to reduce flood risk
        # final batch
        if batch:
            try:
                await client.delete_messages(chat_id, batch)
                deleted += len(batch)
            except RPCError:
                for mid in batch:
                    try:
                        await client.delete_messages(chat_id, mid)
                        deleted += 1
                    except:
                        pass
    except Exception as e:
        print("batch_delete_media_in_range error:", e)
    return deleted

# ---------------------------
# Auto-delete monitor + NSFW handler
# ---------------------------
async def schedule_delete(client, chat_id, msg_id, delay):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, msg_id)
    except:
        pass

def prune_nsfw_counters(chat_id: str, user_id: str):
    now = time.time()
    chat_map = NSFW_TRACKERS.setdefault(str(chat_id), {})
    arr = chat_map.setdefault(str(user_id), [])
    arr[:] = [t for t in arr if now - t <= NSFW_WINDOW_SEC]
    chat_map[str(user_id)] = arr
    NSFW_TRACKERS[str(chat_id)] = chat_map
    return arr

# main media & NSFW handler (group)
@bot.on_message(filters.group & (filters.photo | filters.video | filters.sticker | filters.animation | filters.document))
async def media_nsfw_handler(client, message):
    # ignore service messages or anonymous
    if message.from_user is None:
        return

    chat_id = message.chat.id
    uid = message.from_user.id
    cfg = ensure_chat(chat_id)

    # If chat has NSFW disabled, treat message normally (only auto-clean check)
    nsfw_enabled = cfg.get("nsfw_on", True)

    tmpdir = None
    try:
        # download to temp
        tmpdir = tempfile.mkdtemp()
        path = await client.download_media(message, file_name=os.path.join(tmpdir, "media"))
        if not path or not os.path.exists(path):
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
            return

        is_nsfw = False
        if nsfw_enabled:
            res = await call_hf_nsfw(path)
            # parse result robustly
            try:
                if res:
                    # common case: list of dicts
                    if isinstance(res, list) and len(res) > 0 and isinstance(res[0], dict):
                        item = res[0]
                        label = str(item.get("label", "")).lower()
                        score = float(item.get("score", 0) or 0)
                        if "nsfw" in label or score >= NSFW_CONF_THRESHOLD:
                            is_nsfw = True
                    elif isinstance(res, dict):
                        if "label" in res and "score" in res:
                            lab = str(res.get("label", "")).lower()
                            sc = float(res.get("score", 0) or 0)
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
                                lab = str(f.get("label", "")).lower()
                                sc = float(f.get("score", 0) or 0)
                                if "nsfw" in lab or sc >= NSFW_CONF_THRESHOLD:
                                    is_nsfw = True
            except Exception as e:
                print("NSFW parse error:", e, res)

        # remove temp file ASAP
        try:
            os.remove(path)
        except:
            pass
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)

        # If NSFW detected -> delete message, send warning (auto-delete after WARNING_TTL)
        if is_nsfw:
            try:
                await client.delete_messages(chat_id, message.message_id)
            except:
                pass

            # send temporary warning (single)
            try:
                warn = await client.send_message(chat_id, get_msg("nsfw_deleted", chat_id), reply_to_message_id=None)
                # schedule auto-delete of warning after WARNING_TTL
                asyncio.create_task(schedule_warning_delete(client, warn.chat.id, warn.message_id, WARNING_TTL))
            except Exception:
                warn = None

            # update nsfw tracker for spam detection
            arr = prune_nsfw_counters(str(chat_id), str(uid))
            arr.append(time.time())
            NSFW_TRACKERS[str(chat_id)][str(uid)] = arr

            # if spam threshold reached -> mute (only on spam)
            if len(arr) >= NSFW_SPAM_COUNT:
                try:
                    me = await client.get_me()
                    bot_member = await client.get_chat_member(chat_id, me.id)
                    if bot_member.status not in ("administrator", "creator"):
                        await client.send_message(chat_id, "⚠️ I need admin permissions to mute users automatically. Please grant admin and retry.")
                        return
                    perm = types.ChatPermissions(
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                    )
                    until_ts = int(time.time()) + 10 * 365 * 24 * 3600  # ~10 years
                    await client.restrict_chat_member(chat_id, uid, permissions=perm, until_date=until_ts)
                    name = message.from_user.first_name or str(uid)
                    await client.send_message(chat_id, get_msg("nsfw_muted", chat_id, name=name), parse_mode="md")
                    # DM owner
                    for o in OWNER_IDS:
                        try:
                            await client.send_message(o, f"🚨 User {name} ({uid}) muted in {chat_id} for NSFW spam.")
                        except:
                            pass
                    NSFW_TRACKERS.setdefault(str(chat_id), {}).pop(str(uid), None)
                except Exception as e:
                    print("Failed to mute user for NSFW spam:", e)
                    try:
                        await client.send_message(chat_id, "⚠️ Failed to mute the user automatically. Ensure I have restrict permissions.")
                    except:
                        pass
            return

        # If not NSFW, then treat by normal auto-clean logic (if chat has clean_on)
        cfg = ensure_chat(chat_id)
        if cfg.get("clean_on") and is_clean_enabled_global():
            mins = cfg.get("delete_minutes", 30)
            delay = int(mins) * 60
            if delay == 0:
                try:
                    await client.delete_messages(chat_id, message.message_id)
                except:
                    pass
            else:
                # schedule deletion
                asyncio.create_task(schedule_delete(client, chat_id, message.message_id, delay))
        # done

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
# Background keep-alive + Watchdog
# ---------------------------
async def background_keepalive():
    while True:
        try:
            # optional ping to render health url if provided
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

# ---------------------------
# Synchronous 5-second keep-alive (to prevent Render free-sleep)
# ---------------------------
def keep_alive_sync():
    # choose URL priority: RENDER_HEALTH_URL > RENDER_EXTERNAL_URL > RENDER_URL/PRIMARY_URL
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
    # start flask (keep-alive) in daemon thread
    threading.Thread(target=run_flask, daemon=True).start()
    print("🩵 ShieldX starting...")

    try:
        await bot.start()
        me = await bot.get_me()
        print(f"🩵 ShieldX started (Pyrogram OK). Bot: @{me.username} ({me.id})")
    except Exception as e:
        print("❌ Failed to start Pyrogram client:", e)
        return

    # start background tasks
    asyncio.create_task(background_keepalive())
    asyncio.create_task(watchdog_task(bot))
    print("🩵 Background keepalive + watchdog running.")

    # keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    # apply nest_asyncio if available to avoid "event loop already running" in some environments
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except Exception:
        print("⚠️ nest_asyncio not available or failed to apply — continuing.")

    # start the 5-second synchronous keep-alive in a daemon thread (won't block shutdown)
    try:
        threading.Thread(target=keep_alive_sync, daemon=True).start()
    except Exception as e:
        print("⚠️ Failed to start keep_alive_sync thread:", e)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown requested, exiting...")
