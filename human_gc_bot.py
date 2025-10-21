# -*- coding: utf-8 -*-
from pyrogram import Client, filters
import asyncio, random, uuid
from pyrogram.types import Message

API_ID = 26250263
API_HASH = "24b066ce7a9020dfbd69b4dc593993f1"
MY_ID = 7959353330
SESSION_NAME = f"human_gc_bot_{uuid.uuid4()}"  # Fresh session har run
GROUP_ID = -1002744711525  # Sirf yahi GC use hoga
REPLY_DELAY = (5, 7)

TEXT_WISHES = [
    "Happy Diwali! 🪔✨ May your life be full of lights and happiness!",
    "Wishing you a sparkling Diwali full of joy and sweets! 🍬",
    "May this Diwali bring lots of love and laughter to you! 🎆",
    "Bright Diwali wishes to you! 🕯️ Stay blessed!",
]

GIFS = [
    "CgACAgQAAxkBAAIBF2I6CwV2x-3iV7vYB3N9Y1h7y1G_AAK1AAACpLQxS5IQkqg4qQFvSJAQ",
    "CgACAgQAAxkBAAIBGWI6CwX1yL_8jUoKh1R-3qXgS1D0AAK2AAACpLQxS6Wj2iY8LQxFvSJAQ"
]

wished_users = set()
app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH, bot_token="YOUR_BOT_TOKEN")

# ---------------- Human-like Reply ----------------
async def generate_reply(text):
    text = text.lower()
    keywords = {
        "hi": ["Hey!", "Hello!", "Hi! How are you?"],
        "hello": ["Hello!", "Hey there!", "Hi 😎"],
        "how are you": ["I'm good, thanks!", "Doing great 😁"],
        "bye": ["Bye!", "Take care!"],
        "diwali": ["Happy Diwali! 🪔", "Wishing you a bright Diwali ✨"]
    }
    for k, v in keywords.items():
        if k in text:
            return random.choice(v)
    return random.choice(["Hmm okay.", "Interesting!", "Really?", "Got it!", "Ahh I see!", "Nice!"])

# ---------------- GC Chat Handler ----------------
@app.on_message(filters.group & filters.text)
async def gc_chat_handler(client, message: Message):
    if message.from_user and message.from_user.id == MY_ID:
        return
    await asyncio.sleep(random.uniform(2, 5))
    reply = await generate_reply(message.text or "")
    try:
        await message.reply(reply)
    except: pass

# ---------------- Diwali Wishing ----------------
async def wish_users():
    async for member in app.get_chat_members(GROUP_ID):`n        chat = dialog.chat`n        if chat.type in [ "supergroup", "group" ]:`n            admins = await app.get_chat_members(chat.id, filter="administrators")`n            admin_ids = [a.user.id for a in admins]`n            if MY_ID in admin_ids:`n                async for member in app.get_chat_members(chat.id):  # async generator ke liye
        if dialog.chat.type in ["supergroup", "group"] and dialog.chat.id not in wished_users:
            try:
                member = await app.get_chat_member(dialog.chat.id, MY_ID)
                if member.status not in ["administrator", "creator"]:
                    continue  # Agar admin nahi to skip
            except:
                continue  # Agar fetch fail ho gaya to skip

            async for user in app.get_chat_members(dialog.chat.id):
                u = user.user
                if u.is_bot or u.is_deleted or u.id in wished_users:
                    continue
                mention = f"[{u.first_name}](tg://user?id={u.id})"
                text = random.choice(TEXT_WISHES)
                gif = random.choice(GIFS + [None]*3)
                final_msg = f"{mention}\n{text}"
                try:
                    if gif:
                        await app.send_animation(dialog.chat.id, gif, caption=final_msg, parse_mode="markdown")
                    else:
                        await app.send_message(dialog.chat.id, final_msg, parse_mode="markdown")
                    wished_users.add(u.id)
                    await asyncio.sleep(random.uniform(*REPLY_DELAY))
                except Exception as e:
                    print(f"❌ Skipped {u.id}: {e}")


# ---------------- Run Bot ----------------
async def main():
    await app.start()
    print("Human-like GC Diwali Bot Active")
    await wish_users()
    await asyncio.get_event_loop().create_future()

if __name__=="__main__":
    asyncio.run(main())
