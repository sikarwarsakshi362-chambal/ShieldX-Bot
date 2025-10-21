# -*- coding: utf-8 -*-
# ShieldX Protector Bot — Top Structure Strict Mode
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, ChatMember
import os
import time
import json
import tempfile
import re
import pytz
import datetime
import time
from pyrogram import idle 
import tempfile, shutil, asyncio, os

async def safe_download(message, file_path):
    # Unique temporary file
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=os.path.dirname(file_path), suffix=".temp") as tmp:
        temp_file = tmp.name

    await message.download(file_name=temp_file)

    for _ in range(5):  # 5 attempts
        try:
            shutil.move(temp_file, file_path)
            break
        except PermissionError:
            await asyncio.sleep(0.2)

    return file_path
# from central_admin import *
BLOCKED_STICKER_SETS = {
    "18plus_stickers",
    "nsfw_fun",
    "adult_memes",
    "explicit_pack",
    "hotgirls_pack",
    "xxx_stickers",
    "sexy_pack",
    "erotic_set"
}






# Manual Telegram time sync (Asia/Kolkata)
try:
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(ist)
    unix_time = int(time.mktime(now.timetuple()))
    time_diff = time.time() - unix_time
    if abs(time_diff) > 1:
        os.system('w32tm /resync')
        print("[TIME FORCE SYNC] Adjusted with Asia/Kolkata timezone.")
except Exception as e:
    print(f"[TIME FORCE SYNC ERROR] {e}")



# Config import
from modules.config import API_ID, API_HASH, BOT_TOKEN, ADD_TO_GROUP_USERNAME, SUPPORT_LINK, SESSION_FILE

# Optional image libs for local NSFW heuristic
try:
    import cv2
    import numpy as np
    from PIL import Image
except ImportError:
    cv2 = None
    np = None
    Image = None

