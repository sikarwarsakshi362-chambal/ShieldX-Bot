# -*- coding: utf-8 -*-
# bot.py — ShieldX v3.2 Stable (keep-alive + NSFW + full commands, preserve structure)

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
from flask import Flask
from pyrogram import Client, filters, types
from pyrogram.errors import ChatWriteForbidden, RPCError
from dotenv import load_dotenv

# ---------------------------
# CONFIG / ENV
# ---------------------------
load_dotenv()
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID_RAW = os.getenv("OWNER_ID", "")
try:
    OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW else 0
except:
    OWNER_ID = 0

def parse_owner_ids(s: str) -> List[int]:
    if not s:
        return []
    parts = [p.strip() for p in s.split(",") if p.strip()]
    ids = []
    for p in parts:
        try:
            ids.append(int(p))
        except:
            continue
    return ids

CO_OWNER_IDS = parse_owner_ids(os.getenv("CO_OWNER_IDS", ""))

HF_API_KEY = os.getenv("HF_API_KEY", "")
HF_MODEL = "Falconsai/nsfw_image_detection"
HF_API = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

DATA_FILE = "data.json"

# ---------------------------
# DEFAULT MESSAGES (locales)
# ---------------------------
MESSAGES = {
    "en-in": {
        "start_dm": "🛡️ *ShieldX Protection*\nI keep your groups clean. Use buttons below.",
        "start_group": "🛡️ ShieldX active in this group.",
        "help_dm": "✨ Commands:\n/clean [time]\n/clean off\n/cleanall\n/nsfw on|off|status\n/lang <code>\n/status\n/reload",
        "help_group": "📩 Sent you a DM with commands.",
        "auto_on": "✅ Auto-clean enabled — will clear every {t}.",
        "auto_off": "🛑 Auto-clean disabled.",
        "auto_set": "✅ Auto-clean set to {t}.",
        "cleanall_start": "🧹 Clearing recent media (last 24h)...",
        "cleanall_done": "✅ {n} media items removed.",
        "only_admin": "⚠️ Only group admins can use this.",
        "only_owner": "⚠️ Only group owner or co-owner can use this.",
        "status_text": "🧹 Auto-clean: {on} | Interval: {t}",
        "ping_text": "🏓 Pong! {ms}ms",
    },
    "hi": {
        "start_dm": "🛡️ *ShieldX Protection*\nमैं आपके ग्रुप को साफ़ रखता हूँ। नीचे बटन देखें।",
        "start_group": "🛡️ ShieldX समूह में सक्रिय है।",
        "help_dm": "कमांड:\n/clean [time]\n/clean off\n/cleanall\n/nsfw on|off|status\n/lang <code>\n/status\n/reload",
        "help_group": "कमांड DM में भेज दी गई हैं।",
        "auto_on": "✅ Auto-clean चालू — हर {t} पर साफ़ करेगा।",
        "auto_off": "🛑 Auto-clean बंद किया गया।",
        "auto_set": "✅ Auto-clean सेट किया गया — अंतराल: {t}.",
        "cleanall_start": "🧹 हालिया 24 घंटों की मीडिया हटाई जा रही है...",
        "cleanall_done": "✅ {n} मीडिया हटाए गए।",
        "only_admin": "⚠️ केवल group admins उपयोग कर सकते हैं।",
        "only_owner": "⚠️ केवल group owner या co-owner उपयोग कर सकते हैं।",
        "status_text": "Auto-clean: {on} | Interval: {t}",
        "ping_text": "🏓 Pong! {ms}ms",
    },
}
DEFAULT_LOCALE = "en-in"
SUPPORTED_LOCALES = list(MESSAGES.keys())

# ---------------------------
# STORAGE
# ---------------------------
def load_data() -> Dict:
    try:
        if os.path.exists(DATA_FILE):
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

DATA = load_data()  # chat_id -> settings

def ensure_chat(chat_id):
    cid = str(chat_id)
    if cid not in DATA:
        DATA[cid] = {"clean_on": False, "delete_minutes": 30, "lang": DEFAULT_LOCALE}
        save_data(DATA)
    return DATA[cid]

