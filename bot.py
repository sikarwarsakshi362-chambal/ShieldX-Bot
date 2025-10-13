import asyncio
import os
import threading
from flask import Flask
from pyrogram import Client, filters, types
from pyrogram.errors import RPCError
from dotenv import load_dotenv

# === LOAD ENV ===
load_dotenv()
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# === TELEGRAM BOT ===
app = Client("ShieldXBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
config = {"clean_on": False, "delete_minutes": 0}

# === START COMMAND ===
@app.on_message(filters.command("start", prefixes=["/", "!"]))
async def start_cmd(client, message):
    text = (
        "🩵 **Hey! I'm ShieldX**\n"
        "Your personal auto-clean assistant.\n\n"
        "🧹 I help you keep chats clean — auto delete media & spam.\n"
        "⚙️ Add me to your group and make me admin.\n\n"
        "👇 Use the buttons below to explore!"
    )
    buttons = [
        [
            types.InlineKeyboardButton("🧹 Add to Group", url="https://t.me/ShieldX_CleanerBot?startgroup=new"),
        ],
        [
            types.InlineKeyboardButton("📜 Commands", callback_data="help_menu"),
            types.InlineKeyboardButton("💠 About", callback_data="about_menu"),
        ]
    ]
    reply_markup = types.InlineKeyboardMarkup(buttons)
    await message.reply_text(text, reply_markup=reply_markup, disable_web_page_preview=True)

# === HELP COMMAND ===
@app.on_message(filters.command("help", prefixes=["/", "!"]))
async def help_cmd(client, message):
    await show_help(message)

# === CALLBACK HANDLERS ===
@app.on_callback_query()
async def callback_query(client, query):
    if query.data == "help_menu":
        await show_help(query.message, edit=True)
    elif query.data == "about_menu":
        text = (
            "💠 **About ShieldX**\n\n"
            "• Language: Python (Pyrogram)\n"
            "• Function: Auto-clean media & spam\n"
            "• Speed: Fast, secure & reliable\n\n"
            "🧠 Developed with 💙 for smart Telegram management."
        )
        back_btn = types.InlineKeyboardMarkup(
            [[types.InlineKeyboardButton("⬅️ Back", callback_data="help_menu")]]
        )
        await query.message.edit_text(text, reply_markup=back_btn)
        await query.answer()

async def show_help(message, edit=False):
    text = (
        "✨ **ShieldX Commands**\n\n"
        "🧹 `/clean [minutes]` → Enable auto-clean (default 60m)\n"
        "🚫 `/clean off` → Turn off auto-clean\n"
        "💣 `/cleanall` → Delete all media (for group owner/admins)\n\n"
        "⚡ Clean. Silent. Powerful."
    )
    back_btn = types.InlineKeyboardMarkup(
        [[types.InlineKeyboardButton("🏠 Home", callback_data="start_home")]]
    )
    if edit:
        await message.edit_text(text, reply_markup=back_btn)
    else:
        await message.reply_text(text, reply_markup=back_btn)
        
@app.on_callback_query(filters.regex("start_home"))
async def home_cb(client, query):
    await start_cmd(client, query.message)
    await query.answer()

# === CLEAN COMMAND ===
@app.on_message(filters.group & filters.command("clean", prefixes=["/", "!"]))
async def clean_toggle(client, message):
    member = await app.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        return

    args = message.text.split()
    if len(args) > 1 and args[1].lower() == "off":
        config["clean_on"] = False
        await message.reply_text("🧹 Auto-clean **disabled.**")
        return

    if len(args) > 1:
        try:
            mins = int(args[1])
            if 20 <= mins <= 1440:
                config["delete_minutes"] = mins
                config["clean_on"] = True
                await message.reply_text(f"✅ Auto-clean set for **{mins}m.**")
                return
        except:
            pass

    config["clean_on"] = True
    config["delete_minutes"] = 60
    await message.reply_text("✅ Auto-clean **enabled** (default 60m).")

# === CLEANALL COMMAND ===
@app.on_message(filters.group & filters.command("cleanall", prefixes=["/", "!"]))
async def clean_all(client, message):
    member = await app.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ["creator", "administrator"]:
        return

    await message.reply_text("🧨 Cleaning up media...")
    async for msg in app.get_chat_history(message.chat.id, limit=300):
        if msg.media:
            try:
                await msg.delete()
            except RPCError:
                pass
    await message.reply_text("✅ All media cleaned successfully!")

# === AUTO DELETE MEDIA ===
@app.on_message(filters.group)
async def auto_delete_media(client, message):
    if not config.get("clean_on"):
        return
    if message.media:
        delay = config.get("delete_minutes", 0) * 60
        if delay == 0:
            try:
                await message.delete()
            except:
                pass
        else:
            asyncio.create_task(schedule_delete(client, message.chat.id, message.id, delay))

async def schedule_delete(client, chat_id, msg_id, delay):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, msg_id)
    except:
        pass

# === FLASK KEEP-ALIVE ===
flask_app = Flas_
