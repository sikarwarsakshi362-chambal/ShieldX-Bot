# -*- coding: utf-8 -*-
# bot.py (ShieldX v3.0) — env-aware (OWNER_ID / RENDER vars auto-read)

import asyncio
import os
import threading
import time
from flask import Flask
from pyrogram import Client, filters
from pyrogram import idle
from dotenv import load_dotenv

# === Load .env Variables ===
load_dotenv()
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# === Flask App (Keep-Alive) ===
app = Flask(__name__)

# === Pyrogram Bot Setup ===
bot = Client(
    "shieldx",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# === Commands ===
@bot.on_message(filters.command("start"))
async def start_cmd(_, msg):
    await msg.reply("🩵 ShieldX active & running — protected 24x7!")

@bot.on_message(filters.command("ping"))
async def ping_cmd(_, msg):
    start = time.time()
    r = await msg.reply("🏓 Pong...")
    ms = int((time.time() - start) * 1000)
    await r.edit_text(f"🏓 Pong! {ms}ms")

# === Keep-Alive Flask Server ===
@app.route("/")
def home():
    return "🩵 ShieldX Bot is running and protected."

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# === Background Task (Render Anti-Suspend) ===
async def auto_clean():
    while True:
        await asyncio.sleep(240)
        print("[ShieldX] Background keep-alive tick...")

# === Startup ===
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()

    async def main():
        asyncio.create_task(auto_clean())
        await bot.start()
        print("🩵 ShieldX Bot is running and protected.")
        await idle()

    bot.loop.run_until_complete(main())
# Force build v2








# === ShieldX Watchdog Auto-Alert (Safe Inject) ===
import asyncio, os
from datetime import datetime

async def watchdog(bot):
    owner = int(os.getenv("OWNER_ID", 0))
    while True:
        try:
            await bot.get_me()
        except Exception as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg = f"⚠️ ShieldX Crash Detected at {now}\nError: {e}"
            print(msg)
            if owner:
                try:
                    await bot.send_message(owner, msg)
                except Exception:
                    pass
            os._exit(1)
        await asyncio.sleep(60)

try:
    import asyncio
    asyncio.get_event_loop().create_task(watchdog(bot))
except Exception:
    pass
# === End of ShieldX Watchdog Auto-Alert ===


