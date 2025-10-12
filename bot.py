import os
import time
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from modules import filters as mod_filters
from modules import store

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/your_support_here")
DEFAULT_DELETE_MINUTES = int(os.getenv("DEFAULT_DELETE_MINUTES", "60"))

app = Client("shieldx", bot_token=BOT_TOKEN)

def dm_keyboard(username):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧹 Clean Media", callback_data="clean_on"),
         InlineKeyboardButton("🔞 NSFW Filter", callback_data="nsfw_on")],
        [InlineKeyboardButton("💬 Abuse Filter", callback_data="abuse_on"),
         InlineKeyboardButton("🕓 Clean Timer", callback_data="clean_time")],
        [InlineKeyboardButton("🌐 Language", callback_data="lang"),
         InlineKeyboardButton("🧩 Status", callback_data="ping")],
        [InlineKeyboardButton("🔁 Reload", callback_data="reload"),
         InlineKeyboardButton("⚙️ Help", callback_data="help")],
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{username}?startgroup=true"),
         InlineKeyboardButton("💬 Support", url=SUPPORT_LINK)]
    ])

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    username = (await client.get_me()).username
    text = (
        "🛡️ **ShieldX Protector AI Bot** 🤖\n\n"
        "Welcome! I'm your 24×7 group guardian — keeping chats clean, safe & smart.\n\n"
        "**Features:**\n"
        "• 🚫 NSFW auto-delete + strict protection\n"
        "• 🤬 Abuse filter & warnings\n"
        "• 🧹 Auto media cleaner (20m–24h; default 60m)\n"
        "• 👑 Owner/co-owner controls\n"
        "• 🌍 Multi-language support (Default: English 🇮🇳)\n"
    )
    await message.reply_text(text, reply_markup=dm_keyboard(username), disable_web_page_preview=True)

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message):
    text = (
        "**🧩 ShieldX Help Menu**\n\n"
        "**DM Commands:**\n"
        "• /start - Intro & menu\n"
        "• /help - Show help\n"
        "• /ping - Check latency\n"
        "• /reload - Owner only reload\n\n"
        "**Group Commands (admins only):**\n"
        "• /clean on|off|<time> — Auto-clean media\n"
        "• /cleanall — Delete all media\n"
        "• /abuse on|off — Enable/disable abuse filter\n"
        "• /nsfw on|off — Enable/disable NSFW filter\n"
        "• /lang — Change language\n"
    )
    await message.reply_text(text, disable_web_page_preview=True)

@app.on_message(filters.command("ping") & filters.private)
async def ping_cmd(client, message):
    t0 = time.time()
    await message.reply_text("⏳ Pinging...")
    t1 = time.time()
    await message.reply_text(f"🏓 Pong! Response: {int((t1 - t0) * 1000)} ms")

async def is_admin(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ("creator", "administrator")
    except:
        return False

@app.on_message(filters.command("clean") & filters.group)
async def clean_cmd(client, message):
    chat_id = message.chat.id
    args = message.text.split()
    store.ensure_chat(chat_id)

    if len(args) == 1:
        cfg = store.get_chat(chat_id)
        await message.reply_text(f"🧹 Auto-clean = {cfg.get('clean_on')} | Delete after {cfg.get('delete_minutes')}m")
        return

    op = args[1].lower()
    if op == "on":
        store.set_chat(chat_id, "clean_on", True)
        await message.reply_text("✅ Auto media cleaning enabled.")
    elif op == "off":
        store.set_chat(chat_id, "clean_on", False)
        await message.reply_text("🛑 Auto media cleaning disabled.")
    else:
        try:
            val = args[1]
            if val.endswith("m"): minutes = int(val[:-1])
            elif val.endswith("h"): minutes = int(val[:-1]) * 60
            else: minutes = int(val)
            if not (20 <= minutes <= 24*60): raise ValueError()
            store.set_chat(chat_id, "delete_minutes", minutes)
            await message.reply_text(f"🕓 Timer set to {minutes} minutes.")
        except:
            await message.reply_text("❌ Invalid time. Use e.g. 20m / 1h / 24h")

@app.on_message(filters.command("cleanall") & filters.group)
async def cleanall_cmd(client, message):
    user = message.from_user
    chat_id = message.chat.id
    if not await is_admin(client, chat_id, user.id):
        return await message.reply_text("⚠️ Only admins can use /cleanall.")
    await message.reply_text("🧹 Cleaning all media (2000 recent msgs)...")
    async for msg in client.iter_history(chat_id, limit=2000):
        if msg.media:
            try: await client.delete_messages(chat_id, msg.message_id)
            except: pass
    await message.reply_text("✅ All media deleted.")

@app.on_message(filters.command("reload") & filters.private)
async def reload_cmd(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("⚠️ Owner only.")
    await message.reply_text("♻️ Reloading ShieldX Bot...")
    os._exit(3)

@app.on_message(filters.group & ~filters.service)
async def monitor_group(client, message):
    chat_id = message.chat.id
    user = message.from_user
    store.ensure_chat(chat_id)
    cfg = store.get_chat(chat_id)
    is_admin_user = await is_admin(client, chat_id, user.id)

    if cfg.get("abuse_on", True) and message.text:
        if mod_filters.contains_abuse(message.text):
            await message.delete()
            store.add_warning(user.id)
            await message.reply_text("⚠️ Avoid abusive language. Warning issued.")
            return

    if cfg.get("nsfw_on", True):
        if message.text and mod_filters.contains_nsfw_text(message.text):
            await message.delete()
            await client.send_message(chat_id, "🚫 NSFW detected and removed.")
            return

    if cfg.get("clean_on", False) and message.media and not is_admin_user:
        asyncio.get_event_loop().create_task(schedule_delete(client, chat_id, message.message_id, cfg.get("delete_minutes", DEFAULT_DELETE_MINUTES) * 60))

async def schedule_delete(client, chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, message_id)
    except:
        pass

if __name__ == "__main__":
    store.get_store()
    app.run()
