import asyncio
import os
import threading
from flask import Flask
from pyrogram import Client, filters
from dotenv import load_dotenv

# === LOAD ENV ===
load_dotenv()
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# === TELEGRAM BOT SETUP ===
app = Client("ShieldXBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# === SETTINGS ===
DEFAULT_DELETE_MINUTES = 60
CO_OWNER_IDS = [123456789, 987654321]  # 🔹 Apne co-owner Telegram IDs daal do

# === STORAGE ===
config = {"clean_on": False, "delete_minutes": DEFAULT_DELETE_MINUTES}


# 🧹 CLEAN COMMAND (Admins)
@app.on_message(filters.command("clean", prefixes=["/", "!"]))
async def clean_toggle(client, message):
    user_id = message.from_user.id

    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        is_admin = member.status in ["administrator", "creator"]
    except:
        is_admin = False

    if not is_admin:
        await message.reply("❌ केवल group admins इस command का उपयोग कर सकते हैं।")
        return

    args = message.text.split()

    # OFF Command
    if len(args) > 1 and args[1].lower() == "off":
        config["clean_on"] = False
        await message.reply("🧹 Auto-clean बंद कर दिया गया।")
        return

    # Custom Time Command
    if len(args) > 1:
        try:
            mins = int(args[1])
            if 20 <= mins <= 1440:
                config["delete_minutes"] = mins
                config["clean_on"] = True
                await message.reply(f"✅ Auto-clean चालू ({mins} मिनट के लिए)।")
                return
            else:
                await message.reply("⚠️ समय 20 से 1440 मिनट (24 घंटे) के बीच होना चाहिए।")
                return
        except:
            pass

    # Default 60 Minutes
    config["clean_on"] = True
    config["delete_minutes"] = DEFAULT_DELETE_MINUTES
    await message.reply(f"✅ Auto-clean चालू (default {DEFAULT_DELETE_MINUTES} मिनट)।")


# 🧨 CLEANALL COMMAND (Group Owner + Co-Owners)
@app.on_message(filters.command("cleanall", prefixes=["/", "!"]))
async def clean_all(client, message):
    user_id = message.from_user.id

    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        is_owner = member.status == "creator"
    except:
        is_owner = False

    if not (is_owner or user_id in CO_OWNER_IDS):
        await message.reply("❌ केवल Group Owner या Co-Owners यह command चला सकते हैं।")
        return

    await message.reply("🧨 सभी media messages delete किए जा रहे हैं...")

    async for msg in app.get_chat_history(message.chat.id, limit=500):
        if msg.media:
            try:
                await msg.delete()
            except:
                pass

    await message.reply("✅ सभी media delete कर दिए गए!")


# 🧠 AUTO DELETE MONITOR
@app.on_message(filters.group)
async def auto_delete_media(client, message):
    if not config.get("clean_on"):
        return
    if message.media:
        delay = config.get("delete_minutes", DEFAULT_DELETE_MINUTES) * 60
        asyncio.create_task(schedule_delete(client, message.chat.id, message.id, delay))


async def schedule_delete(client, chat_id, msg_id, delay):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, msg_id)
    except:
        pass


# === FLASK KEEP-ALIVE SERVER ===
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🛡️ ShieldX Bot is running!"

@flask_app.route('/healthz')
def healthz():
    return "OK", 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=10000)

# === START BOTH (FLASK + TELEGRAM BOT) ===
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    print("🛡️ ShieldX Cleaner Bot Active on Render...")
    app.run()
