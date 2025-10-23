# bot.py
import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

# ===== Env Variables =====
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7981496411:AAHSjcC62nEmpkA2xXMUT4Tl1X3_9xFtZDE")
WEBHOOK_PATH = "/webhook"  # as per your setWebhook URL

# ===== Initialize Bot =====
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, None, workers=0)  # synchronous for webhook

app = Flask(__name__)

# ===== Bot Commands =====
def start(update: Update, context):
    update.message.reply_text("Webhook test successful! ✅")

dp.add_handler(CommandHandler("start", start))

# ===== Webhook Route =====
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return "ok", 200

# ===== Health Check =====
@app.route("/", methods=["GET"])
def index():
    return "Bot is running ✅", 200

# ===== Optional: local test =====
if __name__ == "__main__":
    print(f"Bot running. Webhook path: {WEBHOOK_PATH}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
