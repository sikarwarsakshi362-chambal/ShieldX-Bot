# -*- coding: utf-8 -*-
# ShieldX Bot v3.1 — Hybrid (Always-on NSFW, auto-clean, spam-mute, multi-lang UI)
# Requirements: pyrogram, flask, python-dotenv, opencv-python (optional), numpy (optional), pillow (optional)

import asyncio
import os
import threading
import time
import tempfile
import shutil
from datetime import datetime, timedelta
from flask import Flask
from pyrogram import Client, filters, types
from pyrogram.errors import RPCError
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

# Optional image libs for local NSFW heuristic
try:
    import cv2
    import numpy as np
    from PIL import Image
except Exception:
    cv2 = None
    np = None
    Image = None

# === Load .env Variables ===
load_dotenv()
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
PORT = int(os.getenv("PORT", 8080))
DEFAULT_LANG = os.getenv("LANG", "en")  # default bot language

# === Flask App for KeepAlive / Health ===
app = Flask(__name__)

@app.route("/")
def home():
    return "🛡️ ShieldX Active — running 24×7."

@app.route("/healthz")
def healthz():
    return "ok"

def keep_alive_sync():
    # Bind to PORT from env (Render / hosts expect PORT)
    app.run(host="0.0.0.0", port=PORT)

# === Text Constants (multi-language support store) ===
# Minimal example: you can expand translations. Keys used across bot.
LANG_STRINGS = {
    "en": {
        "start_dm_text": (
            "🛡️ **Welcome to ShieldX Protection!**\n\n"
            "I’m your 24×7 automated guard that keeps your Telegram groups clean and secure.\n\n"
            "🧹 What I do:\n"
            "• Auto-clean spam & media floods\n"
            "• Detect & delete NSFW content\n"
            "• Keep your community safe without downtime\n\n"
            "🚀 Add me to your group to activate real-time protection."
        ),
        "start_group_text": "🛡️ ShieldX is now active in this group! Admins: use /help.",
        "help_dm": (
            "✨ **ShieldX — Control Center**\n\n"
            "🧹 **Auto-Clean:**\n"
            "• /clean on — enable auto-clean (default: 30m)\n"
            "• /clean_custom <time> — set custom clean time (e.g., 20m, 1h)\n            "
            "• /clean off — disable auto-clean\n"
            "• /cleanstatus — show current clean status\n"
            "• /cleanall — delete recent media (last 24h)\n\n"
            "🚫 **NSFW Protection:**\n"
            "• Always active — images/videos scanned and deleted instantly if NSFW.\n\n"
            "⚙️ **Utility:**\n"
            "• /status — view live protection state\n"
            "• /ping — check response & uptime\n"
            "• /lang <code> — change UI language for this chat\n\n"
            "🕒 Default clean interval: 30 minutes"
        ),
        "help_group": "📩 Check your DM for ShieldX’s full command list.",
        "clean_on": "✅ Auto-clean enabled — media will be removed every 30 minutes.",
        "clean_custom": "✅ Auto-clean enabled — media will be removed every {t}.",
        "clean_off": "🛑 Auto-clean disabled.",
        "cleanall_start": "🧹 Starting safe media delete for last {t}... This may take a while.",
        "cleanall_done": "✅ Media delete complete — removed {n} media items from last {t}.",
        "status_text": "🧹 Auto-clean: {on} | Interval: {t}",
        "ping_text": "🩵 ShieldX Online!\n⚡ {ms}ms | Uptime: {uptime}",
        "nsfw_deleted": "⚠️ NSFW content detected and deleted. Please follow group rules.",
        "nsfw_muted": "🚫 User muted for repeated NSFW spam.",
        "lang_changed": "🌐 Language for this chat changed to: {lang}",
        "no_permission": "❌ You must be an admin or the owner to use this command.",
        "unknown_lang": "⚠️ Unknown language code.",
        "status_overview": "🧭 ShieldX status:\nAuto-clean: {clean}\nNSFW: always ON\nLanguage: {lang}"
    },

    # Example additional languages. Add translations as needed.
    "hi": {  # Hindi (example - partial)
        "start_dm_text": "🛡️ ShieldX में आपका स्वागत है! मैं आपके समूह को 24×7 सुरक्षित रखता हूँ।",
        "start_group_text": "🛡️ ShieldX अब इस समूह में सक्रिय है! एडमिन /help देखें।",
        "help_dm": "✨ ShieldX — कमांड सूची (संक्षेप):\n/clean on, /clean_custom, /clean off, /cleanstatus, /ping, /lang <code>",
        "help_group": "📩 पूर्ण कमांड सूची के लिए DM देखें।",
        "clean_on": "✅ ऑटो-क्लीन सक्षम — प्रत्येक 30 मिनट में मीडिया हटाया जाएगा।",
        "clean_custom": "✅ ऑटो-क्लीन सक्षम — मीडिया हटाया जाएगा हर {t}।",
        "clean_off": "🛑 ऑटो-क्लीन अक्षम।",
        "cleanall_start": "🧹 पिछले {t} के मीडिया की सुरक्षित हटाई शुरू कर रहा हूँ...",
        "cleanall_done": "✅ मीडिया हटाना पूरा — हटाए गए {n} आइटम।",
        "status_text": "🧹 Auto-clean: {on} | Interval: {t}",
        "ping_text": "🩵 ShieldX ऑनलाइन!\n⚡ {ms}ms | Uptime: {uptime}",
        "nsfw_deleted": "⚠️ NSFW कंटेंट हटाया गया। नियमों का पालन करें।",
        "nsfw_muted": "🚫 यूज़र को NSFW स्पैम के लिए म्यूट किया गया।",
        "lang_changed": "🌐 इस चैट की भाषा बदल दी गई: {lang}",
        "no_permission": "❌ इस कमांड के लिए आपको एडमिन या ओनर होना चाहिए।",
        "unknown_lang": "⚠️ अज्ञात भाषा कोड।",
        "status_overview": "🧭 ShieldX स्थिति:\nAuto-clean: {clean}\nNSFW: हमेशा ON\nLanguage: {lang}"
    },

    # Add more languages (ru, bn, etc.) as needed
}

