# bot.py (ShieldX v3.0) — env-aware (OWNER_ID / RENDER vars auto-read)
import asyncio
import json
import os
import threading
import time
from typing import Dict, List

from flask import Flask
from pyrogram import Client, filters, types
from pyrogram.errors import RPCError, ChatWriteForbidden
from dotenv import load_dotenv

# ---------------------------
# CONFIG / ENV
# ---------------------------
load_dotenv()
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# OWNER / CO-OWNER support: allow comma-separated list in env
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

OWNER_ID_RAW = os.getenv("OWNER_ID", "")  # can be "12345" or "123,456,789"
CO_OWNER_IDS = parse_owner_ids(OWNER_ID_RAW) or []  # list of ints

# RENDER vars (not used by bot directly but kept for convenience)
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "")
RENDER_HEALTH_URL = os.getenv("RENDER_HEALTH_URL", "")

DATA_FILE = "data.json"  # persistent per-chat settings

# ---------------------------
# DEFAULT MESSAGES (multi-locale small map)
# ---------------------------
MESSAGES = {
    "en-in": {
        "start_dm": "🛡️ *ShieldX Protection*\nI keep your groups clean. Use buttons below.",
        "start_group": "🛡️ ShieldX active in this group.",
        "help_dm": "✨ *ShieldX Commands*\n\n• /clean [time] — enable auto-clean (admins)\n• /clean off — disable auto-clean\n• /cleanall — delete all media (group owner / co-owners)\n• /lang <code> — set language\n• /status — show current status\n\nDefault auto-clean: 60 minutes.",
        "help_group": "📩 Sent you a DM with commands.",
        "auto_on": "✅ Auto-clean enabled — media will be cleared every {t}.",
        "auto_off": "🛑 Auto-clean disabled.",
        "auto_set": "✅ Auto-clean enabled — interval set to {t}.",
        "cleanall_start": "🧹 Clearing media...",
        "cleanall_done": "✅ {n} media items removed.",
        "only_admin": "⚠️ Only group admins can use this.",
        "only_owner": "⚠️ Only group owner or co-owner can use this.",
        "status_text": "🧹 Auto-clean: {on} | Interval: {t}",
        "ping_text": "🏓 Pong! {ms}ms",
    },
    "en-us": {
        "start_dm": "🛡️ ShieldX — auto-clean assistant. Use buttons below.",
        "start_group": "🛡️ ShieldX active.",
        "help_dm": "Commands:\n/clean [time]\n/clean off\n/cleanall\n/lang <code>\n/status",
        "help_group": "Check your DM for commands.",
        "auto_on": "✅ Auto-clean enabled — will clear every {t}.",
        "auto_off": "🛑 Auto-clean disabled.",
        "auto_set": "✅ Auto-clean set to {t}.",
        "cleanall_start": "🧹 Cleaning media...",
        "cleanall_done": "✅ Removed {n} media files.",
        "only_admin": "⚠️ Only group admins allowed.",
        "only_owner": "⚠️ Only group owner or co-owner allowed.",
        "status_text": "Auto-clean: {on} | Interval: {t}",
        "ping_text": "🏓 Pong! {ms}ms",
    },
    "hi": {
        "start_dm": "🛡️ ShieldX — आपका auto-clean सहायक। नीचे बटन्स देखें।",
        "start_group": "🛡️ ShieldX समूह में सक्रिय है।",
        "help_dm": "कमांड:\n/clean [time]\n/clean off\n/cleanall\n/lang <code>\n/status",
        "help_group": "कमांड DM में भेज दी गई हैं।",
        "auto_on": "✅ Auto-clean चालू — हर {t} पर साफ़ करेगा।",
        "auto_off": "🛑 Auto-clean बंद किया गया।",
        "auto_set": "✅ Auto-clean सेट किया गया — अंतराल {t}.",
        "cleanall_start": "🧹 मीडिया हटाया जा रहा है...",
        "cleanall_done": "✅ {n} मीडिया हटाए गए।",
        "only_admin": "⚠️ केवल group admins उपयोग कर सकते हैं।",
        "only_owner": "⚠️ केवल group owner या co-owner उपयोग कर सकते हैं।",
        "status_text": "Auto-clean: {on} | Interval: {t}",
        "ping_text": "🏓 Pong! {ms}ms",
    },
}

