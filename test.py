import os
from pyrogram import Client, filters
from flask import Flask
import threading

# Config
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH") 
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))

# Pyrogram Client
app = Client("test_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask App
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "🤖 Test Bot is Live 24/7"

@flask_app.route("/health")
def health():
    return "✅ OK", 200

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    return "✅ Webhook OK", 200

# Bot Commands
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("🚀 **Test Bot is Working!**\n\n24/7 Live on Render")

@app.on_message(filters.command("ping"))
async def ping(client, message):
    await message.reply("🏓 **Pong!**\nBot is active and responding.")

@app.on_message(filters.command("info"))
async def info(client, message):
    await message.reply("📊 **Bot Info:**\n• 24/7 Uptime\n• Render Deployment\n• Pyrogram + Flask")

# Flask run in thread
def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, debug=False)

# Keep alive
if __name__ == "__main__":
    print("🚀 Starting Test Bot...")
    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    # Start Pyrogram (main thread)
    app.run()