# Per-chat language (defaults to DEFAULT_LANG)
chat_lang = {}  # chat_id -> lang_code

def t(chat_id: int, key: str, **kwargs) -> str:
    """Translate helper: choose language for chat, fallback to default english."""
    lang = chat_lang.get(chat_id, DEFAULT_LANG)
    strings = LANG_STRINGS.get(lang, LANG_STRINGS["en"])
    text = strings.get(key, LANG_STRINGS["en"].get(key, ""))
    try:
        return text.format(**kwargs)
    except Exception:
        return text

# === Pyrogram Client ===
bot = Client("ShieldX", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# === State stores ===
clean_intervals = {}   # chat_id: seconds
clean_tasks = {}       # chat_id: asyncio.Task

# Keep user nsfw timestamps for spam detection (sliding window)
user_nsfw_log = {}  # chat_id -> { user_id: [timestamps] }

# === Module check (startup log) ===
def log_module_status():
    cv2_ok = "OK" if cv2 is not None else "MISSING"
    pil_ok = "OK" if Image is not None else "MISSING"
    np_ok = "OK" if np is not None else "MISSING"
    print(f"🧠 NSFW modules check → cv2: {cv2_ok}, PIL: {pil_ok}, numpy: {np_ok}")
    if cv2 is None or Image is None or np is None:
        print("⚠️ NSFW detection will run in fallback mode if modules are missing (no crash).")

# --------------------------
# Helper: allow owner OR bot OR admin
# --------------------------
async def is_admin_or_owner(client, chat_id: int, user_id: int) -> bool:
    try:
        # owner always allowed
        if user_id == OWNER_ID:
            return True
        # bot itself allowed
        me = await client.get_me()
        if me and getattr(me, "id", None) == user_id:
            return True
        # check chat membership/roles
        member = await client.get_chat_member(chat_id, user_id)
        if getattr(member, "status", None) in ("administrator", "creator"):
            return True
    except Exception:
        # any failure => deny (fail-safe)
        pass
    return False

# --------------------------
# Local NSFW heuristic (skin ratio)
# --------------------------
def is_nsfw_local(image_path: str, skin_ratio_threshold: float = 0.30) -> bool:
    """
    Return True if image looks NSFW by simple skin-pixel ratio heuristic.
    If cv2/numpy not available returns False (no instant delete).
    """
    if cv2 is None or np is None:
        return False
    try:
        img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return False
        h, w = img.shape[:2]
        # resize to limit computation
        scale = 600.0 / max(h, w) if max(h, w) > 600 else 1.0
        if scale != 1.0:
            img = cv2.resize(img, (int(w * scale), int(h * scale)))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # simple skin color ranges (works as heuristic)
        lower1 = np.array([0, 10, 60], dtype=np.uint8)
        upper1 = np.array([20, 150, 255], dtype=np.uint8)
        lower2 = np.array([160, 10, 60], dtype=np.uint8)
        upper2 = np.array([179, 150, 255], dtype=np.uint8)
        mask = cv2.bitwise_or(cv2.inRange(hsv, lower1, upper1), cv2.inRange(hsv, lower2, upper2))
        skin_pixels = int(cv2.countNonZero(mask))
        total_pixels = img.shape[0] * img.shape[1]
        ratio = skin_pixels / float(total_pixels) if total_pixels > 0 else 0.0
        return ratio >= skin_ratio_threshold
    except Exception as e:
        print("is_nsfw_local error:", e)
        return False

# --------------------------
# Periodic cleaner task per chat (auto-clean) - BATCH-WISE
# --------------------------
async def clean_media_periodically(chat_id: int, interval: int):
    while True:
        try:
            deleted = 0
            batch = []
            async for msg in bot.get_chat_history(chat_id, limit=500):
                if msg.media:
                    batch.append(msg.message_id)
                    if len(batch) >= 20:
                        try:
                            await bot.delete_messages(chat_id, batch)
                            deleted += len(batch)
                        except Exception:
                            # fallback: try individual deletes
                            for mid in batch:
                                try:
                                    await bot.delete_messages(chat_id, mid)
                                except:
                                    pass
                        batch.clear()
                        await asyncio.sleep(2)  # short pause between batches
            if batch:
                try:
                    await bot.delete_messages(chat_id, batch)
                    deleted += len(batch)
                except Exception:
                    for mid in batch:
                        try:
                            await bot.delete_messages(chat_id, mid)
                        except:
                            pass
            if deleted:
                print(f"[AUTO CLEAN] Deleted {deleted} media in chat {chat_id}")
            await asyncio.sleep(interval)
        except RPCError:
            await asyncio.sleep(10)
        except Exception as e:
            print("clean_media_periodically error:", e)
            await asyncio.sleep(10)

# --------------------------
# Handlers: start/help/ping/lang
# --------------------------
@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    # send DM if private; in group, send group text + prompt
    if message.chat.type == "private":
        buttons = [
            [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{(await client.get_me()).username}?startgroup=true"),
             InlineKeyboardButton("💬 Support", url="https://t.me/ShieldXSupport")]
        ]
        await message.reply_text(t(message.chat.id, "start_dm_text"), reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        await message.reply_text(t(message.chat.id, "start_group_text"), disable_web_page_preview=True)

@bot.on_message(filters.command("help"))
async def help_cmd(client, message):
    if message.chat.type == "private":
        await message.reply_text(t(message.chat.id, "help_dm"), disable_web_page_preview=True)
    else:
        await message.reply_text(t(message.chat.id, "help_group"), disable_web_page_preview=True)

start_time = time.time()

@bot.on_message(filters.command("ping"))
async def ping_cmd(client, message):
    start = time.time()
    try:
        m = await message.reply_text("🏓 Pinging...")
        ms = int((time.time() - start) * 1000)
        uptime = str(datetime.utcnow() - datetime.utcfromtimestamp(start_time)).split(".")[0]
        await m.edit_text(t(message.chat.id, "ping_text", ms=ms, uptime=uptime))
    except Exception:
        uptime = str(datetime.utcnow() - datetime.utcfromtimestamp(start_time)).split(".")[0]
        await message.reply_text(t(message.chat.id, "ping_text", ms=0, uptime=uptime))

@bot.on_message(filters.command("lang"))
async def lang_cmd(client, message):
    # allow anyone to set language for their chat (admins recommended)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: /lang <code> (e.g. en, hi, ru)")
        return
    code = parts[1].strip().lower()
    if code not in LANG_STRINGS:
        await message.reply_text(t(message.chat.id, "unknown_lang"))
        return
    chat_lang[message.chat.id] = code
    await message.reply_text(t(message.chat.id, "lang_changed", lang=code))

@bot.on_message(filters.command("status"))
async def status_cmd(client, message):
    chat_id = message.chat.id
    on = "ON" if chat_id in clean_tasks else "OFF"
    interval = clean_intervals.get(chat_id, 0)
    t_str = f"{interval//60}m" if interval else "—"
    lang = chat_lang.get(chat_id, DEFAULT_LANG)
    await message.reply_text(t(chat_id, "status_overview", clean=on, lang=lang))

# --------------------------
# CLEAN commands: /clean on, /clean_custom, /clean off, /cleanstatus, /cleanall
# --------------------------
@bot.on_message(filters.command(["clean", "clean_on"], prefixes=["/", "!", "."]))
async def clean_on_cmd(client, msg):
    # admin/owner/bot-only
    try:
        user_id = msg.from_user.id if msg.from_user else None
        if not user_id or not await is_admin_or_owner(client, msg.chat.id, user_id):
            await msg.reply_text(t(msg.chat.id, "no_permission"))
            return
    except:
        return

    chat_id = msg.chat.id
    interval = 30 * 60  # 30 minutes default
    if chat_id in clean_tasks:
        try:
            clean_tasks[chat_id].cancel()
        except:
            pass
    task = asyncio.create_task(clean_media_periodically(chat_id, interval))
    clean_tasks[chat_id] = task
    clean_intervals[chat_id] = interval
    await msg.reply_text(t(chat_id, "clean_on"))

@bot.on_message(filters.command("clean_custom"))
async def clean_custom_cmd(client, msg):
    # admin/owner/bot-only
    try:
        user_id = msg.from_user.id if msg.from_user else None
        if not user_id or not await is_admin_or_owner(client, msg.chat.id, user_id):
            await msg.reply_text(t(msg.chat.id, "no_permission"))
            return
    except:
        return

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply_text("Usage: /clean_custom <time> e.g., /clean_custom 20m", quote=True)
        return
    t = parts[1].strip().lower()
    seconds = 0
    try:
        if t.endswith("m"):
            minutes = int(t[:-1])
            if minutes < 1 or minutes > 1440:
                await msg.reply_text("⚠️ /clean_custom supports 1m to 24h only.", quote=True)
                return
            seconds = minutes * 60
        elif t.endswith("h"):
            hours = int(t[:-1])
            if hours < 1 or hours > 24:
                await msg.reply_text("⚠️ /clean_custom supports 1h to 24h only.", quote=True)
                return
            seconds = hours * 3600
        else:
            await msg.reply_text("Invalid format! Use like 20m or 1h.", quote=True)
            return
    except:
        await msg.reply_text("Invalid numeric value.", quote=True)
        return

    chat_id = msg.chat.id
    if chat_id in clean_tasks:
        try:
            clean_tasks[chat_id].cancel()
        except:
            pass
    task = asyncio.create_task(clean_media_periodically(chat_id, seconds))
    clean_tasks[chat_id] = task
    clean_intervals[chat_id] = seconds
    await msg.reply_text(t(chat_id, "clean_custom", t=t))

@bot.on_message(filters.command(["clean_off", "cleanoff"], prefixes=["/", "!", "."]))
async def clean_off_cmd(client, msg):
    # admin/owner/bot-only
    try:
        user_id = msg.from_user.id if msg.from_user else None
        if not user_id or not await is_admin_or_owner(client, msg.chat.id, user_id):
            await msg.reply_text(t(msg.chat.id, "no_permission"))
            return
    except:
        return

    chat_id = msg.chat.id
    if chat_id in clean_tasks:
        try:
            clean_tasks[chat_id].cancel()
        except:
            pass
        del clean_tasks[chat_id]
        if chat_id in clean_intervals:
            del clean_intervals[chat_id]
        await msg.reply_text(t(chat_id, "clean_off"))
    else:
        await msg.reply_text("❌ Auto-clean not active in this chat.")

@bot.on_message(filters.command("cleanstatus"))
async def clean_status_cmd(client, msg):
    # admin/owner/bot-only
    try:
        user_id = msg.from_user.id if msg.from_user else None
        if not user_id or not await is_admin_or_owner(client, msg.chat.id, user_id):
            await msg.reply_text(t(msg.chat.id, "no_permission"))
            return
    except:
        return
    chat_id = msg.chat.id
    on = "ON" if chat_id in clean_tasks else "OFF"
    interval = clean_intervals.get(chat_id, 0)
    t = f"{interval//60}m" if interval else "—"
    await msg.reply_text(t(chat_id, "status_text", on=on, t=t))

@bot.on_message(filters.command("cleanall"))
async def cleanall_cmd(client, msg):
    # admin/owner/bot-only
    try:
        user_id = msg.from_user.id if msg.from_user else None
        if not user_id or not await is_admin_or_owner(client, msg.chat.id, user_id):
            await msg.reply_text(t(msg.chat.id, "no_permission"))
            return
    except:
        return

    await msg.reply_text(t(msg.chat.id, "cleanall_start", t="24h"))
    deleted = 0
    batch = []
    cutoff = datetime.utcnow() - timedelta(hours=24)

    try:
        async for m in client.get_chat_history(msg.chat.id, limit=5000):
            # normalize naive datetimes
            if isinstance(m.date, datetime) and m.date.tzinfo is None:
                msg_date = m.date.replace(tzinfo=None)
            else:
                msg_date = m.date
            if msg_date < cutoff:
                break
            if m.media:
                batch.append(m.message_id)
                if len(batch) >= 20:
                    try:
                        await client.delete_messages(msg.chat.id, batch)
                        deleted += len(batch)
                    except Exception:
                        for mid in batch:
                            try:
                                await client.delete_messages(msg.chat.id, mid)
                                deleted += 1
                            except:
                                pass
                    batch.clear()
                    await asyncio.sleep(2)
        if batch:
            try:
                await client.delete_messages(msg.chat.id, batch)
                deleted += len(batch)
            except Exception:
                for mid in batch:
                    try:
                        await client.delete_messages(msg.chat.id, mid)
                        deleted += 1
                    except:
                        pass
    except Exception as e:
        print("cleanall error:", e)

    await msg.reply_text(t(msg.chat.id, "cleanall_done", n=deleted, t="24h"))

# --------------------------
# Media handler: NSFW always-on + schedule/delete + spam mute
# --------------------------
@bot.on_message(filters.group & (filters.photo | filters.video | filters.sticker | filters.animation | filters.document))
async def media_handler(client, message):
    if message.from_user is None:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    tmpdir = None
    path = None
    try:
        tmpdir = tempfile.mkdtemp()
        path = await client.download_media(message, file_name=os.path.join(tmpdir, "media"))
        if not path or not os.path.exists(path):
            # cleanup and exit
            if path and os.path.exists(path):
                try: os.remove(path)
                except: pass
            if tmpdir:
                try: shutil.rmtree(tmpdir, ignore_errors=True)
                except: pass
            return

        # ALWAYS ACTIVE NSFW detection (local heuristic)
        nsfw_flag = is_nsfw_local(path, skin_ratio_threshold=0.30)

        # cleanup temp files asap
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except:
            pass
        if tmpdir:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except:
                pass

        if nsfw_flag:
            # instant remove
            try:
                await client.delete_messages(chat_id, message.message_id)
            except:
                pass

            # sliding-window spam detection per-chat
            now = time.time()
            chat_map = user_nsfw_log.setdefault(chat_id, {})
            lst = chat_map.setdefault(user_id, [])
            lst.append(now)
            # keep only last 3 seconds
            chat_map[user_id] = [t for t in lst if now - t <= 3]

            # if 5 or more NSFW media within 3 seconds -> permanent mute (restrict)
            if len(chat_map[user_id]) >= 5:
                try:
                    # Restrict permanently: set can_send_messages False
                    await client.restrict_chat_member(chat_id, user_id, permissions=types.ChatPermissions(can_send_messages=False))
                    await client.send_message(chat_id, t(chat_id, "nsfw_muted"))
                    chat_map[user_id] = []
                except Exception as e:
                    print("mute failed:", e)
            else:
                try:
                    await client.send_message(chat_id, t(chat_id, "nsfw_deleted"))
                except:
                    pass
            return
        else:
            # Not NSFW — schedule normal auto-clean if active
            if chat_id in clean_intervals:
                interval = clean_intervals[chat_id]
                asyncio.create_task(schedule_delete(client, chat_id, message.message_id, interval))
            return
    except Exception as e:
        print("media_handler error:", e)
        try:
            if path and os.path.exists(path):
                os.remove(path)
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass

async def schedule_delete(client, chat_id, msg_id, delay):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, msg_id)
    except:
        pass

# --------------------------
# NOTE: /nsfw_on and /nsfw_off commands intentionally removed — NSFW always active
# --------------------------

# --------------------------
# KEEP ALIVE & WATCHDOG
# --------------------------
async def background_keepalive():
    while True:
        print("💤 Ping: ShieldX alive...")
        await asyncio.sleep(300)

async def watchdog_task(bot_client):
    while True:
        try:
            # send a quiet message to owner as heartbeat
            await bot_client.send_message(OWNER_ID, "🩵 ShieldX watchdog ping OK.", disable_notification=True)
        except Exception:
            pass
        await asyncio.sleep(1800)  # every 30 min

# --------------------------
# STARTUP
# --------------------------
async def main():
    log_module_status()
    try:
        await bot.start()
        print("✅ Pyrogram client started.")
    except Exception as e:
        print("❌ Failed to start Pyrogram client:", e)
        return

    # start keepalive/watchdog
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

    # start flask thread for health endpoint
    try:
        threading.Thread(target=keep_alive_sync, daemon=True).start()
    except Exception as e:
        print("⚠️ Failed to start keep_alive_sync thread:", e)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown requested, exiting...")