# ================== Pyrogram Client ==================
# Strict: only ONE client instance
app = Client(
    "ShieldXFresh",      # naya session name
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# ================== PRINT BOT STARTING ==================
print("✅ ShieldX Protector Bot is starting...")

# ================== OTHER BOT HANDLERS (start/help/lang etc.) ==================

# ================== SESSION CLEANUP ==================
if os.path.exists(SESSION_FILE):
    try:
        os.remove(SESSION_FILE)
    except:
        pass

# ================== DATA STORAGE ==================
DATA_FILE = "data.json"
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            DATA = json.load(f)
        except:
            DATA = {}
else:
    DATA = {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
# ================== Temp / Memory-only session ==================
import tempfile

MEM_SESSION = os.path.join(tempfile.gettempdir(), "ShieldXTemp.session")
app = Client(
    MEM_SESSION,
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================== LANGUAGE OPTIONS ==================

# (rest of your bot code continues here...)
LANG_OPTIONS=[
    ("English", "en"), ("हिंदी", "hi"), ("Español", "es"), ("Français", "fr"),
    ("Deutsch", "de"), ("Русский", "ru"), ("العربية", "ar"), ("Português", "pt"),
    ("বাংলা", "bn"), ("日本語", "ja"), ("한국어", "ko"), ("Türkçe", "tr"),
    ("Italiano", "it"), ("Nederlands", "nl"), ("Polski", "pl"), ("Українська", "uk"),
    ("فارسی", "fa"), ("Svenska", "sv"), ("Norsk", "no"), ("Suomi", "fi"),
    ("ไทย", "th"), ("Bahasa Indonesia", "id"), ("Bahasa Melayu", "ms"), ("Tiếng Việt", "vi"),
    ("हिंदी (देवनागरी)", "hi-IN"), ("中文 (简体)", "zh-CN"), ("中文 (繁體)", "zh-TW"), ("Ελληνικά", "el"),
    ("עברית", "he"), ("Català", "ca")
]

def build_lang_keyboard():
    buttons, row = [], []
    for i, (name, code) in enumerate(LANG_OPTIONS, start=1):
        row.append(InlineKeyboardButton(name, callback_data=f"sx_lang_{code}"))
        if i % 4 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
import os, json
from modules.config import ADD_TO_GROUP_USERNAME, SUPPORT_LINK, SESSION_FILE

# ================= SESSION CLEANUP =================
if os.path.exists(SESSION_FILE):
    try:
        os.remove(SESSION_FILE)
    except:
        pass
# ================= CONFIG =================
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

ADD_TO_GROUP_USERNAME = "shieldxprotector_bot"
SUPPORT_LINK = "https://t.me/your_support_chat"

# Store last DM message per user to prevent spam
user_last_dm = {}

# ================= Helper: send single DM =================
async def send_single_dm(client, user_id, text, buttons, user_key):
    try:
        last_msg = user_last_dm.get(user_key)
        if last_msg:
            try: await last_msg.delete()
            except: pass
        msg = await client.send_message(user_id, text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        user_last_dm[user_key] = msg
        return msg
    except Exception as e:
        print(f"send_single_dm error: {e}")
        return None

# ================= DM /start =================
@app.on_message(filters.command("start") & filters.private)
async def cmd_start_dm(client: Client, message: Message):
    me = await client.get_me()
    bot_name = me.first_name
    user_name = message.from_user.first_name if message.from_user else "User"
    user_mention = message.from_user.mention if message.from_user else "there"

    text = (
        f"🛡️ **{bot_name} — Your Multi-Layer Telegram Guardian**\n\n"
        f"Hey {user_mention} 👋\n"
        f"I'm **{bot_name}**, here to protect your Telegram world — smartly and silently.\n\n"
        "✨ Here's what I can do:\n"
        "• Auto-clean photos, videos, and documents (custom intervals)\n"
        "• Detect and delete NSFW instantly (AI-powered)\n"
        "• Smart spam-mute for repeat offenders\n"
        "• Keepalive watchdog ensures I never sleep 😴\n\n"
        f"Glad to meet you, **{user_name}**! Use the buttons below to explore features or add me to your group 🚀"
    )

    buttons = [
        [InlineKeyboardButton("🧠 Commands", callback_data="sx_help_menu"),
         InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{ADD_TO_GROUP_USERNAME}?startgroup=true")],
        [InlineKeyboardButton("💙 Support", url=SUPPORT_LINK),
         InlineKeyboardButton("🌐 Language", callback_data="sx_lang_menu")]
    ]

    await send_single_dm(client, message.from_user.id, text, buttons, message.from_user.id)

# ================= Commands Menu =================
@app.on_callback_query(filters.regex(r"^sx_help_menu$"))
async def cb_commands(client: Client, query: CallbackQuery):
    await query.answer()
    cmds_text = (
        "🧠 **ShieldX Commands:**\n\n"
        "/start - Show start message\n"
        "/ping - Check bot status\n"
        "/lang - Change language\n"
        "… aur baki commands yaha …"
    )
    buttons = [[InlineKeyboardButton("🔙 Back", callback_data="sx_back:start")]]
    await send_single_dm(client, query.from_user.id, cmds_text, buttons, query.from_user.id)

# ================= Language Menu =================
@app.on_callback_query(filters.regex(r"^sx_lang_menu$"))
async def cb_language(client: Client, query: CallbackQuery):
    await query.answer()
    lang_text = "🌐 **Select Language:**"
    buttons = [
        [InlineKeyboardButton("English", callback_data="sx_lang:en"),
         InlineKeyboardButton("Hindi", callback_data="sx_lang:hi")],
        [InlineKeyboardButton("🔙 Back", callback_data="sx_back:start")]
    ]
    await send_single_dm(client, query.from_user.id, lang_text, buttons, query.from_user.id)

# ================= Language Select =================
@app.on_callback_query(filters.regex(r"^sx_lang:"))
async def cb_lang_select(client: Client, query: CallbackQuery):
    await query.answer()
    selected = query.data.split(":")[1]
    await query.message.edit_text(f"🌐 Language set to: {selected.upper()}")
    buttons = [[InlineKeyboardButton("🔙 Back", callback_data="sx_back:start")]]
    await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))

# ================= Back Button =================
@app.on_callback_query(filters.regex(r"^sx_back:start$"))
async def cb_back_start(client: Client, query: CallbackQuery):
    await query.answer()
    try: await query.message.delete()
    except: pass
    await cmd_start_dm(client, query.message)

# ================== /ping ==================
@app.on_message(filters.command("ping") & (filters.private | filters.group))
async def cmd_ping(client: Client, message: Message):
    try:
        t0 = time.time()
        m = await message.reply_text("🏓 Pinging...")
        ms = int((time.time() - t0) * 1000)
        await m.edit_text(f"🩵 ShieldX Online!\n⚡ {ms}ms | Uptime: {int(time.time())}")
    except Exception:
        try:
            await message.reply_text("🩵 ShieldX Online!")
        except:
            pass

# ================= OTHER COMMANDS (CLEAN, DELAY, NSFW, ETC.) =================
# --- Paste your existing commands here exactly as they were ---
# Example:
@app.on_message(filters.command("clean") & filters.private)
async def cmd_clean(client: Client, message: Message):
    # original clean logic
    pass

@app.on_message(filters.command("delay") & filters.private)
async def cmd_delay(client: Client, message: Message):
    # original delay logic
    pass

@app.on_message(filters.command("nsfw") & filters.private)
async def cmd_nsfw(client: Client, message: Message):
    # original nsfw logic
    pass

# ================= GC /start =================
@app.on_message(filters.command("start") & filters.group)
async def cmd_start_gc(client: Client, message: Message):
    try:
        me = await client.get_me()
        bot_name = me.first_name

        # Headline-style short message
        text = (
            f"🛡️ **{bot_name} Protection Active!**\n\n"
            "Hey admins, ShieldX is guarding this group 👀\n"
            "Media cleanup, spam defense, and NSFW detection are live.\n\n"
            "Click '📘 DM' below to receive full guide in DM."
        )

        buttons = [
            [
                InlineKeyboardButton("➕ Add to Group", url="https://t.me/shieldxprotector_bot?startgroup=true"),
                InlineKeyboardButton("📘 DM", callback_data="sx_help_dm")
            ]
        ]

        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), quote=False)
    except Exception as e:
        print(f"GC /start error: {e}")

# ================= GC → DM full headline =================
@app.on_callback_query(filters.regex(r"^sx_help_dm$"))
async def cb_gc_help_dm(client: Client, query):
    await query.answer()
    try:
        if query.from_user:
            me = await client.get_me()
            bot_name = me.first_name
            user_name = query.from_user.first_name if query.from_user else "User"
            user_mention = query.from_user.mention if query.from_user else "there"

            # Headline-style full DM message
            text = (
                f"🛡️ **{bot_name} — Your Multi-Layer Telegram Guardian**\n\n"
                f"Hey {user_mention} 👋\n"
                f"I'm **{bot_name}**, here to protect your Telegram world — smartly and silently.\n\n"
                "✨ Here's what I can do:\n"
                "• Auto-clean photos, videos, and documents (custom intervals)\n"
                "• Detect and delete NSFW instantly (AI-powered)\n"
                "• Smart spam-mute for repeat offenders\n"
                "• Keepalive watchdog ensures I never sleep 😴\n\n"
                f"Glad to meet you, **{user_name}**! Use the buttons below to explore features or add me to your group 🚀"
            )

            buttons = [
                [InlineKeyboardButton("🧠 Commands", callback_data="sx_help_menu"),
                 InlineKeyboardButton("➕ Add to Group", url="https://t.me/shieldxprotector_bot?startgroup=true")],
                [InlineKeyboardButton("💙 Support", url=SUPPORT_LINK),
                 InlineKeyboardButton("🌐 Language", callback_data="sx_lang_menu")]
            ]

            await client.send_message(
                query.from_user.id,
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True
            )

    except Exception as e:
        print(f"GC → DM error: {e}")

# =============================== IMPORTS ===============================
import os, asyncio, tempfile, shutil, time
from PIL import Image
import cv2
from nudenet import NudeDetector
from pyrogram import filters

# =============================== BOT & DETECTOR INIT ===============================
# assume `app` is already created somewhere
detector = NudeDetector()  # single instance

# =============================== SAFE DOWNLOAD ===============================
async def safe_download(message, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=os.path.dirname(file_path), suffix=".temp") as tmp:
        temp_file = tmp.name
    await message.download(file_name=temp_file)
    for _ in range(5):
        try:
            shutil.move(temp_file, file_path)
            break
        except PermissionError:
            await asyncio.sleep(0.2)
    return file_path

# =============================== SAFE DELETE (instant delete, optional warning) ===============================
async def safe_delete(message, file_path=None, warn_user=False):
    try:
        if message.chat.type in ("group", "supergroup"):
            bot_id = (await message._client.get_me()).id
            try:
                bot_member = await message._client.get_chat_member(message.chat.id, bot_id)
                can_delete = getattr(bot_member, "privileges", None) and getattr(bot_member.privileges, "can_delete_messages", False)
            except Exception:
                can_delete = False
            if not can_delete:
                return
        if warn_user:
            warn_msg = await message.reply_text("⚠️ NSFW / Adult content detected! Message will be deleted in 30 seconds.")
            await asyncio.sleep(30)
            try: await warn_msg.delete()
            except: pass
        await message.delete()
        if file_path and os.path.exists(file_path):
            async def _rm(p):
                for _ in range(3):
                    try:
                        os.remove(p)
                        break
                    except PermissionError:
                        await asyncio.sleep(0.05)
                    except Exception:
                        break
            asyncio.create_task(_rm(file_path))
    except Exception:
        pass

# =============================== CONVERT WEBP -> PNG ===============================
def convert_webp_to_png(file_path):
    if not file_path or not os.path.exists(file_path):
        return None
    if file_path.lower().endswith(".webp"):
        try:
            img = Image.open(file_path).convert("RGB")
            new_path = file_path + ".png"
            img.save(new_path, "PNG")
            return new_path
        except Exception:
            return None
    return file_path

# =============================== NSFW PACK FILTERS ===============================
ADULT_PACK_KEYWORDS = [
    "18plus", "porn", "sex", "xxx", "xnxx", "fuck", "bitch", "hotgirl", "adult", "erotic", "nude", "sexy"
]

# =============================== STICKER / MEDIA HANDLER ===============================
@app.on_message(filters.group & (filters.photo | filters.video | filters.document | filters.sticker | filters.animation))
async def gc_handler(client, message):
    try:
        # filename
        if message.sticker:
            fname = f"{message.sticker.file_unique_id}.webp"
            set_name = message.sticker.set_name.lower() if message.sticker.set_name else ""
        elif message.animation:
            fname = f"{message.animation.file_unique_id}.webp"
            set_name = ""
        elif message.photo:
            mid = getattr(message, "message_id", int(time.time()*1000))
            fname = f"photo_{mid}.jpg"
            set_name = ""
        elif message.document:
            fname = getattr(message.document, "file_name", f"doc_{int(time.time()*1000)}")
            set_name = ""
        else:
            fname = f"media_{int(time.time()*1000)}"
            set_name = ""

        save_path = os.path.join("downloads", fname)
        file_path = await safe_download(message, save_path)
        ext = os.path.splitext(file_path)[1].lower()
        is_image = ext in [".jpg", ".jpeg", ".png", ".webp"]
        conv_file = convert_webp_to_png(file_path) if ext==".webp" else file_path

        # Check adult pack keywords first
        if any(keyword in set_name for keyword in ADULT_PACK_KEYWORDS):
            await safe_delete(message, file_path, warn_user=False)
            print(f"[NSFW BLOCKED SET] Deleted from pack: {set_name}")
            return

        # AI detection
        if conv_file and os.path.exists(conv_file):
            try:
                result = await asyncio.to_thread(detector.detect, conv_file)
                is_nsfw = any(item.get("score",0) > 0.2 for item in result)
                if is_nsfw:
                    await safe_delete(message, file_path, warn_user=False)
                    try: os.remove(conv_file)
                    except: pass
                    print(f"[NSFW DETECTED] Deleted: {file_path}")
            except Exception:
                pass

    except Exception as e:
        print(f"[GC HANDLER ERROR] {e}")

# =============================== GC WORKER (optional queue system for large groups) ===============================
gc_queue = asyncio.Queue()

async def gc_worker():
    while True:
        client, message, file_path, conv_file, is_image = await gc_queue.get()
        try:
            # For instant delete, logic is already handled in gc_handler
            pass
        finally:
            gc_queue.task_done()


# =============================== ABUSE DETECTION ===============================
ABUSE_KEYWORDS = [
    "chutiya", "chutiyA", "bhosdike", "bhosdikE", "lund", "lund", "gandu", "gandu",
    "randi", "randi", "kutti", "kutTi", "bsdk", "Bsdk", "bahanchod", "bahanchOd", "kutta", "kutta",
    "madar", "Madar", "madarchod", "Madarchod", "madarjat", "Madarjat", "sala", "sala",
    "harami", "bhadve", "behenchod", "bhenchod", "bhen ka", "bhen ka", "jhatu", "gand",
    "lodu", "choot", "choot ka", "lund ka", "mc", "bc", "lundu", "jeeja", "tharki",
    "chhinal", "bewakoof", "kamina", "saala", "londa", "lond", "ludiya",
    "sex", "fuck", "bitch", "bastard", "ass", "cock", "dick", "boobs",
    "slut", "anal", "cum", "naked", "porn", "xxx", "tits", "pussy",
    "fuckme", "masturbate", "whore", "prostitute", "retard", "idiot", "jerk",
    "shit", "damn", "crap"
]

# Strict detection: ignore case aur short variations
ABUSE_KEYWORDS = [word.lower() for word in ABUSE_KEYWORDS]

def is_abuse(text):
    text_lower = text.lower()
    for word in ABUSE_KEYWORDS:
        if word in text_lower:
            return True
    return False

ABUSE_STATUS = {}  # chat_id: True/False

@app.on_message(filters.group & filters.text)
async def abuse_auto_delete(client: Client, message: Message):
    chat_id = message.chat.id
    from_user_id = message.from_user.id if message.from_user else None

    if not ABUSE_STATUS.get(chat_id, True):
        return

    chat_member = await client.get_chat_member(chat_id, from_user_id)
    if chat_member.status in ["administrator", "creator"]:
        return

    text_lower = message.text.lower()
    if any(word in text_lower for word in ABUSE_KEYWORDS):

        async def delete_warn():
            try:
                bot_member = await client.get_chat_member(chat_id, (await client.get_me()).id)
                if not getattr(bot_member, "privileges", None) or not getattr(bot_member.privileges, "can_delete_messages", False):
                    return

                await message.delete()
                warn = await message.reply_text(
                    f"⚠️ {message.from_user.mention} Abusive content removed!",
                    quote=True
                )
                await asyncio.sleep(5)
                await warn.delete()
            except Exception as e:
                print(f"[ABUSE Handler] {e}")

        asyncio.create_task(delete_warn())
# --------- /abuse COMMAND ----------
from pyrogram import Client, filters
from pyrogram.types import Message

# Group-wise abuse filter status
ABUSE_STATUS = {}

@app.on_message(filters.command("abuse") & filters.group)
async def cmd_abuse_toggle(client: Client, message: Message):
    from_user = message.from_user
    chat_id = message.chat.id

    # Admin/creator check
    try:
        member = await client.get_chat_member(chat_id, from_user.id)
        if member.status not in ["creator", "administrator"]:
            await message.reply("❌ Only admins/creator can toggle abuse filter!")
            return
    except Exception:
        await message.reply("❌ Unable to check admin status.")
        return

    # Command argument parsing
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = "ON" if ABUSE_STATUS.get(chat_id, True) else "OFF"
        await message.reply(
            f"⚡ Abuse filter current status: {current}\nUse `/abuse on` or `/abuse off`"
        )
        return

    option = args[1].strip().lower()
    if option in ["on", "enable"]:
        ABUSE_STATUS[chat_id] = True
        await message.reply("✅ Abuse filter enabled for this group.")
    elif option in ["off", "disable"]:
        ABUSE_STATUS[chat_id] = False
        await message.reply("❌ Abuse filter disabled for this group.")
    else:
        await message.reply("⚠️ Invalid option! Use `/abuse on` or `/abuse off`")


# =============================== CLEAN MEDIA GC ===============================
import os, asyncio, time
from pyrogram import filters

CLEAN_BATCH_SIZE = 50       # ek batch me delete items
CLEAN_BATCH_DELAY = 2       # sec delay between batches
CLEAN_TARGET_MINUTES = 2    # kitne minute purana media delete hoga
DOWNLOADS_DIR = "downloads"

clean_gc_queue = asyncio.Queue()

# ====== Safe delete with permission check for groups ======
async def clean_safe_delete(client, message=None, file_path=None):
    try:
        # Agar group/supergroup me hai to permission check
        if message and message.chat.type in ("group", "supergroup"):
            bot_id = (await client.get_me()).id
            try:
                bot_member = await client.get_chat_member(message.chat.id, bot_id)
                can_delete = getattr(bot_member, "privileges", None) and getattr(bot_member.privileges, "can_delete_messages", False)
            except Exception:
                can_delete = False
            if not can_delete:
                return

        # Delete Telegram message agar diya ho
        if message:
            try:
                await message.delete()
            except:
                pass

        # Delete file from disk
        if file_path and os.path.exists(file_path):
            try: os.remove(file_path)
            except:
                pass
    except:
        pass

from telebot import TeleBot
import threading
import time

# ==========================
# ShieldX Bot token
# ==========================
bot = TeleBot("SHIELDX_BOT_TOKEN")  # Replace with your existing ShieldX token

# ==========================
# Global admins
# ==========================
GLOBAL_ADMINS = [123456789, 987654321]  # Replace with your IDs

# ==========================
# Flags & Settings
# ==========================
clean_enabled = True
clean_delay = 30  # default 30 minutes
GROUP_IDS = [-1001234567890]  # Replace with your group IDs
BATCH_SIZE = 50

# ==========================
# Admin check
# ==========================
def is_global_admin(user_id):
    return user_id in GLOBAL_ADMINS

# ==========================
# /clean_on
# ==========================
@bot.message_handler(commands=['clean_on'])
def clean_on(message):
    global clean_enabled
    if not is_global_admin(message.from_user.id):
        return
    clean_enabled = True

# ==========================
# /clean_off
# ==========================
@bot.message_handler(commands=['clean_off'])
def clean_off(message):
    global clean_enabled
    if not is_global_admin(message.from_user.id):
        return
    clean_enabled = False

# ==========================
# /cleannow
# ==========================
@bot.message_handler(commands=['cleannow'])
def clean_now(message):
    if not is_global_admin(message.from_user.id):
        return
    batch_delete_all_groups([message.chat.id])

# ==========================
# /delay XX (20m–24h)
# ==========================
@bot.message_handler(commands=['delay'])
def set_delay(message):
    global clean_delay
    if not is_global_admin(message.from_user.id):
        return
    try:
        args = message.text.split()[1]
        if args.endswith('m'):
            minutes = int(args[:-1])
        elif args.endswith('h'):
            minutes = int(args[:-1]) * 60
        else:
            return
        clean_delay = max(20, min(minutes, 1440))
    except:
        return

# ==========================
# Batch-wise media deletion for a single chat
# ==========================
def delete_old_media(chat_id):
    messages_to_delete = []
    now = time.time()
    cutoff = now - 24*3600
    try:
        for msg in bot.get_chat(chat_id).get_history(limit=500):
            if msg.date.timestamp() >= cutoff and msg.content_type in ['photo','video','document','sticker']:
                messages_to_delete.append(msg.message_id)
                if len(messages_to_delete) >= BATCH_SIZE:
                    for mid in messages_to_delete:
                        try: bot.delete_message(chat_id, mid)
                        except: pass
                    messages_to_delete = []
                    time.sleep(1)
        for mid in messages_to_delete:
            try: bot.delete_message(chat_id, mid)
            except: pass
    except:
        pass

# ==========================
# Batch-wise delete for multiple groups
# ==========================
def batch_delete_all_groups(group_list):
    for gid in group_list:
        delete_old_media(gid)

# ==========================
# Scheduled automatic cleanup
# ==========================
def scheduled_cleanup():
    while True:
        if clean_enabled:
            batch_delete_all_groups(GROUP_IDS)
        time.sleep(clean_delay * 60)

# ==========================
# Start cleanup thread
# ==========================
threading.Thread(target=scheduled_cleanup, daemon=True).start()

# ==========================
# Start the bot
# ==========================
bot.polling(none_stop=True)

# ====== Start Clean GC ======
async def start_bot():
    await app.start()                  # client start
    print("✅ ShieldX GC worker running...")
    # agar start_clean_gc() call karni hai to yahan karo, warna remove
    # asyncio.create_task(clean_gc_worker())
    from pyrogram import idle
    await idle()


if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(start_bot())


