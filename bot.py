# -*- coding: utf-8 -*-
# ShieldX v4 — Final (fixed clean system, NSFW 5-in-3s mute, improved start/help UI)
# Requirements: pyrogram, flask, python-dotenv, opencv-python (optional), numpy (optional), pillow (optional)
# Keep your .env with API_ID, API_HASH, BOT_TOKEN, OWNER_ID, PORT,
# SUPPORT_URL (optional)

import asyncio
import os
import threading
import time
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from typing import Dict, List

from flask import Flask
from pyrogram import Client, filters, types
from pyrogram.errors import RPCError, ChatWriteForbidden
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
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

# ========== Load environment ==========
load_dotenv()
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID_RAW = os.getenv("OWNER_ID", "")
try:
    OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW else 0
except:
    OWNER_ID = 0

PORT = int(os.getenv("PORT", 10000))
SUPPORT_LINK = os.getenv("SUPPORT_URL", "https://t.me/+DVyj2cr4yE85ZWQ1")
ADD_TO_GROUP_USERNAME = os.getenv(
    "ADD_BOT_USERNAME",
     "shieldprotector_bot")  # used in Add button

# Data persistence file (for per-chat settings)
DATA_FILE = "data.json"

# ========== Helpers for persisting chat settings ==========


def load_data() -> Dict:
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_data(d: Dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


DATA = load_data()  # keys: str(chat_id) -> settings dict


def ensure_chat(chat_id: int):
    cid = str(chat_id)
    if cid not in DATA:
        DATA[cid] = {
            "clean_on": False,
            "clean_interval_minutes": 30,
            "nsfw_on": True,
            "action_delay_seconds": 0,
        }
        save_data(DATA)
    return DATA[cid]


# ========== Flask Keepalive ==========
app = Flask(__name__)


@app.route("/")
def home():
    return "🛡️ ShieldX Active — running 24×7."


@app.route("/healthz")
def healthz():
    return "ok"


def run_flask():
    app.run(host="0.0.0.0", port=PORT)


# ========== Pyrogram client ==========
bot = Client("ShieldX", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ========== Module check ==========


def log_module_status():
    cv2_ok = "OK" if cv2 is not None else "MISSING"
    pil_ok = "OK" if Image is not None else "MISSING"
    np_ok = "OK" if np is not None else "MISSING"
    print(
        f"🧠 NSFW modules check → cv2: {cv2_ok}, PIL: {pil_ok}, numpy: {np_ok}")
    if cv2 is None or Image is None or np is None:
        print("⚠️ NSFW detection will run in fallback (heuristic may be limited).")

# ========== NSFW detection (local heuristic fallback) ==========
# Returns True if image likely NSFW by simple skin-tone heuristic
# (best-effort).


def is_nsfw_local(image_path: str, skin_ratio_threshold: float = 0.30) -> bool:
    if cv2 is None or np is None:
        return False
    try:
        img = cv2.imdecode(
    np.fromfile(
        image_path,
        dtype=np.uint8),
         cv2.IMREAD_COLOR)
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
        mask = cv2.bitwise_or(
    cv2.inRange(
        hsv, lower1, upper1), cv2.inRange(
            hsv, lower2, upper2))
        skin_pixels = int(cv2.countNonZero(mask))
        total_pixels = img.shape[0] * img.shape[1]
        ratio = skin_pixels / float(total_pixels) if total_pixels > 0 else 0.0
        return ratio >= skin_ratio_threshold
    except Exception as e:
        print("is_nsfw_local error:", e)
        return False


# ========== NSFW counters and behavior ==========
NSFW_WINDOW_SECONDS = 3
NSFW_SPAM_COUNT = 5  # mute if >= 5 within window
# chat_id -> {user_id -> [timestamps]}
NSFW_COUNTERS: Dict[str, Dict[str, List[float]]] = {}


def prune_nsfw_counters(chat_id: str, user_id: str):
    now = time.time()
    chat_map = NSFW_COUNTERS.setdefault(str(chat_id), {})
    arr = chat_map.setdefault(str(user_id), [])
    arr[:] = [t for t in arr if now - t <= NSFW_WINDOW_SECONDS]
    chat_map[str(user_id)] = arr
    NSFW_COUNTERS[str(chat_id)] = chat_map
    return arr


# ========== Auto-clean background tasks map ==========
clean_tasks = {}  # chat_id -> asyncio.Task


async def clean_media_periodically(
    client: Client,
    chat_id: int,
     interval_seconds: int):
    # Batch sweep: deletes media messages in batches periodically
    while True:
        try:
            deleted = 0
            batch = []
            async for msg in client.get_chat_history(chat_id, limit=500):
                if msg.media:
                    batch.append(msg.message_id)
                    if len(batch) >= 20:
                        try:
                            await client.delete_messages(chat_id, batch)
                            deleted += len(batch)
                        except Exception:
                            for mid in batch:
                                try:
                                    await client.delete_messages(chat_id, mid)
                                except:
                                    pass
                        batch.clear()
                        await asyncio.sleep(1)
            if batch:
                try:
                    await client.delete_messages(chat_id, batch)
                    deleted += len(batch)
                except Exception:
                    for mid in batch:
                        try:
                            await client.delete_messages(chat_id, mid)
                        except:
                            pass
            if deleted:
                print(
                    f"[AUTO CLEAN] Deleted {deleted} media in chat {chat_id}")
            await asyncio.sleep(interval_seconds)
        except RPCError:
            await asyncio.sleep(5)
        except Exception as e:
            print("clean_media_periodically error:", e)
            await asyncio.sleep(5)


def start_clean_task_if_needed(client: Client, chat_id: int):
    cfg = ensure_chat(chat_id)
    if cfg.get("clean_on"):
        interval_minutes = cfg.get("clean_interval_minutes", 30)
        interval_seconds = max(60, int(interval_minutes) * 60)
        if chat_id in clean_tasks:
            # cancel existing and restart with new interval
            try:
                clean_tasks[chat_id].cancel()
            except:
                pass
        clean_tasks[chat_id] = asyncio.create_task(
    clean_media_periodically(
        client, chat_id, interval_seconds))


def stop_clean_task(chat_id: int):
    if chat_id in clean_tasks:
        try:
            clean_tasks[chat_id].cancel()
        except:
            pass
        del clean_tasks[chat_id]

# ========== Utility helpers ==========


async def is_admin_or_owner(
    client: Client,
    chat_id: int,
     user_id: int) -> bool:
    try:
        if user_id == OWNER_ID:
            return True
        me = await client.get_me()
        if me and getattr(me, "id", None) == user_id:
            return True
        member = await client.get_chat_member(chat_id, user_id)
        if getattr(member, "status", None) in ("administrator", "creator"):
            return True
    except Exception:
     pass
    return False


def fmt_interval(mins: int) -> str:
    if mins >= 60 and mins % 60 == 0:
        hours = mins // 60
        return f"{hours}h"
    return f"{mins}m"


# ========== Commands & Handlers ==========
@bot.on_message(filters.command("start") & (filters.private | filters.group))
async def cmd_start(client: Client, message: Message):
    try:
        if message.chat.type == "private":
            me = await client.get_me()
            text = (
                "🛡️ *ShieldX Multi-Protection* — Active & Watching\n\n"
                f"Hey {message.from_user.mention if message.from_user else ''} 👋\n"
                "I'm *ShieldX*, your Telegram Guardian bot — I keep groups safe from spam, unwanted media, and NSFW content 24×7.\n\n"
                "What I provide:\n"
                "• Auto-clean media (custom interval)\n"
                "• Instant NSFW detection & delete\n"
                "• Smart spam-mute for repeat NSFW\n"
                "• Keepalive & watchdog for continuous uptime\n\n"
                "Use the buttons below to get started. /help shows full command list."
            )
            buttons = [
                [
                    InlineKeyboardButton("🧠 Commands", callback_data="sx_help"),
                    InlineKeyboardButton(
                        "➕ Add ShieldX to Group",
                        url=f"https://t.me/{ADD_TO_GROUP_USERNAME}?startgroup=true"
                    ),
                ],
                [
                    InlineKeyboardButton("💙 Support", url=SUPPORT_LINK)
                ]
            ]
            await message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True
            )
        else:
            await message.reply_text(
                "🛡️ ShieldX Guard Active in this group! Admins: use /help to see commands.",
                quote=False
            )
    except Exception:
        pass

@bot.on_callback_query(filters.regex(r"^sx_help$"))
async def cb_help(client: Client, query):
    try:
        await query.answer()
        help_text = (
            "💡 *ShieldX Commands & Usage Guide*\n\n"
            "🧹 /clean on — enable auto media cleanup (default 30m)\n"
            "🧼 /delay <20m|1h|2h> — set custom cleanup interval\n"
            "🛑 /clean off — disable auto-clean\n"
            "🧹 /cleanall — delete media from last 24h (admin only)\n"
            "🔞 NSFW — automatic detection & delete; 5 NSFW posts in 3s = mute\n"
            "🧭 /status — current protection status (group-only)\n"
            "🌐 /lang <code> — change language for this chat (DM only)\n\n"
            "Pro tip: Add ShieldX as admin in your group for full permissions.\n"
            f"Support: {SUPPORT_LINK}"
        )
    except Exception:
        pass

        buttons=[
            [InlineKeyboardButton(
                "🔙 Back to Start", callback_data="sx_start")],
            [
                InlineKeyboardButton(
    "➕ Add to Group",
     url=f"https://t.me/{ADD_TO_GROUP_USERNAME}?startgroup=true"),
                InlineKeyboardButton("💙 Support", url=SUPPORT_LINK)
            ]
        ]
        try:
            await query.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        except:
            await client.send_message(query.from_user.id, help_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    except Exception:
        pass


@ bot.on_message(filters.command("help") & (filters.private | filters.group))
async def cmd_help(client: Client, message: Message):
    try:
        help_text=(
            "💡 *ShieldX Commands & Usage Guide*\n\n"
            "🧹 /clean on — enable auto media cleanup (default 30m)\n"
            "🧼 /delay <20m|1h|2h> — set custom cleanup interval\n"
            "🛑 /clean off — disable auto-clean\n"
            "🧹 /cleanall — delete media from last 24h (admin only)\n"
            "🔞 NSFW — automatic detection & delete; 5 NSFW posts in 3s = mute\n"
            "🧭 /status — current protection status (group-only)\n"
            "🌐 /lang <code> — change language for this chat (DM only)\n\n"
            "Pro tip: Add ShieldX as admin in your group for full permissions.\n"
            f"Support: {SUPPORT_LINK}"
        )
        if message.chat.type == "private":
            buttons=[
                [InlineKeyboardButton(
                    "🔙 Back to Start", callback_data="sx_start")],
                [
                    InlineKeyboardButton(
    "➕ Add to Group",
     url=f"https://t.me/{ADD_TO_GROUP_USERNAME}?startgroup=true"),
                    InlineKeyboardButton("💙 Support", url=SUPPORT_LINK)
                ]
            ]
            await message.reply_text(help_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        else:
            gc_button=InlineKeyboardMarkup(
                [[InlineKeyboardButton(
                    "💌 Open Help in DM", url=f"https://t.me/{ADD_TO_GROUP_USERNAME}?start=help")]]
            )
            await message.reply_text("📘 Help menu sent to your DM 💌", reply_markup=gc_button, quote=False)
            try:
                await client.send_message(message.from_user.id, help_text)
            except Exception:
                pass
    except Exception:
        pass

@ bot.on_callback_query(filters.regex(r"^sx_start$"))
async def cb_start(client: Client, query):
    try:
        await query.answer()
        me=await client.get_me()
        text=(
            "🛡️ *ShieldX Multi-Protection* — Active & Watching\n\n"
            f"Hey {query.from_user.mention if query.from_user else ''} 👋\n"
            "I'm *ShieldX*, your Telegram Guardian bot — keeping groups safe from spam, unwanted media, "
            "and NSFW content 24×7.\n\n"
            "Use /help to see available commands."
        )
        buttons=[
            [InlineKeyboardButton("🧠 Commands", callback_data="sx_help")],
            [InlineKeyboardButton(
                "➕ Add to Group", url=f"https://t.me/{ADD_TO_GROUP_USERNAME}?startgroup=true")],
            [InlineKeyboardButton("💙 Support", url=SUPPORT_LINK)]
        ]
        await client.send_message(query.from_user.id, text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        pass


@ bot.on_message(filters.command("ping") & (filters.private | filters.group))
async def cmd_ping(client: Client, message: Message):
    try:
        t0=time.time()
        m=await message.reply_text("🏓 Pinging...")
        ms=int((time.time() - t0) * 1000)
        await m.edit_text(f"🩵 ShieldX Online!\n⚡ {ms}ms | Uptime: {int(time.time())}")
    except Exception:
        try:
            await message.reply_text("🩵 ShieldX Online!")
        except:
            pass


# ---------- STATUS (group-only) ----------
@ bot.on_message(filters.command("status") & filters.group)
async def cmd_status(client: Client, message: Message):
    try:
        cfg=ensure_chat(message.chat.id)
        on="ON" if cfg.get("clean_on") else "OFF"
        interval=cfg.get("clean_interval_minutes", 30)
        nsfw="Active" if cfg.get("nsfw_on", True) else "Off"
        # Watchdog always running on this process if started
        status_msg=(
            f"🧭 ShieldX Status:\n"
            f"🧹 Auto-clean: {on} (every {fmt_interval(interval)})\n"
            f"🔞 NSFW filter: {nsfw}\n"
            f"💤 Watchdog: Running"
        )
        await message.reply_text(status_msg, quote=False)
    except Exception:
        pass


# ============================================================
# 🧹 CLEAN SYSTEM — GLOBAL AUTO MEDIA CLEANER (ShieldX v4)
# ============================================================

# ---------- /clean (enable auto-clean globally) ----------
@ bot.on_message(filters.command("clean") & filters.group)
async def cmd_clean_on(client: Client, message: Message):
    """Enable automatic background cleaning for media in this group."""
    try:
        user_id=message.from_user.id if message.from_user else None
        if not user_id or not await is_admin_or_owner(client, message.chat.id, user_id):
            return  # ignore silently for non-admins

        cfg=ensure_chat(message.chat.id)
        cfg["clean_on"]=True
        if "clean_interval_minutes" not in cfg:
            cfg["clean_interval_minutes"]=30
        save_data(DATA)

        start_global_clean_task(client, message.chat.id)

        await message.reply_text(
            f"✅ Auto-clean enabled — every {cfg['clean_interval_minutes']} minutes media will be cleaned in background.",
            quote=True,
        )
    except Exception as e:
        print("cmd_clean_on error:", e)


# ---------- /delay (set custom clean interval globally) ----------
@ bot.on_message(filters.command("delay") & filters.group)
async def cmd_delay(client: Client, message: Message):
    """Set custom interval for auto-clean task in minutes."""
    try:
        user_id=message.from_user.id if message.from_user else None
        if not user_id or not await is_admin_or_owner(client, message.chat.id, user_id):
            return  # ignore silently

        parts=message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply_text("Usage: /delay <minutes> — e.g. `/delay 45`", quote=True)
            return

        try:
            minutes=int(parts[1].strip())
            if minutes < 1 or minutes > 1440:
                raise ValueError
        except Exception:
            await message.reply_text("⚠️ Please enter valid minutes between 1–1440.", quote=True)
            return

        cfg=ensure_chat(message.chat.id)
        cfg["clean_interval_minutes"]=minutes
        save_data(DATA)

        start_global_clean_task(client, message.chat.id)

        await message.reply_text(
            f"⏱ Auto-clean interval updated — every {minutes} minute(s) background cleaning will run.",
            quote=True,
        )
    except Exception as e:
        print("cmd_delay error:", e)


# ---------- /cleanall (manual full clean) ----------
@ bot.on_message(filters.command("cleanall") & filters.group)
async def cmd_cleanall(client: Client, message: Message):
    """Manually clean all recent media from last 24h."""
    try:
        user_id=message.from_user.id if message.from_user else None
        if not user_id or not await is_admin_or_owner(client, message.chat.id, user_id):
            return

        await message.reply_text("🧹 Starting deep clean... this may take a few minutes.", quote=True)

        deleted=await full_chat_clean(client, message.chat.id, hours=24)

        await message.reply_text(f"✅ Clean complete — removed {deleted} media items.", quote=True)
    except Exception as e:
        print("cmd_cleanall error:", e)


# ============================================================
# ⚙️ BACKGROUND CLEANER TASKS
# ============================================================

GLOBAL_CLEAN_TASKS={}

def start_global_clean_task(client: Client, chat_id: int):
    """Start or restart auto-clean loop for given chat."""
    if chat_id in GLOBAL_CLEAN_TASKS and not GLOBAL_CLEAN_TASKS[chat_id].done(
    ):
        return  # already running

    task=asyncio.create_task(global_clean_loop(client, chat_id))
    GLOBAL_CLEAN_TASKS[chat_id]=task


async def global_clean_loop(client: Client, chat_id: int):
    """Loop that runs periodically to clean all media messages."""
    while True:
        try:
            cfg=ensure_chat(chat_id)
            if not cfg.get("clean_on"):
                break

            minutes=cfg.get("clean_interval_minutes", 30)
            await full_chat_clean(client, chat_id, hours=24)
            await asyncio.sleep(minutes * 60)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"global_clean_loop error ({chat_id}):", e)
            await asyncio.sleep(60)


async def full_chat_clean(client: Client, chat_id: int, hours: int=24):
    """Delete all media messages within the last N hours."""
    deleted=0
    batch=[]
    try:
        cutoff=datetime.utcnow() - timedelta(hours=hours)
        async for msg in client.get_chat_history(chat_id, limit=5000):
            msg_date=msg.date if not (
    hasattr(
        msg.date,
        "tzinfo") and msg.date.tzinfo) else msg.date.replace(
            tzinfo=None)
            if msg_date < cutoff:
                break
            if msg.media:
                batch.append(msg.message_id)
                if len(batch) >= 20:
                    try:
                        await client.delete_messages(chat_id, batch)
                        deleted += len(batch)
                    except Exception:
                        for mid in batch:
                            try:
                                await client.delete_messages(chat_id, mid)
                                deleted += 1
                            except:
                                pass
                    batch.clear()

        if batch:
            try:
                await client.delete_messages(chat_id, batch)
                deleted += len(batch)
            except Exception:
                for mid in batch:
                    try:
                        await client.delete_messages(chat_id, mid)
                        deleted += 1
                    except:
                        pass

    except Exception as e:
        print("full_chat_clean error:", e)

    return deleted

# ========== NSFW / media handler (group-only) ==========
@ bot.on_message(filters.group & (filters.photo | filters.video |
                 filters.document | filters.animation | filters.sticker))
async def media_handler(client: Client, message: Message):
    # If no from_user (channel, anonymous), skip
    if message.from_user is None:
        return

    chat_id=message.chat.id
    user_id=message.from_user.id

    cfg=ensure_chat(chat_id)
    if not cfg.get("nsfw_on", True):
        # NSFW scanning disabled for this chat
        return

    # Download media to temp and run heuristic
    tmpdir=None
    path=None
    try:
        tmpdir=tempfile.mkdtemp()
        path=await client.download_media(message, file_name=os.path.join(tmpdir, "media"))
        if not path or not os.path.exists(path):
            return

        # Attempt local heuristic
        nsfw_flag=is_nsfw_local(path, skin_ratio_threshold=0.30)

        # cleanup downloaded file
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except:
            pass
        try:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass

        if not nsfw_flag:
            # Not NSFW — schedule for auto-clean if enabled
            if cfg.get("clean_on"):
                minutes=cfg.get("clean_interval_minutes", 30)
                delay=max(0, int(minutes) * 60)
                if delay == 0:
                    try:
                        await client.delete_messages(chat_id, message.message_id)
                    except:
                        pass
                else:
                    # schedule delete task
                    asyncio.create_task(
    schedule_delete(
        client,
        chat_id,
        message.message_id,
         delay))
            return

        # If NSFW detected:
        try:
            await client.delete_messages(chat_id, message.message_id)
        except:
            pass

        # Warn group (single warning message)
        try:
            await client.send_message(chat_id, "⚠️ NSFW content detected and removed. Please follow group rules.")
        except:
            pass

        # Update counters and mute if spammy (5 in 3 seconds)
        arr=prune_nsfw_counters(str(chat_id), str(user_id))
        arr.append(time.time())
        NSFW_COUNTERS[str(chat_id)][str(user_id)]=arr
        if len(arr) >= NSFW_SPAM_COUNT:
            # Mute permanently (best-effort)
            try:
                me=await client.get_me()
                bot_member=await client.get_chat_member(chat_id, me.id)
                if getattr(
    bot_member,
    "status",
    None) not in (
        "administrator",
         "creator"):
                    await client.send_message(chat_id, "⚠️ I need admin permissions to mute users automatically. Please promote me to admin.")
                    return
                until_ts=int(time.time()) + (10 * 365 * 24 *
                             3600)  # effectively permanent
                perm=types.ChatPermissions(
    can_send_messages=False,
    can_send_media_messages=False,
    can_send_other_messages=False,
     can_add_web_page_previews=False)
                # Respect configured action delay if any
                action_delay=cfg.get("action_delay_seconds", 0)
                if action_delay and action_delay > 0:
                    await asyncio.sleep(int(action_delay))
                await client.restrict_chat_member(chat_id, int(user_id), permissions=perm, until_date=until_ts)
                await client.send_message(chat_id, f"🚫 User muted for repeated NSFW violations.")
                # clear user's counter
                NSFW_COUNTERS.setdefault(
    str(chat_id), {}).pop(
        str(user_id), None)
            except Exception as e:
                print("nsfw mute failed:", e)
                try:
                    await client.send_message(chat_id, "⚠️ Failed to mute the user. Ensure I have admin rights.")
                except:
                    pass

    except Exception as e:
        print("media_handler error:", e)
        try:
            if path and os.path.exists(path):
                os.remove(path)
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass

async def schedule_delete(
    client: Client,
    chat_id: int,
    msg_id: int,
     delay: int):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, msg_id)
    except:
        pass

# ========== Auto-enable when added to group ==========
@ bot.on_message(filters.new_chat_members)
async def on_added_to_group(client: Client, message: Message):
    # When the bot is added to a group, check and set defaults for that chat
    try:
        for m in message.new_chat_members:
            if m.is_self:
                cfg=ensure_chat(message.chat.id)
                cfg["clean_on"]=True
                cfg["clean_interval_minutes"]=30
                cfg["nsfw_on"]=True
                save_data(DATA)
                start_clean_task_if_needed(client, message.chat.id)
                print(
                    f"✅ ShieldX initialized for new group: {message.chat.title} ({message.chat.id})")
                try:
                    await client.send_message(message.chat.id, f"🛡️ ShieldX initialized — Auto-clean: 30m | NSFW: ON")
                except:
                    pass
                break
    except Exception:
        pass

# ========== /lang (DM only, list-based selector) ==========
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# List of available languages
LANG_OPTIONS=[
    ("English", "en"), ("हिंदी", "hi"), ("Español", "es"), ("Français", "fr"),
    ("Deutsch", "de"), ("Русский", "ru"), ("العربية", "ar"), ("Português", "pt"),
    ("বাংলা", "bn"), ("日本語", "ja"), ("한국어", "ko"), ("Türkçe", "tr")
]

# Build inline keyboard (4 columns)
def build_lang_keyboard():
    buttons, row=[], []
    for i, (name, code) in enumerate(LANG_OPTIONS, start=1):
        row.append(InlineKeyboardButton(name, callback_data=f"sx_lang_{code}"))
        if i % 4 == 0:
            buttons.append(row)
            row=[]
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

@ bot.on_message(filters.command("lang") & filters.private)
async def cmd_lang(client, message):
    try:
        kb=build_lang_keyboard()
        await message.reply_text("🌐 Select your language:", reply_markup=kb, quote=True)
    except Exception as e:
        print("lang cmd error:", e)

@ bot.on_callback_query(filters.regex(r"^sx_lang_"))
async def cb_lang_select(client, query):
    try:
        await query.answer()
        code=query.data.replace("sx_lang_", "").strip().lower()
        name=next((n for n, c in LANG_OPTIONS if c == code), code)
        udata=DATA.setdefault("users", {})
        udata[str(query.from_user.id)]={"lang": code}
        save_data(DATA)
        await query.message.edit_text(f"🌐 Language set: {name} ({code})")
    except Exception as e:
        print("lang select error:", e)


# ========== Watchdog & background ==========
async def background_keepalive():
    while True:
        print("💤 Ping: ShieldX alive...")
        await asyncio.sleep(5)  # user wanted fast ping (5s) for visibility

async def watchdog_task(bot_client: Client):
    while True:
        try:
            if OWNER_ID:
                await bot_client.send_message(OWNER_ID, "🩵 ShieldX watchdog ping OK.", disable_notification=True)
        except Exception:
            pass
        await asyncio.sleep(1800)

# ========== Startup ==========
async def main():
    log_module_status()
    # Try to start pyrogram client with auto-retry
    backoff=1
    while True:
        try:
            await bot.start()
            print("✅ Pyrogram client started.")
            break
        except Exception as e:
            print("❌ Failed to start Pyrogram client:", e)
            print(f"⏳ Retrying in {backoff} seconds...")
            await asyncio.sleep(backoff)
            backoff=min(backoff * 2, 60)

    # start keepalive/watchdog/background
    asyncio.create_task(background_keepalive())
    asyncio.create_task(watchdog_task(bot))
    # start auto-clean tasks for chats that were enabled in persisted DATA
    try:
        for cid, cfg in DATA.items():
            # skip non-numeric keys
            if not cid.lstrip("-").isdigit():
                continue
            chat_id=int(cid)
            if cfg.get("clean_on"):
                start_clean_task_if_needed(bot, chat_id)
    except Exception as e:
        print("restore-clean-tasks error:", e)

    print("🩵 Background keepalive + watchdog running.")
    await asyncio.Event().wait()

# -------------------------
# SINGLE CLEAN STARTUP BLOCK
# (This replaces duplicate startup blocks and prevents double-start / freezes)
# -------------------------
if __name__ == "__main__":
    # choose a free port (try env PORT first, then search forward)
    try:
        chosen_port=find_free_port(PORT, search_range=100)
        if chosen_port != PORT:
            print(
                f"⚠️ Preferred port {PORT} busy — using fallback port {chosen_port}.")
        else:
            print(f"Using preferred port {PORT} for Flask keepalive.")
        PORT=chosen_port
    except Exception as e:
        print("Port selection error:", e)

    # start flask thread (daemon so it won't block shutdown)
    try:
        threading.Thread(target=run_flask, args=(PORT,), daemon=True).start()
        # keepalive thread uses blocking time.sleep loop to avoid freezing
        # input on ctrl+c
        threading.Thread(
    target=lambda: asyncio.run(
        background_keepalive()),
         daemon=True).start()
    except Exception as e:
        print("⚠️ Failed to start keepalive Flask thread:", e)

    # run main pyrogram startup loop (CTRL+C will stop asyncio.run cleanly)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
      print("Shutdown requested, exiting...")
