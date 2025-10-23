# file: app.py
import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

# === Env Variables ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook")  # optional, default /webhook

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, None, workers=0)  # workers=0 for sync handling in webhook

app = Flask(__name__)

# === Bot Command ===
def start(update: Update, context):
    update.message.reply_text("Webhook test successful! ✅")

dp.add_handler(CommandHandler("start", start))

# === Webhook Route ===
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return "ok", 200

# === Health check ===
@app.route("/", methods=["GET"])
def index():
    return "Bot is running ✅", 200

# === Optional: run locally ===
if __name__ == "__main__":
    app.run(debug=True)
