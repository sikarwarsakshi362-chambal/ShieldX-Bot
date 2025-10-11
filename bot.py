import os
import time
from pyrogram import Client, filters

# Environment Variables (Render/Koyeb से auto-load होंगे)
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not API_ID or not API_HASH or not BOT_TOKEN:
    print("❌ ERROR: Missing API_ID / API_HASH / BOT_TOKEN in environment.")
    exit(1)

# Pyrogram client
app = Client("shieldx_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply_text(
        "🤖 *ShieldX Media Protector Bot is Active!*\n\n"
        "✅ Protects your groups from NSFW, spam & abuse.\n"
        "💬 Use /help to see more commands.\n"
        "🔒 Add me as admin in your group to activate protection.",
        quote=True
    )

print("🚀 ShieldX Bot is starting...")

# Auto-restart loop
while True:
    try:
        # ---- Web server to keep Render.com free service alive ----
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ ShieldX Bot is running on Render!"

def run_web():
    app.run(host="0.0.0.0", port=8080)

# Start the web server in a background thread
Thread(target=run_web).start()

        app.run()
    except Exception as e:
        print(f"⚠️ Bot crashed due to: {e}")
        print("🔁 Restarting in 5 seconds...")
        time.sleep(5)
