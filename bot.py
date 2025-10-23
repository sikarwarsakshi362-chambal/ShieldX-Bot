# bot.py
import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, None, workers=0)

app = Flask(__name__)

# ===== Bot Commands =====
def start(update: Update, context):
    update.message.reply_text("Webhook test successful! ✅")

def echo(update: Update, context):
    # simple echo for testing any message
    update.message.reply_text(f"You said: {update.message.text}")

# add handlers
dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

# ===== Webhook Route =====
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running ✅", 200
