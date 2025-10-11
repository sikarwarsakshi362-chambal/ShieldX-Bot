import os
from pyrogram import Client, filters

# Load credentials from environment variables (set these in Koyeb)
API_ID = int(os.environ.get("API_ID") or 0)
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not API_ID or not API_HASH or not BOT_TOKEN:
    print("ERROR: API_ID, API_HASH or BOT_TOKEN not set in environment.")
    raise SystemExit(1)

app = Client("shieldx", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply_text(
        "🛡️ *Welcome to ShieldX Media Protector Bot!*\n\n"
        "✅ Automatically removes spam, NSFW & abusive content.\n"
        "👮 Add me as admin in your group to activate protection.",
        quote=True
    )

print("🤖 ShieldX Bot is ready.")
app.run()
