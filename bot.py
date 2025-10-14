# -*- coding: utf-8 -*-
# ShieldX Bot v3 — Final (Commands fixed, batch-safe deletes, NSFW instant delete, module check)
# Requirements: pyrogram, flask, python-dotenv, opencv-python (optional), numpy (optional), pillow (optional)

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

# Local image libs (optional)
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

# === Flask App for KeepAlive ===
app = Flask(__name__)

@app.route("/")
def home():
    return "🛡️ ShieldX Active — running 24×7."

def keep_alive_sync():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

# === Text Constants ===
TXT = {
    "start_dm": {
        "text": (
            "🛡️ **Welcome to ShieldX Protection!**\n\n"
            "I’m your 24×7 automated guard that keeps your Telegram groups clean and secure.\n\n"
            "🧹 What I do:\n"
            "• Auto-clean spam & media floods\n"
            "• Detect & delete NSFW content\n"
            "• Keep your community safe without downtime\n\n"
            "🚀 Add me to your group to activate real-time protection."
        ),
        "buttons": [
            [
                {"text": "➕ Add to Group", "url": "https://t.me/shieldxprotector_bot?startgroup=true"},
                {"text": "💬 Support", "url": "https://t.me/ShieldXSupport"}
            ]
        ]
    },

    "start_group": {
        "text": (
            "🛡️ ShieldX is now active in this group!\n\n"
            "I’m guarding your chat 24×7 against spam, NSFW, and unwanted media.\n"
            "Admins can manage protection via /help.\n\n"
            "💡 *Try:* `/clean on`, `/clean_custom`, `/status`"
        ),
        "buttons": [
            [
                {"text": "➕ Add to Another Group", "url": "https://t.me/shieldxprotector_bot?startgroup=true"},
                {"text": "💬 Support", "url": "https://t.me/ShieldXSupport"}
            ]
        ]
    },

    "help_dm": (
        "✨ **ShieldX — Control Center**\n\n"
        "🧹 **Auto-Clean:**\n"
        "• `/clean on` — enable auto-clean (default: 30m)\n"
        "• `/clean_custom <time>` — set custom clean time (e.g., 20m, 1h)\n"
        "• `/clean off` — disable auto-clean\n"
        "• `/cleanstatus` — show current clean status\n"
        "• `/cleanall` — delete recent media (last 24h)\n\n"
        "🚫 **NSFW Protection:**\n"
        "• `/nsfw_on` — enable NSFW detection (local)\n"
        "• `/nsfw_off` — disable NSFW detection\n\n"
        "⚙️ **Utility:**\n"
        "• `/status` — view live protection state\n"
        "• `/ping` — check response & uptime\n"
        "• `/lang <code>` — change language\n\n"
        "🕒 Default clean interval: 30 minutes\n"
        "🔗 [Add ShieldX to your Group](https://t.me/shieldxprotector_bot?startgroup=true)"
    ),

    "help_group": (
        "📩 Check your DM for ShieldX’s full command list.\n\n"
        "[📘 Open Command Center](https://t.me/shieldxprotector_bot?start=help)"
    ),

    "clean_on": "✅ /clean on — media will be automatically removed every 30 minutes.",
    "clean_custom": "✅ /clean_custom — media will be automatically removed every {t}.",
    "clean_off": "🛑 /clean off — auto media removal disabled.",
    "cleanall_start": "🧹 Starting safe media delete for last {t}... This may take a while.",
    "cleanall_done": "✅ Media delete complete — removed {n} media items from last {t}.",
    "status_text": "🧹 Auto-clean: {on} | Interval: {t}",
    "ping_text": "🩵 ShieldX Online!\n⚡ {ms}ms | Uptime: {uptime}",
    "nsfw_deleted": "⚠️ NSFW content detected and deleted. Please follow group rules.",
    "nsfw_on": "🔎 NSFW detection enabled — messages will be scanned automatically (local heuristic).",
    "nsfw_off": "🚫 NSFW detection disabled — no scanning active.",
}

