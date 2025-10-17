from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
import os, time, json

# ========== DATA STORAGE ==========
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

# ========== ENVIRONMENT ==========
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
ADD_TO_GROUP_USERNAME = os.getenv("ADD_TO_GROUP_USERNAME") or "shieldprotector_bot"
SUPPORT_LINK = os.getenv("SUPPORT_LINK") or "https://t.me/+yGiJaSdHDoRlN2Zl"

app = Client("ShieldXTestBot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# ========== LANGUAGE OPTIONS ==========
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
    buttons, row=[], []
    for i, (name, code) in enumerate(LANG_OPTIONS, start=1):
        row.append(InlineKeyboardButton(name, callback_data=f"sx_lang_{code}"))
        if i % 4 == 0:
            buttons.append(row)
            row=[]
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

# ========== /start ==========
@app.on_message(filters.command("start") & (filters.private | filters.group))
async def cmd_start(client: Client, message: Message):
    try:
        me = await client.get_me()
        bot_name = me.first_name
        user_name = message.from_user.first_name if message.from_user else "User"
        user_mention = message.from_user.mention if message.from_user else "there"

        if message.chat.type == "private":
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
                [
                    InlineKeyboardButton("🧠 Commands", callback_data="sx_help"),
                    InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{ADD_TO_GROUP_USERNAME}?startgroup=true")
                ],
                [
                    InlineKeyboardButton("💙 Support", url=SUPPORT_LINK),
                    InlineKeyboardButton("🌐 Language", callback_data="sx_lang_menu")
                ]
            ]
            await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        else:
            group_text = (
                f"🛡️ **{bot_name} Protection Active!**\n\n"
                f"Hey admins, {bot_name} is now guarding this group 👀\n"
                "Media cleanup, spam defense, and NSFW detection are live.\n\n"
                "Use /help to view commands or /status to check protection settings."
            )
            group_buttons = InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{ADD_TO_GROUP_USERNAME}?startgroup=true"),
                    InlineKeyboardButton("💙 Support", url=SUPPORT_LINK),
                    InlineKeyboardButton("📘 Help Menu", callback_data="sx_help")
                ]]
            )
            await message.reply_text(group_text, reply_markup=group_buttons, quote=False)
    except Exception as e:
        print(f"/start error: {e}")

# ========== /help ==========
@app.on_callback_query(filters.regex(r"^sx_help$"))
async def cb_help(client: Client, query):
    try:
        await query.answer()
        me = await client.get_me()
        bot_name = me.first_name
        help_text = (
            f"💡 **{bot_name} Commands & Usage Guide**\n\n"
            "🧹 /clean on — enable auto media cleanup (default 30m)\n"
            "🧼 /delay <20m|1h|2h> — set custom cleanup interval\n"
            "🛑 /clean off — disable auto-clean\n"
            "🧹 /cleanall — delete media from last 24h (admin only)\n"
            "🔞 NSFW — automatic detection & delete; 5 NSFW posts in 3s = mute\n"
            "🧭 /status — current protection status (group-only)\n"
            "🌐 /lang <code> — change language for this chat (DM only)\n\n"
            f"Support: {SUPPORT_LINK}"
        )
        buttons = [
            [InlineKeyboardButton("🔙 Back to Start", callback_data="sx_start")],
            [
                InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{ADD_TO_GROUP_USERNAME}?startgroup=true"),
                InlineKeyboardButton("💙 Support", url=SUPPORT_LINK)
            ]
        ]
        try:
            await query.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        except:
            await client.send_message(query.from_user.id, help_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    except Exception as e:
        print(f"Help callback error: {e}")

# ========== Back to Start ==========
@app.on_callback_query(filters.regex(r"^sx_start$"))
async def cb_start(client: Client, query):
    try:
        await query.answer()
        await cmd_start(client, query.message)
    except Exception as e:
        print(f"Back to start error: {e}")

# ========== /ping ==========
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

# ========== /lang menu ==========
@app.on_callback_query(filters.regex(r"^sx_lang_menu$"))
async def cb_lang_menu(client, query):
    try:
        await query.answer()
        kb = build_lang_keyboard()
        await query.message.edit_text("🌐 Select your language:", reply_markup=kb)
    except Exception as e:
        print("lang menu error:", e)

# ========== /lang select ==========
@app.on_callback_query(filters.regex(r"^sx_lang_"))
async def cb_lang_select(client, query):
    try:
        await query.answer()
        code = query.data.replace("sx_lang_", "").strip().lower()
        name = next((n for n, c in LANG_OPTIONS if c == code), code)
        udata = DATA.setdefault("users", {})
        udata[str(query.from_user.id)] = {"lang": code}
        save_data(DATA)
        await query.message.edit_text(f"🌐 Language set: {name} ({code})")
    except Exception as e:
        print("lang select error:", e)

# ========== Run Bot ==========
print("✅ ShieldX Test Bot is starting...")
app.run()
