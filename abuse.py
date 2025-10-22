# helper/abuse.py
# =========================
# Abuse filter module (delete + warn only, no penalties)
# Admins and allowlisted users are NOT bypassed
# =========================

import re
import asyncio
from pyrogram import Client, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# ================= abusive words =================
ABUSIVE_WORDS = [
    # English
    "fuck", "shit", "bitch", "asshole", "idiot", "stupid", "dumb", "loser",
    "nigger", "cunt", "faggot", "dick", "pussy", "slut", "moron", "jerk",
    # Hindi / Hinglish
    "bhosdike", "chutiya", "madarchod", "randi", "gandu", "lund", "chodu", 
    "harami", "kamina", "kutte", "saala", "haramzada", "bhenchod", "betichod",
    "chod", "jhant", "loda", "lodu", "randi", "motha", "badmaash",
    # lowercase + capital variations will be normalized
]

ABUSE_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in ABUSIVE_WORDS) + r")\b", flags=re.IGNORECASE)

# ================= normalize text for leet/emoji =================
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

# ================= helper utils =================
from helper.utils import increment_warning, reset_warnings, add_allowlist, get_allowlist

# ================= abuse handler =================
async def abuse_check_handler(client: Client, message: Message):
    if message.from_user is None or message.from_user.is_bot:
        return

    # text or caption
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

        # increment warning count
        count = await increment_warning(message.chat.id, user_id)

        text_warn = (
            f"🚨 **Warning Issued** 🚨\n\n"
            f"👤 {mention} `[{user_id}]`\n"
            f"❌ Reason: abusive language detected\n"
            f"⚠️ Warning: {count}\n\n"
            "Please stop using abusive language."
        )

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌ Cancel Warning", callback_data=f"cancel_warn_{user_id}"),
                InlineKeyboardButton("✅ Allowlist", callback_data=f"allowlist_{user_id}")
            ],
            [InlineKeyboardButton("🗑️ Delete", callback_data="Delete")]
        ])

        try:
            await message.reply_text(text_warn, reply_markup=kb, parse_mode="md")
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