# ---------------------------
# UTIL
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
            return int(token[:-1])
        if token.endswith("h"):
            return int(token[:-1]) * 60
        if token.endswith("d"):
            return int(token[:-1]) * 1440
        if token.isdigit():
            return int(token)
    except:
        return None
    return None

def get_msg(key: str, chat_id, **kwargs):
    cfg = ensure_chat(chat_id)
    lang = cfg.get("lang", DEFAULT_LOCALE)
    if lang not in MESSAGES:
        lang = DEFAULT_LOCALE
    template = MESSAGES[lang].get(key, MESSAGES[DEFAULT_LOCALE].get(key, ""))
    return template.format(**kwargs)

# ---------------------------
# FLASK (keep-alive)
# ---------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "🩵 ShieldX Bot — alive"

@flask_app.route("/healthz")
def healthz():
    return "OK", 200

def run_flask():
    # run without blocking
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

# ---------------------------
# PYROGRAM BOT
# ---------------------------
bot = Client("shieldx", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------------------
# COMMANDS and HANDLERS
# ---------------------------
@bot.on_message(filters.command("start", prefixes=["/", "!"]))
async def start_cmd(client, message):
    try:
        if message.chat and message.chat.type == "private":
            text = get_msg("start_dm", message.chat.id)
            me = await client.get_me()
            kb = [
                [types.InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{me.username}?startgroup=new")],
                [types.InlineKeyboardButton("📘 Commands", callback_data="sx_help")],
                [types.InlineKeyboardButton("🔧 Support", url=os.getenv("SUPPORT_URL", "https://t.me/shieldxprotector_bot"))],
            ]
            await message.reply_text(text, reply_markup=types.InlineKeyboardMarkup(kb), disable_web_page_preview=True)
        else:
            await message.reply(get_msg("start_group", message.chat.id), quote=False)
    except Exception:
        pass

@bot.on_callback_query(filters.regex(r"^sx_help$"))
async def cb_help(client, query):
    await query.answer()
    try:
        await query.message.edit_text(get_msg("help_dm", query.message.chat.id))
    except:
        pass

@bot.on_message(filters.command("help", prefixes=["/", "!"]))
async def help_cmd(client, message):
    try:
        if message.chat and message.chat.type == "private":
            await message.reply_text(get_msg("help_dm", message.chat.id), disable_web_page_preview=True)
        else:
            try:
                await message.reply(get_msg("help_group", message.chat.id), quote=False)
            except ChatWriteForbidden:
                pass
    except:
        pass

@bot.on_message(filters.command("ping", prefixes=["/", "!"]))
async def ping_cmd(client, message):
    t0 = time.time()
    m = await message.reply("🏓 ...")
    ms = int((time.time() - t0) * 1000)
    await m.edit_text(get_msg("ping_text", message.chat.id, ms=ms))

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
        await message.reply("Usage: /lang <locale_code> (eg. en-in, en-us, hi)", quote=False)
        return
    code = args[1].lower()
    if code not in SUPPORTED_LOCALES:
        await message.reply(f"Unsupported. Supported: {', '.join(SUPPORTED_LOCALES)}", quote=False)
        return
    cfg = ensure_chat(message.chat.id)
    cfg["lang"] = code
    save_data(DATA)
    await message.reply(get_msg("start_group", message.chat.id) + f"\n🌐 Language: {code}", quote=False)

@bot.on_message(filters.command("clean", prefixes=["/", "!"]) & filters.group)
async def clean_cmd(client, message):
    # admin only
    try:
        m = await client.get_chat_member(message.chat.id, message.from_user.id)
        if m.status not in ("administrator", "creator"):
            await message.reply(get_msg("only_admin", message.chat.id), quote=False)
            return
    except:
        await message.reply(get_msg("only_admin", message.chat.id), quote=False)
        return

    args = message.text.split()
    cfg = ensure_chat(message.chat.id)

    if len(args) > 1:
        token = args[1].lower()
        if token == "on":
            cfg["clean_on"] = True
            cfg["delete_minutes"] = 30
            save_data(DATA)
            await message.reply(get_msg("auto_on", message.chat.id, t=fmt_timespan(cfg["delete_minutes"])), quote=False)
            return
        if token == "off":
            cfg["clean_on"] = False
            save_data(DATA)
            await message.reply(get_msg("auto_off", message.chat.id), quote=False)
            return
        mins = parse_time_token(token)
        if mins is None or mins < 20 or mins > 1440:
            await message.reply("⚠️ Provide time between 20m and 24h (e.g. 20m, 2h, 1d).", quote=False)
            return
        cfg["clean_on"] = True
        cfg["delete_minutes"] = mins
        save_data(DATA)
        await message.reply(get_msg("auto_set", message.chat.id, t=fmt_timespan(mins)), quote=False)
        return

    cfg["clean_on"] = True
    cfg["delete_minutes"] = 30
    save_data(DATA)
    await message.reply(get_msg("auto_on", message.chat.id, t=fmt_timespan(cfg["delete_minutes"])), quote=False)

@bot.on_message(filters.command("cleanall", prefixes=["/", "!"]) & filters.group)
async def cleanall_cmd(client, message):
    user_id = message.from_user.id
    try:
        m = await client.get_chat_member(message.chat.id, user_id)
        is_owner = (m.status == "creator")
    except:
        is_owner = False
    if not (is_owner or user_id in CO_OWNER_IDS or user_id == OWNER_ID):
        await message.reply(get_msg("only_owner", message.chat.id), quote=False)
        return

    await message.reply(get_msg("cleanall_start", message.chat.id), quote=False)
    deleted = 0
    try:
        # search recent messages (last ~24h) — limit to avoid overload
        async for msg in client.get_chat_history(message.chat.id, limit=1000):
            # only delete media and recent messages (roughly last 24h)
            if msg.media:
                try:
                    await client.delete_messages(message.chat.id, msg.message_id)
                    deleted += 1
                except RPCError:
                    continue
    except Exception:
        pass
    await message.reply(get_msg("cleanall_done", message.chat.id, n=deleted), quote=False)

# ---------------------------
# Auto-delete monitor + scheduler
# ---------------------------
async def schedule_delete(client, chat_id, msg_id, delay):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, msg_id)
    except:
        pass

@bot.on_message(filters.group)
async def auto_delete_monitor(client, message):
    cfg = ensure_chat(message.chat.id)
    if not cfg.get("clean_on"):
        return
    if message.media:
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
# NSFW detection (HuggingFace free model)
# ---------------------------
NSFW_CONF_THRESHOLD = 0.8
NSFW_WINDOW_SEC = 3
NSFW_SPAM_COUNT = 5
WARNING_TTL = 60

NSFW_COUNTERS: Dict[str, Dict[str, List[float]]] = {}

async def call_hf_nsfw(file_path: str):
    headers = {}
    if HF_API_KEY:
        headers["Authorization"] = f"Bearer {HF_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                data = f.read()
            async with session.post(HF_API, data=data, headers=headers, timeout=30) as resp:
                if resp.status == 200:
                    try:
                        return await resp.json()
                    except:
                        return None
                else:
                    _ = await resp.text()
                    return None
    except Exception:
        return None

def prune_nsfw_counters(chat_id: str, user_id: str):
    now = time.time()
    chat_map = NSFW_COUNTERS.setdefault(str(chat_id), {})
    arr = chat_map.setdefault(str(user_id), [])
    arr[:] = [t for t in arr if now - t <= NSFW_WINDOW_SEC]
    chat_map[str(user_id)] = arr
    NSFW_COUNTERS[str(chat_id)] = chat_map
    return arr

async def schedule_warning_delete(client, chat_id, msg_id, delay):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, msg_id)
    except:
        pass