# === Pyrogram Client ===
bot = Client("ShieldX", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# === State stores ===
clean_intervals = {}   # chat_id: seconds
clean_tasks = {}       # chat_id: asyncio.Task
nsfw_enabled = set()   # chat ids with NSFW detection on

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
    """
    Return True if user_id is:
      - OWNER_ID (configured owner)
      - the bot itself (so 'self' commands allowed)
      - an administrator/creator of the chat
    This fixes the 'same ID' problem where owner and bot share the same identity.
    """
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
# Local NSFW heuristic
# --------------------------
def is_nsfw_local(image_path: str, skin_ratio_threshold: float = 0.30) -> bool:
    if cv2 is None or np is None:
        return False
    try:
        img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return False
        h, w = img.shape[:2]
        scale = 600.0 / max(h, w) if max(h, w) > 600 else 1.0
        if scale != 1.0:
            img = cv2.resize(img, (int(w * scale), int(h * scale)))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower1 = np.array([0, 10, 60], dtype=np.uint8)
        upper1 = np.array([20, 150, 255], dtype=np.uint8)
        lower2 = np.array([160, 10, 60], dtype=np.uint8)
        upper2 = np.array([179, 150, 255], dtype=np.uint8)
        mask = cv2.bitwise_or(cv2.inRange(hsv, lower1, upper1), cv2.inRange(hsv, lower2, upper2))
        skin_pixels = int(cv2.countNonZero(mask))
        total_pixels = img.shape[0] * img.shape[1]
        ratio = skin_pixels / float(total_pixels) if total_pixels > 0 else 0.0
        if total_pixels < 500 * 500 and ratio < 0.5:
            pass
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
                        await asyncio.sleep(3)
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
# Handlers: start/help/ping
# --------------------------
@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    data = TXT["start_dm"] if message.chat.type == "private" else TXT["start_group"]
    if isinstance(data, dict):
        buttons = [
            [InlineKeyboardButton(btn["text"], url=btn["url"]) for btn in row]
            for row in data["buttons"]
        ]
        await message.reply_text(data["text"], reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        await message.reply_text(data, disable_web_page_preview=True)

@bot.on_message(filters.command("help"))
async def help_cmd(client, message):
    text = TXT["help_dm"] if message.chat.type == "private" else TXT["help_group"]
    await message.reply_text(text, disable_web_page_preview=True)

start_time = time.time()

@bot.on_message(filters.command("ping"))
async def ping_cmd(client, message):
    start = time.time()
    try:
        m = await message.reply_text("🏓 Pinging...")
        ms = int((time.time() - start) * 1000)
        uptime = str(datetime.utcnow() - datetime.utcfromtimestamp(start_time)).split(".")[0]
        await m.edit_text(TXT["ping_text"].format(ms=ms, uptime=uptime))
    except Exception:
        uptime = str(datetime.utcnow() - datetime.utcfromtimestamp(start_time)).split(".")[0]
        await message.reply_text(TXT["ping_text"].format(ms=0, uptime=uptime))

# --------------------------
# CLEAN commands: /clean on, /clean_custom, /clean off, /cleanstatus, /cleanall
# --------------------------
@bot.on_message(filters.command(["clean", "clean_on"], prefixes=["/", "!", "."]))
async def clean_on_cmd(client, msg):
    # admin/owner/bot-only
    try:
        user_id = msg.from_user.id if msg.from_user else None
        if not user_id or not await is_admin_or_owner(client, msg.chat.id, user_id):
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
    await msg.reply_text(TXT["clean_on"])

@bot.on_message(filters.command("clean_custom"))
async def clean_custom_cmd(client, msg):
    # admin/owner/bot-only
    try:
        user_id = msg.from_user.id if msg.from_user else None
        if not user_id or not await is_admin_or_owner(client, msg.chat.id, user_id):
            return
    except:
        return

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply_text("Usage: `/clean_custom <time>` e.g., `/clean_custom 20m`", quote=True)
        return
    t = parts[1].strip().lower()
    seconds = 0
    try:
        if t.endswith("m"):
            minutes = int(t[:-1])
            if minutes < 20 or minutes > 1440:
                await msg.reply_text("⚠️ `/clean_custom` supports 20m to 24h only.", quote=True)
                return
            seconds = minutes * 60
        elif t.endswith("h"):
            hours = int(t[:-1])
            if hours < 1 or hours > 24:
                await msg.reply_text("⚠️ `/clean_custom` supports 20m to 24h only.", quote=True)
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
    await msg.reply_text(TXT["clean_custom"].format(t=t))

@bot.on_message(filters.command(["clean_off", "cleanoff"], prefixes=["/", "!", "."]))
async def clean_off_cmd(client, msg):
    # admin/owner/bot-only
    try:
        user_id = msg.from_user.id if msg.from_user else None
        if not user_id or not await is_admin_or_owner(client, msg.chat.id, user_id):
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
        await msg.reply_text(TXT["clean_off"])
    else:
        await msg.reply_text("❌ Auto-clean not active in this chat.")

@bot.on_message(filters.command("cleanstatus"))
async def clean_status_cmd(client, msg):
    # admin/owner/bot-only
    try:
        user_id = msg.from_user.id if msg.from_user else None
        if not user_id or not await is_admin_or_owner(client, msg.chat.id, user_id):
            return
    except:
        return
    chat_id = msg.chat.id
    on = "ON" if chat_id in clean_tasks else "OFF"
    interval = clean_intervals.get(chat_id, 0)
    t = f"{interval//60}m" if interval else "—"
    await msg.reply_text(TXT["status_text"].format(on=on, t=t))

@bot.on_message(filters.command("cleanall"))
async def cleanall_cmd(client, msg):
    # admin/owner/bot-only
    try:
        user_id = msg.from_user.id if msg.from_user else None
        if not user_id or not await is_admin_or_owner(client, msg.chat.id, user_id):
            return
    except:
        return

    await msg.reply_text(TXT["cleanall_start"].format(t="24h"))
    deleted = 0
    batch = []
    cutoff = datetime.utcnow() - timedelta(hours=24)

    try:
        async for m in client.get_chat_history(msg.chat.id, limit=5000):
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
                    await asyncio.sleep(3)

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

    await msg.reply_text(TXT["cleanall_done"].format(n=deleted, t="24h"))

# --------------------------
# Media handler: NSFW check (local) + schedule/delete
# --------------------------
@bot.on_message(filters.group & (filters.photo | filters.video | filters.sticker | filters.animation | filters.document))
async def media_handler(client, message):
    if message.from_user is None:
        return

    chat_id = message.chat.id

    # If NSFW disabled -> schedule normal auto-clean only
    if chat_id not in nsfw_enabled:
        if chat_id in clean_intervals:
            interval = clean_intervals[chat_id]
            asyncio.create_task(schedule_delete(client, chat_id, message.message_id, interval))
        return

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

        # Run local NSFW detection heuristic
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
            # warn in group
            try:
                await client.send_message(chat_id, TXT["nsfw_deleted"])
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
# NSFW toggle commands
# --------------------------
@bot.on_message(filters.command("nsfw_on"))
async def nsfw_on_cmd(client, msg):
    # admin/owner/bot-only
    try:
        user_id = msg.from_user.id if msg.from_user else None
        if not user_id or not await is_admin_or_owner(client, msg.chat.id, user_id):
            return
    except:
        return
    nsfw_enabled.add(msg.chat.id)
    await msg.reply_text(TXT["nsfw_on"])

@bot.on_message(filters.command("nsfw_off"))
async def nsfw_off_cmd(client, msg):
    # admin/owner/bot-only
    try:
        user_id = msg.from_user.id if msg.from_user else None
        if not user_id or not await is_admin_or_owner(client, msg.chat.id, user_id):
            return
    except:
        return
    nsfw_enabled.discard(msg.chat.id)
    await msg.reply_text(TXT["nsfw_off"])

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