SUPPORTED_LOCALES = list(MESSAGES.keys())
DEFAULT_LOCALE = "en-in"

# ---------------------------
# STORAGE HANDLING
# ---------------------------
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

DATA = load_data()  # format: { "<chat_id>": {"clean_on":bool,"delete_minutes":int,"lang":str} }

def ensure_chat(chat_id):
    cid = str(chat_id)
    if cid not in DATA:
        DATA[cid] = {"clean_on": False, "delete_minutes": 60, "lang": DEFAULT_LOCALE}
        save_data(DATA)
    return DATA[cid]

# ---------------------------
# UTILITIES
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
    """
    Accept forms:
      20m, 120, 2h, 1d
    Return minutes int or None
    """
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
        # plain integer treated as minutes
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
# APP INIT
# ---------------------------
app = Client("ShieldXBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
flask_app = Flask(__name__)

# ---------------------------
# COMMANDS
# ---------------------------
@app.on_message(filters.command("start", prefixes=["/", "!"]))
async def start_cmd(client, message):
    cfg = ensure_chat(message.chat.id if message.chat else message.from_user.id)
    # If private, show UI buttons
    try:
        if message.chat and message.chat.type == "private":
            text = get_msg("start_dm", message.chat.id)
            me = await client.get_me()
            buttons = [
                [types.InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{me.username}?startgroup=new")],
                [types.InlineKeyboardButton("📘 Commands", callback_data="sx_help")],
            ]
            await message.reply_text(text, reply_markup=types.InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        else:
            # short group reply
            await message.reply(get_msg("start_group", message.chat.id), quote=False)
    except Exception:
        # don't crash on weird chat types
        pass

@app.on_message(filters.command("help", prefixes=["/", "!"]))
async def help_cmd(client, message):
    try:
        if message.chat and message.chat.type == "private":
            await message.reply_text(get_msg("help_dm", message.chat.id), disable_web_page_preview=True)
        else:
            # short group ping to DM
            try:
                await message.reply(get_msg("help_group", message.chat.id), quote=False)
            except ChatWriteForbidden:
                pass
    except Exception:
        pass

# callback handlers for inline help button
@app.on_callback_query(filters.regex(r"^sx_help$"))
async def cb_help(client, query):
    await query.answer()
    try:
        await query.message.edit_text(get_msg("help_dm", query.message.chat.id))
    except:
        pass

# /status
@app.on_message(filters.command("status", prefixes=["/", "!"]) & filters.group)
async def status_cmd(client, message):
    cfg = ensure_chat(message.chat.id)
    on = "On" if cfg.get("clean_on") else "Off"
    t = fmt_timespan(cfg.get("delete_minutes", 60))
    await message.reply(get_msg("status_text", message.chat.id, on=on, t=t), quote=False)

# /ping
@app.on_message(filters.command("ping", prefixes=["/", "!"]))
async def ping_cmd(client, message):
    t0 = time.time()
    m = await message.reply("🏓 ...")
    ms = int((time.time() - t0) * 1000)
    await m.edit_text(get_msg("ping_text", message.chat.id, ms=ms))

# /lang <code>
@app.on_message(filters.command("lang", prefixes=["/", "!"]) & filters.group)
async def lang_cmd(client, message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /lang <locale_code> (eg. en-in, en-us, hi, fr, de)", quote=False)
        return
    code = args[1].lower()
    if code not in SUPPORTED_LOCALES:
        await message.reply(f"Unsupported. Supported: {', '.join(SUPPORTED_LOCALES)}", quote=False)
        return
    cfg = ensure_chat(message.chat.id)
    cfg["lang"] = code
    save_data(DATA)
    await message.reply(get_msg("start_group", message.chat.id) + f"\n🌐 Language: {code}", quote=False)

# /clean [time|on|off]
@app.on_message(filters.command("clean", prefixes=["/", "!"]) & filters.group)
async def clean_cmd(client, message):
    # only admins
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
            cfg["delete_minutes"] = 60
            save_data(DATA)
            await message.reply(get_msg("auto_on", message.chat.id, t=fmt_timespan(cfg["delete_minutes"])), quote=False)
            return
        if token == "off":
            cfg["clean_on"] = False
            save_data(DATA)
            await message.reply(get_msg("auto_off", message.chat.id), quote=False)
            return
        # parse time token
        mins = parse_time_token(token)
        if mins is None or mins < 20 or mins > 1440:
            await message.reply("⚠️ Provide time between 20m and 24h (e.g. 20m, 2h, 1d).", quote=False)
            return
        cfg["clean_on"] = True
        cfg["delete_minutes"] = mins
        save_data(DATA)
        await message.reply(get_msg("auto_set", message.chat.id, t=fmt_timespan(mins)), quote=False)
        return

    # default on = 60
    cfg["clean_on"] = True
    cfg["delete_minutes"] = 60
    save_data(DATA)
    await message.reply(get_msg("auto_on", message.chat.id, t=fmt_timespan(cfg["delete_minutes"])), quote=False)

# /cleanall (group owner or co-owner)
@app.on_message(filters.command("cleanall", prefixes=["/", "!"]) & filters.group)
async def cleanall_cmd(client, message):
    user_id = message.from_user.id
    try:
        m = await client.get_chat_member(message.chat.id, user_id)
        is_owner = (m.status == "creator")
    except:
        is_owner = False

    # allow env-defined co-owners as well
    if not (is_owner or user_id in CO_OWNER_IDS):
        await message.reply(get_msg("only_owner", message.chat.id), quote=False)
        return

    # start cleaning
    await message.reply(get_msg("cleanall_start", message.chat.id), quote=False)
    deleted = 0
    try:
        # iterate over recent history (limit to avoid long tasks)
        async for msg in client.get_chat_history(message.chat.id, limit=500):
            if msg.media:
                try:
                    await client.delete_messages(message.chat.id, msg.message_id)
                    deleted += 1
                except RPCError:
                    # skip messages we can't delete (permissions, older than allowed, etc.)
                    continue
    except Exception:
        # in case of any error retrieving history, continue
        pass

    await message.reply(get_msg("cleanall_done", message.chat.id, n=deleted), quote=False)

# Auto-delete monitor
@app.on_message(filters.group)
async def auto_delete_monitor(client, message):
    cfg = ensure_chat(message.chat.id)
    if not cfg.get("clean_on"):
        return
    # only act on media messages
    if message.media:
        mins = cfg.get("delete_minutes", 60)
        delay = int(mins) * 60
        # if immediate deletion configured (0), attempt immediate delete
        if delay == 0:
            try:
                await client.delete_messages(message.chat.id, message.message_id)
            except:
                pass
        else:
            # schedule deletion without awaiting (fire-and-forget)
            asyncio.create_task(schedule_delete(client, message.chat.id, message.message_id, delay))

async def schedule_delete(client, chat_id, msg_id, delay):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, msg_id)
    except:
        pass

# ---------------------------
# FLASK KEEP-ALIVE
# ---------------------------
@flask_app.route("/")
def index():
    return "🩵 ShieldX Bot — alive"

@flask_app.route("/healthz")
def healthz():
    return "OK", 200

def run_flask():
    # Use a non-blocking Flask run in a daemon thread — keep default port env-driven
    port = int(os.getenv("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# ---------------------------
# MAIN
# ---------------------------
async def main():
    # start flask keep-alive in background thread
    threading.Thread(target=run_flask, daemon=True).start()
    print("🩵 ShieldX starting...")
    try:
        await app.start()
        me = await app.get_me()
        print(f"🩵 ShieldX started (Pyrogram OK). Bot: @{me.username} ({me.id})")
    except Exception as e:
        print("❌ Failed to start Pyrogram client:", e)
        return

    # keep alive forever
    try:
        await asyncio.Event().wait()
    finally:
        try:
            await app.stop()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
