# -*- coding: utf-8 -*-
# ShieldX v4.5 — Stable moderation, NSFW toggle, batch clean, minimal reply noise
# NOTE: KEEP structure same as original. Only behavioral fixes and added toggles.
# Set secrets in .env: API_ID, API_HASH, BOT_TOKEN, OWNER_ID, HF_API_KEY (optional), SUPPORT_LINK, ADD_GROUP_LINK, RENDER_HEALTH_URL

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

# ---------------------------
# LOAD ENV
# ---------------------------
load_dotenv()
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID_RAW = os.getenv("OWNER_ID", "")  # comma-separated list
HF_API_KEY = os.getenv("HF_API_KEY", "")  # optional
RENDER_HEALTH_URL = os.getenv("RENDER_HEALTH_URL", "")
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/ShieldXSupport")
ADD_GROUP_LINK = os.getenv("ADD_GROUP_LINK", "https://t.me/ShieldXProtectorBot?startgroup=true")

# parse owners
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
# structure: {"_global":{...}, "<chat_id>": {"clean_on":bool, "delete_minutes":int, "lang":..., "nsfw_on":bool}}

def load_data() -> Dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(d: Dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
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
# MESSAGES / LOCALES (kept simple, add languages later)
# ---------------------------
MESSAGES = {
    "en-in": {
        "start_dm": "🛡️ ShieldX Protection\nI keep your groups clean 24/7. Use buttons below.",
        "start_group": "🛡️ ShieldX active in this group. I will help keep it clean.",
        "help_dm": "✨ ShieldX Commands\n\n• /clean [time] — enable auto-clean (admins)\n• /cleanoff — disable auto-clean (owner)\n• /cleanon — enable auto-clean (owner)\n• /cleanstatus — show status\n• /cleanall — delete media (owner/admin, last 24h)\n• /warnreset <user_id> — reset warns (owner/admin)\n• /nsfw_on /nsfw_off — toggle NSFW detection (admins)\n• /lang <code> — set language\n• /status — show current status\n\nDefault auto-clean: 30 minutes.",
        "help_group": "📩 I sent you commands in DM.",
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
        "nsfw_deleted": "⚠️ NSFW content detected and removed.",
        "nsfw_muted": "🚫 User {name} muted permanently for repeated NSFW spam.",
        "nsfw_unavailable": "⚠️ NSFW detection is OFF (no HF key). Enable HF API key to use model or toggle NSFW off.",
    },
    "hi": {
        "start_dm": "🛡️ ShieldX सुरक्षा\nमैं आपके ग्रुप्स को 24/7 साफ़ रखता हूँ। नीचे बटन देखें।",
        "start_group": "🛡️ ShieldX समूह में सक्रिय है।",
        "help_dm": "कमांड:\n/clean [time]\n/cleanoff\n/cleanon\n/cleanstatus\n/cleanall\n/warnreset <user_id>\n/nsfw_on /nsfw_off\n/lang <code>\n/status",
        "help_group": "📩 मैंने आपको कमांड DM में भेजी हैं।",
        "auto_on": "✅ Auto-clean चालू — हर {t} पर साफ़ करेगा।",
        "auto_off": "🛑 Auto-clean बंद किया गया।",
        "auto_set": "✅ Auto-clean सेट किया गया — अंतराल {t}.",
        "cleanall_start": "🧹 पिछले {t} की मीडिया हटाई जा रही है... कृपया प्रतीक्षा करें।",
        "cleanall_done": "✅ मीडिया हटाई पूरी हुई — हटाए गए आइटम: {n}.",
        "clean_done": "✅ मीडिया हटाई पूरी हुई — हटाए गए आइटम: {n}.",
        "only_admin": "⚠️ केवल group admins उपयोग कर सकते हैं।",
        "only_owner": "⚠️ केवल group owner या configured co-owners उपयोग कर सकते हैं।",
        "status_text": "🧹 Auto-clean: {on} | Interval: {t}",
        "ping_text": "🩵 ShieldX Online!\n⚡ {ms}ms | Uptime: {uptime}",
        "nsfw_deleted": "⚠️ NSFW सामग्री मिली और हटा दी गई।",
        "nsfw_muted": "🚫 उपयोगकर्ता {name} को बार-बार NSFW पोस्ट करने पर स्थायी म्यूट किया गया।",
        "nsfw_unavailable": "⚠️ NSFW पता लगाने की सेवा बंद है (HF key नहीं)।",
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
# Utilities
# ---------------------------
START_TIME = datetime.utcnow()

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
NSFW_WINDOW_SEC = 3
NSFW_SPAM_COUNT = 5
WARNING_TTL = 60
NSFW_TRACKERS: Dict[str, Dict[str, List[float]]] = {}

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
                    print("HF NSFW error:", resp.status, txt[:200])
                    return None
    except Exception as e:
        print("HF request exception:", e)
        return None

# ---------------------------
# Flask keep-alive
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
# COMMANDS
# ---------------------------
@bot.on_message(filters.command("start", prefixes=["/", "!"]) )
async def start_cmd(client, message):
    # send a single, clean start message. In groups, say group-start text and also send buttons visible in chat.
    try:
        me = await client.get_me()
    except:
        me = None

    buttons = [
        [types.InlineKeyboardButton("➕ Add Me To Group", url=ADD_GROUP_LINK), types.InlineKeyboardButton("🆘 Support", url=SUPPORT_LINK)],
    ]

    if message.chat and message.chat.type == "private":
        text = get_msg("start_dm", message.chat.id)
        await message.reply_text(text, reply_markup=types.InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        # group
        text = get_msg("start_group", message.chat.id)
        # include the same buttons so they are visible in group
        try:
            await message.reply(text, reply_markup=types.InlineKeyboardMarkup(buttons), quote=False)
        except ChatWriteForbidden:
            pass

@bot.on_message(filters.command("help", prefixes=["/", "!"]))
async def help_cmd(client, message):
    if message.chat and message.chat.type == "private":
        await message.reply_text(get_msg("help_dm", message.chat.id), disable_web_page_preview=True)
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
    m = await message.reply("🏓 ...")
    ms = int((time.time() - t0) * 1000)
    uptime = str(datetime.utcnow() - START_TIME).split(".")[0]
    await m.edit_text(get_msg("ping_text", message.chat.id, ms=ms, uptime=uptime))

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

# /nsfw_on and /nsfw_off (admins)
@bot.on_message(filters.command(["nsfw_on", "nsfw_off"], prefixes=["/", "!"]) & filters.group)
async def nsfw_toggle_cmd(client, message):
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
    except:
        member = None
    if not member or member.status not in ("administrator", "creator"):
        await message.reply(get_msg("only_admin", message.chat.id), quote=False)
        return
    cfg = ensure_chat(message.chat.id)
    cmd = message.text.split()[0].lower()
    if cmd.endswith("_on") or cmd == "/nsfw_on":
        cfg["nsfw_on"] = True
        save_data(DATA)
        await message.reply("✅ NSFW detection ENABLED for this chat.", quote=False)
    else:
        cfg["nsfw_on"] = False
        save_data(DATA)
        await message.reply("🛑 NSFW detection DISABLED for this chat.", quote=False)

# /clean command (admins) - concise reply and activate scheduled deletions
@bot.on_message(filters.command("clean", prefixes=["/", "!"]) & filters.group)
async def clean_cmd(client, message):
    # check global enabled
    if not is_clean_enabled_global():
        await message.reply("⚠️ Media clean system is currently disabled. Owner can enable with /cleanon.", quote=False)
        return

    # admin check
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
        mins = 30

    cfg = ensure_chat(message.chat.id)
    cfg["clean_on"] = True
    cfg["delete_minutes"] = mins
    save_data(DATA)

    human = fmt_timespan(mins)
    # concise confirmation
    await message.reply(f"🧹 Auto-clean service activated!\n🔹 Delete interval: every {mins} minutes", quote=False)

    # perform an immediate batch-delete of media older than mins
    asyncio.create_task(_run_batch_and_report(client, message.chat.id, mins))

async def _run_batch_and_report(client, chat_id, mins):
    human = fmt_timespan(mins)
    # run batch silently; on completion, send a short summary to chat
    deleted = await batch_delete_media_in_range(client, chat_id, mins)
    try:
        await client.send_message(chat_id, get_msg("clean_done", chat_id, n=deleted, t=human))
    except:
        pass

# /cleanall - owner/admin: delete last 24h media (batch-wise)
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
    await message.reply(get_msg("cleanall_start", message.chat.id, t=human), quote=False)
    deleted = await batch_delete_media_in_range(client, message.chat.id, 1440)
    await message.reply(get_msg("cleanall_done", message.chat.id, n=deleted, t=human), quote=False)

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
# Batch delete helper (safe, chunked)
# ---------------------------
async def batch_delete_media_in_range(client, chat_id: int, minutes: int) -> int:
    """
    Delete media-only messages in last `minutes` minutes in safe batches.
    Returns number deleted.
    """
    deleted = 0
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    try:
        # iterate history (newest first). We'll collect deletable message ids in batches and delete in small bursts.
        to_delete = []
        async for msg in client.get_chat_history(chat_id, limit=5000):
            if msg.date < cutoff:
                break
            if msg.media:
                to_delete.append(msg.message_id)
            # process in chunks to avoid flood
            if len(to_delete) >= 20:
                try:
                    await _bulk_delete_safe(client, chat_id, to_delete)
                    deleted += len(to_delete)
                except:
                    pass
                to_delete = []
                await asyncio.sleep(1)
        if to_delete:
            try:
                await _bulk_delete_safe(client, chat_id, to_delete)
                deleted += len(to_delete)
            except:
                pass
    except Exception as e:
        print("batch_delete_media_in_range error:", e)
    return deleted

async def _bulk_delete_safe(client, chat_id, message_ids: List[int]):
    # attempts to delete messages in small groups; ignore errors per-message if needed
    try:
        # Pyrogram allows deleting a list
        await client.delete_messages(chat_id, message_ids)
    except RPCError as e:
        # fallback — try per-message
        for mid in message_ids:
            try:
                await client.delete_messages(chat_id, mid)
                await asyncio.sleep(0.1)
            except Exception:
                await asyncio.sleep(0.05)
                continue

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

@bot.on_message(filters.group & (filters.photo | filters.video | filters.sticker | filters.animation | filters.document))
async def media_nsfw_handler(client, message):
    # ignore anonymous/service
    if message.from_user is None:
        return

    chat_id = message.chat.id
    uid = message.from_user.id
    cfg = ensure_chat(chat_id)

    # If NSFW detection is disabled for this chat, treat as normal media (just schedule auto-clean if set)
    if not cfg.get("nsfw_on", True):
        await _handle_normal_media(client, message, cfg)
        return

    # If HF key not provided, notify once and skip detection
    if not HF_API_KEY:
        # only post a one-time warning per chat to avoid spam
        key = f"_nsfw_warning_sent_{chat_id}"
        if not DATA.get(key):
            try:
                await client.send_message(chat_id, get_msg("nsfw_unavailable", chat_id))
            except:
                pass
            DATA[key] = True
            save_data(DATA)
        await _handle_normal_media(client, message, cfg)
        return

    tmpdir = None
    try:
        tmpdir = tempfile.mkdtemp()
        path = await client.download_media(message, file_name=os.path.join(tmpdir, "media"))
        if not path or not os.path.exists(path):
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
            return

        res = await call_hf_nsfw(path)

        is_nsfw = False
        try:
            if res:
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
        except Exception as e:
            print("NSFW parse error:", e, res)

        try:
            os.remove(path)
        except:
            pass
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)

        if not is_nsfw:
            await _handle_normal_media(client, message, cfg)
            return

        # NSFW detected: delete, warn, track
        try:
            await client.delete_messages(chat_id, message.message_id)
        except:
            pass

        try:
            warn = await client.send_message(chat_id, get_msg("nsfw_deleted", chat_id))
            asyncio.create_task(schedule_warning_delete(client, warn.chat.id, warn.message_id, WARNING_TTL))
        except Exception:
            warn = None

        arr = prune_nsfw_counters(str(chat_id), str(uid))
        arr.append(time.time())
        NSFW_TRACKERS[str(chat_id)][str(uid)] = arr

        # if spam threshold reached -> mute permanently
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
                until_ts = int(time.time()) + 10 * 365 * 24 * 3600
                await client.restrict_chat_member(chat_id, uid, permissions=perm, until_date=until_ts)
                name = message.from_user.first_name or str(uid)
                await client.send_message(chat_id, get_msg("nsfw_muted", chat_id, name=name), parse_mode="md")
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

async def _handle_normal_media(client, message, cfg):
    # schedule auto-delete if chat has clean_on enabled
    if cfg.get("clean_on") and is_clean_enabled_global():
        mins = cfg.get("delete_minutes", 30)
        delay = int(mins) * 60
        if delay == 0:
            try:
                await client.delete_messages(message.chat.id, message.message_id)
            except:
                pass
        else:
            asyncio.create_task(schedule_delete(client, message.chat.id, message.message_id, delay))

# ---------------------------
# Background tasks: keepalive + watchdog
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

# Synchronous 5-second keep-alive (optional external ping)
def keep_alive_sync():
    url = RENDER_HEALTH_URL or None
    if not url:
        print("⚠️ No render keepalive URL provided in env (RENDER_HEALTH_URL). Skipping 5s pings.")
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
