# abuse.py
import re
import asyncio
from pyrogram import Client, errors, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from helper.utils import increment_warning, reset_warnings

# ================= abusive words =================
ABUSIVE_WORDS = [
    # English
    "fuck", "shit", "bitch", "asshole", "idiot", "stupid", "dumb", "loser",
    "nigger", "cunt", "faggot", "dick", "pussy", "slut", "moron", "jerk",
    "bastard", "whore", "motherfucker", "douchebag", "scumbag", "retard",
    "wanker", "prick", "twat", "arsehole", "bullshit", "damn", "hell",
    "crap", "piss", "darn", "screw", "bloody", "bugger", "bollocks",
    
    # Hindi / Hinglish
    "bhosdike", "chutiya", "madarchod", "randi", "gandu", "lund", "chodu", 
    "harami", "kamina", "kutte", "saala", "haramzada", "bhenchod", "betichod",
    "chod", "jhant", "loda", "lodu", "randi", "motha", "badmaash",
    "behenchod", "bhosda", "gaand", "gaandu", "gand", "kutta", "kutti",
    "lauda", "lawda", "maderchod", "madherchod", "randwa", "suar", "tatti",
    "ullu", "chut", "choot", "chutia", "chutiye", "bhadwa", "bhosdi",
    "bhosad", "bosdike", "land", "lound", "nautank", "pagli", "pagal",
    "bewakoof", "gadha", "gadhe", "gadhi", "ullu", "murkh", "nalayak",
]

ABUSE_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in ABUSIVE_WORDS) + r")\b", flags=re.IGNORECASE)

# ================= normalize text =================
_LEET = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "@": "a", "$": "s", "5": "s", "7": "t"
})

def normalize_text(text: str) -> str:
    if not text:
        return ""
    s = text.lower().translate(_LEET)
    s = re.sub(r"(.)\1{2,}", r"\1\1", s)  # repeated chars
    s = re.sub(r"[\u200B-\u200F\uFEFF]", "", s)  # zero-width
    return s

# ================= abuse state per chat =================
ABUSE_STATE = {}  # chat_id -> True/False

def is_abuse_enabled(chat_id: int) -> bool:
    return ABUSE_STATE.get(chat_id, True)

def set_abuse_state(chat_id: int, state: bool):
    ABUSE_STATE[chat_id] = state

# ================= abuse handler =================
async def abuse_check_handler(client: Client, message: Message):
    if not is_abuse_enabled(message.chat.id):
        return

    if message.from_user is None or message.from_user.is_bot:
        return

    # COMMANDS BYPASS - yeh line add karo
    if message.text and message.text.startswith('/'):
        return

    text = message.text or message.caption
    if not text:
        return

    norm = normalize_text(text)
    if ABUSE_RE.search(norm):
        try:
            await message.delete()
        except errors.MessageDeleteForbidden:
            try:
                await message.reply_text("⚠️ I need delete permission to remove abusive messages.")
            except Exception:
                pass

        user_id = message.from_user.id
        full_name = f"{message.from_user.first_name}{(' ' + message.from_user.last_name) if message.from_user.last_name else ''}"
        mention = f"[{full_name}](tg://user?id={user_id})"

        # SABKE LIYE WARNING - no admin/allowlist check
        count = await increment_warning(message.chat.id, user_id)
        text_warn = (
            f"🚨 **Warning Issued** 🚨\n\n"
            f"👤 {mention} `[{user_id}]`\n"
            f"❌ Reason: abusive language detected\n"
            f"⚠️ Warning: {count}\n\n"
            "Please stop using abusive language."
        )

        try:
            await message.reply_text(text_warn, parse_mode="md")
        except Exception:
            pass

# ================= runtime update words =================
def add_abusive_word(word: str):
    w = word.lower().strip()
    if w and w not in ABUSIVE_WORDS:
        ABUSIVE_WORDS.append(w)
        _recompile()

def remove_abusive_word(word: str):
    w = word.lower().strip()
    if w in ABUSIVE_WORDS:
        ABUSIVE_WORDS.remove(w)
        _recompile()

def _recompile():
    global ABUSE_RE
    ABUSE_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in ABUSIVE_WORDS) + r")\b", flags=re.IGNORECASE)

# ================= abuse toggle command =================
@Client.on_message(filters.command("abuse") & filters.group)
async def abuse_toggle_cmd(client: Client, message: Message):
    if not message.from_user:
        return
    # only admins can toggle
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if not (member.status in ["administrator", "creator"]):
            await message.reply_text("❌ Only admins can toggle abuse filter.")
            return
    except:
        return

    if len(message.command) < 2:
        await message.reply_text("Usage: /abuse on | off")
        return

    arg = message.command[1].lower()
    if arg == "on":
        set_abuse_state(message.chat.id, True)
        await message.reply_text("✅ Abuse filter enabled.")
    elif arg == "off":
        set_abuse_state(message.chat.id, False)
        await message.reply_text("⚠️ Abuse filter disabled.")
    else:
        await message.reply_text("Usage: /abuse on | off")
