import os
import requests
import threading
import time  # Don't forget to import the time module
from flask import Flask, request
import telegram

# Bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telegram.Bot(token=BOT_TOKEN)
app = Flask(__name__)

# ====== Webhook Ping ======
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://shieldx-bot-1.onrender.com")
WEBHOOK_URL = f"{RENDER_URL}/health"

def ping_webhook():
    while True:
        try:
            # Ping the webhook URL every 6 minutes
            response = requests.get(WEBHOOK_URL)
            if response.status_code == 200:
                print(f"✅ Webhook pinged successfully at {RENDER_URL}")
            else:
                print(f"❌ Webhook ping failed with status code {response.status_code}")
        except Exception as e:
            print(f"❌ Error pinging webhook: {e}")
        
        # Wait for 6 minutes (360 seconds) before the next ping
        time.sleep(360)

# Start the pinging thread
ping_thread = threading.Thread(target=ping_webhook, daemon=True)
ping_thread.start()

# ====== Webhook Handling ======
@app.route('/webhook', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    if update.message:
        if update.message.text == '/start':
            chat_id = update.message.chat.id
            user_name = update.message.from_user.first_name
            text = (
                f"✨ **Welcome, {user_name}!** ✨\n\n"
                "I'm 🛡️ **ShieldX Protector** 🤖 Bot — your all-in-one AI Group Security system.\n\n"
                "🔹 **Key Protections:**\n"
                "   ✨🛡️ **Bio Shield:** Automatically scans & removes any links from user bios 🔗\n"
                "   • Auto-deletes edited or spam messages 🧹\n"
                "   • Smart abuse filter with auto delete ⚔️\n"
                "   • Custom warning limits with punishments 🚨\n"
                "   • Allowlist management for trusted members ✅\n\n"
                "💡 • Use /help to view all commands.\n"
                "🛡️ Stay safe — ShieldX is watching everything 👁️"
            )
            # Sending welcome message
            bot.send_message(chat_id, text)

    return 'ok', 200

@app.route('/health', methods=['GET'])
def health():
    return '✅ Bot is running', 200

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