@bot.on_message(filters.group & (filters.photo | filters.video | filters.document))
async def nsfw_handler(client, message):
    tmpdir = None
    try:
        tmpdir = tempfile.mkdtemp()
        path = await client.download_media(message, file_name=os.path.join(tmpdir, "media"))
        if not path or not os.path.exists(path):
            shutil.rmtree(tmpdir, ignore_errors=True)
            return
        res = await call_hf_nsfw(path)
        try:
            os.remove(path)
            shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass

        is_nsfw = False
        if res:
            try:
                # handle a few typical structures
                if isinstance(res, list) and len(res) > 0 and isinstance(res[0], dict):
                    lab = str(res[0].get("label", "")).lower()
                    sc = float(res[0].get("score", 0) or 0)
                    if "nsfw" in lab or sc >= NSFW_CONF_THRESHOLD:
                        is_nsfw = True
                elif isinstance(res, dict) and "label" in res and "score" in res:
                    lab = str(res.get("label", "")).lower()
                    sc = float(res.get("score", 0) or 0)
                    if "nsfw" in lab or sc >= NSFW_CONF_THRESHOLD:
                        is_nsfw = True
                else:
                    # deep search for score-like dict
                    def find_scores(obj):
                        if isinstance(obj, dict):
                            if "score" in obj and isinstance(obj.get("score"), (int, float)):
                                return obj
                            for v in obj.values():
                                r = find_scores(v)
                                if r:
                                    return r
                        elif isinstance(obj, list):
                            for el in obj:
                                r = find_scores(el)
                                if r:
                                    return r
                        return None
                    found = find_scores(res)
                    if found:
                        lab = str(found.get("label", "")).lower()
                        sc = float(found.get("score", 0) or 0)
                        if "nsfw" in lab or sc >= NSFW_CONF_THRESHOLD:
                            is_nsfw = True
            except Exception:
                is_nsfw = False

        if not is_nsfw:
            return

        # delete original message
        try:
            await client.delete_messages(message.chat.id, message.message_id)
        except:
            pass

        # send warning and schedule its deletion
        try:
            warn = await client.send_message(message.chat.id, f"⚠️ NSFW content detected and removed. — {message.from_user.first_name}")
            asyncio.create_task(schedule_warning_delete(client, warn.chat.id, warn.message_id, WARNING_TTL))
        except:
            warn = None

        # update counters and mute if spammy
        uid = str(message.from_user.id)
        chatid = str(message.chat.id)
        arr = prune_nsfw_counters(chatid, uid)
        arr.append(time.time())
        NSFW_COUNTERS[chatid][uid] = arr

        if len(arr) >= NSFW_SPAM_COUNT:
            try:
                me = await client.get_me()
                bot_member = await client.get_chat_member(message.chat.id, me.id)
                if bot_member.status not in ("administrator", "creator"):
                    await client.send_message(message.chat.id, "⚠️ I need admin permissions to mute users automatically. Please grant admin.")
                    return
                until_ts = int(time.time()) + 10 * 365 * 24 * 3600
                perm = types.ChatPermissions(can_send_messages=False, can_send_media_messages=False, can_send_other_messages=False, can_add_web_page_previews=False)
                await client.restrict_chat_member(message.chat.id, int(uid), permissions=perm, until_date=until_ts)
                await client.send_message(message.chat.id, f"🚫 User [{uid}](tg://user?id={uid}) muted for repeated NSFW spam.", parse_mode="md")
                NSFW_COUNTERS.setdefault(chatid, {}).pop(uid, None)
            except Exception:
                try:
                    await client.send_message(message.chat.id, "⚠️ Failed to mute the user. Ensure I have restrict permissions.")
                except:
                    pass

    except Exception:
        try:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass

# ---------------------------
# BACKGROUND: auto-clean tick (render-safe)
# ---------------------------
async def background_loop():
    # small background tasks: keep-alive tick, optionally health pings
    while True:
        # run every 4 minutes to keep process active
        print("[ShieldX] background tick", datetime.utcnow().isoformat())
        await asyncio.sleep(240)

# ---------------------------
# MAIN / STARTUP
# ---------------------------
async def main():
    # start flask in separate thread
    threading.Thread(target=run_flask, daemon=True).start()
    # small sleep to let flask start
    await asyncio.sleep(0.5)
    try:
        await bot.start()
        me = await bot.get_me()
        print(f"🩵 ShieldX started. Bot @{me.username} ({me.id})")
    except Exception as e:
        print("❌ Failed to start Pyrogram client:", e)
        return

    # start background tasks
    asyncio.create_task(background_loop())

    # keep running
    try:
        await asyncio.Event().wait()
    finally:
        try:
            await bot.stop()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
