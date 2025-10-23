# -*- coding: utf-8 -*-
# ShieldX Protector Bot — Webhook Ready Top Patch
import os
import asyncio
import threading
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.error import TelegramError
from flask import Flask, request, jsonify
from pyrogram import Client, filters, errors
from pyrogram.types import Message, ChatMemberUpdated, ChatPermissions
from abuse import abuse_check_handler
from config import API_ID, API_HASH, BOT_TOKEN, URL_PATTERN
from helper.utils import (
    is_admin,
    get_config,
    update_config,
    increment_warning,
    reset_warnings,
    is_allowlisted,
    add_allowlist,
    remove_allowlist,
    get_allowlist
)

# ====== Basic Config ======
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://shieldx-bot-1.onrender.com")
WEBHOOK_URL = f"{RENDER_URL}/webhook"
PORT = int(os.getenv("PORT", 8080))

# ====== Telegram + Pyrogram Setup ======
bot = Bot(token=BOT_TOKEN)
app = Client("ShieldX-Bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ====== Flask Server ======
flask_app = Flask("ShieldXBot")

@flask_app.route("/")
def home():
    return "🛡️ ShieldX Bot is Running - 24/7 Active 🚀"

@flask_app.route("/health")
def health():
    return jsonify({"status": "✅ Bot is running", "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else "loop_not_running"}), 200

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        if update.message:
            chat_id = update.message.chat.id
            text = update.message.text
            print(f"[Webhook] Message from {chat_id}: {text}")

            # Minimal /start reply (engagement-free)
            if text == "/start":
                bot.send_message(chat_id, "✨ ShieldX Bot is active via webhook 🛡️")
        return "ok", 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return "error", 500

# ====== Webhook Setup Function ======
async def setup_webhook():
    try:
        await bot.set_webhook(WEBHOOK_URL)
        print(f"✅ Webhook set to: {WEBHOOK_URL}")
    except Exception as e:
        print(f"❌ Webhook setup failed: {e}")

# ====== TOP PATCH END ======
@app.on_message(filters.command("start"))
async def start_handler(client: Client, message):
    try:
        chat_id = message.chat.id
        bot_user = await client.get_me()

        # Safe user name fetch (fallback)
        user = message.from_user.first_name if message.from_user else "User"

        add_url = f"https://t.me/{bot_user.username}?startgroup=true"
        text = (
            f"✨ **नमस्ते, {user}!** ✨\n\n"
            "मैं 🛡️ **ShieldX Protector** 🤖 बॉट हूं — आपकी ऑल-इन-वन AI ग्रुप सिक्योरिटी सिस्टम।\n\n"
            "🔹 **मुख्य सुरक्षा:**\n"
            "   ✨🛡️ **Bio Shield:** यूजर बायो से लिंक्स को ऑटो स्कैन और रिमूव करता है 🔗\n"
            "   • एडिटेड या स्पैम मैसेजेस को ऑटो डिलीट करता है 🧹\n"
            "   • स्मार्ट अब्यूज फिल्टर ऑटो डिलीट के साथ ⚔️\n"
            "   • कस्टम वार्निंग लिमिट्स और सजा 🚨\n"
            "   • भरोसेमंद मेंबर्स के लिए अलाउलिस्ट मैनेजमेंट ✅\n\n"
            "💡 • सभी कमांड्स देखने के लिए /help यूज करें।\n"
            "🛡️ सेफ रहें — ShieldX सब कुछ देख रहा है 👁️"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ मुझे अपने ग्रुप में ऐड करें", url=add_url)],
            [
                InlineKeyboardButton("🛠️ सपोर्ट", url="https://t.me/FakeSupportX"),
                InlineKeyboardButton("🗑️ डिलीट", callback_data="delete")
            ]
        ])

        await client.send_message(chat_id, text, reply_markup=kb)
    except Exception as e:
        print(f"Start handler error: {e}")

@app.on_message(filters.command("help"))
async def help_handler(client: Client, message):
    try:
        chat_id = message.chat.id
        help_text = (
            "**🛠️ ShieldX Protector Bot — कमांड्स और फीचर्स**\n\n"
            "`/config` – वार्न-लिमिट और सजा मोड सेट करें (mute/ban)\n"
            "`/allow` – यूजर को अलाउलिस्ट करें (रिप्लाई या यूजर/आईडी)\n"
            "`/unallow` – यूजर को अलाउलिस्ट से हटाएं\n"
            "`/allowlist` – सभी अलाउलिस्टेड यूजर्स दिखाएं\n\n"
            "**🚨 ऑटोमेटिक प्रोटेक्शन:**\n"
            " 1️⃣ ⚠️ अब्यूसिव वर्ड्स वाले मैसेजेस को ऑटो वार्न और डिलीट\n"
            " 2️⃣ ✏️ ग्रुप्स में एडिटेड मैसेजेस को डिटेक्ट और डिलीट\n"
            " 3️⃣ 🔗 यूजर बायो में लिंक्स को डिटेक्ट और डिलीट\n"
            " 4️⃣ 🔇 वार्निंग लिमिट क्रॉस होने पर म्यूट\n"
            " 5️⃣ 🔨 बैन मोड सेट होने पर बैन\n\n"
            "**💡 इंटरेक्टिव बटन्स:**\n"
            "वार्निंग्स पर इनलाइन बटन्स यूज करें तुरंत कैंसल, अलाउलिस्ट या डिलीट करने के लिए।\n\n"
            "**🛡️ ShieldX Protector के साथ अपने ग्रुप को सेफ और क्लीन रखें!**"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")]
        ])
        await client.send_message(chat_id, help_text, reply_markup=kb)
    except Exception as e:
        print(f"Help handler error: {e}")

@app.on_message(filters.group & filters.command("config"))
async def configure(client: Client, message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not await is_admin(client, chat_id, user_id):
            return await message.reply("❌ आप एडमिन नहीं हैं!")

        mode, limit, penalty = await get_config(chat_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("वार्निंग लिमिट", callback_data="warn")],
            [
                InlineKeyboardButton("म्यूट ✅" if penalty == "mute" else "म्यूट", callback_data="mute"),
                InlineKeyboardButton("बैन ✅" if penalty == "ban" else "बैन", callback_data="ban")
            ],
            [InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")]
        ])
        await client.send_message(
            chat_id,
            "**बायो में लिंक वाले यूजर्स के लिए सजा चुनें:**",
            reply_markup=keyboard
        )
        await message.delete()
    except Exception as e:
        print(f"Config handler error: {e}")

@app.on_message(filters.group & filters.command("allow"))
async def command_allow(client: Client, message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not await is_admin(client, chat_id, user_id):
            return await message.reply("❌ आप एडमिन नहीं हैं!")

        if message.reply_to_message:
            target = message.reply_to_message.from_user
        elif len(message.command) > 1:
            arg = message.command[1]
            target = await client.get_users(int(arg) if arg.isdigit() else arg)
        else:
            return await client.send_message(chat_id, "**रिप्लाई करें या /allow यूजर या आईडी से किसी को अलाउलिस्ट करें।**")

        await add_allowlist(chat_id, target.id)
        await reset_warnings(chat_id, target.id)

        text = f"**✅ {target.mention} को अलाउलिस्ट में ऐड कर दिया गया है**"
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🚫 अनअलाउलिस्ट", callback_data=f"unallowlist_{target.id}"),
                InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")
            ]
        ])
        await client.send_message(chat_id, text, reply_markup=keyboard)
    except Exception as e:
        print(f"Allow handler error: {e}")

@app.on_message(filters.group & filters.command("unallow"))
async def command_unallow(client: Client, message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not await is_admin(client, chat_id, user_id):
            return await message.reply("❌ आप एडमिन नहीं हैं!")

        if message.reply_to_message:
            target = message.reply_to_message.from_user
        elif len(message.command) > 1:
            arg = message.command[1]
            target = await client.get_users(int(arg) if arg.isdigit() else arg)
        else:
            return await client.send_message(chat_id, "**रिप्लाई करें या /unallow यूजर या आईडी से किसी को अनअलाउलिस्ट करें।**")

        if await is_allowlisted(chat_id, target.id):
            await remove_allowlist(chat_id, target.id)
            text = f"**🚫 {target.mention} को अलाउलिस्ट से रिमूव कर दिया गया है**"
        else:
            text = f"**ℹ️ {target.mention} अलाउलिस्टेड नहीं है।**"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ अलाउलिस्ट", callback_data=f"allowlist_{target.id}"),
                InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")
            ]
        ])
        await client.send_message(chat_id, text, reply_markup=keyboard)
    except Exception as e:
        print(f"Unallow handler error: {e}")

@app.on_message(filters.group & filters.command("allowlist"))
async def command_allowlist(client: Client, message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if not await is_admin(client, chat_id, user_id):
            return await message.reply("❌ आप एडमिन नहीं हैं!")

        ids = await get_allowlist(chat_id)
        if not ids:
            await client.send_message(chat_id, "**⚠️ इस ग्रुप में कोई यूजर अलाउलिस्टेड नहीं है।**")
            return

        text = "**📋 अलाउलिस्टेड यूजर्स:**\n\n"
        for i, uid in enumerate(ids, start=1):
            try:
                user = await client.get_users(uid)
                name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
                text += f"{i}: {name} [`{uid}`]\n"
            except:
                text += f"{i}: [यूजर नहीं मिला] [`{uid}`]\n"

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")]])
        await client.send_message(chat_id, text, reply_markup=keyboard)
    except Exception as e:
        print(f"Allowlist handler error: {e}")

@app.on_callback_query()
async def callback_handler(client: Client, callback_query):
    try:
        data = callback_query.data
        chat_id = callback_query.message.chat.id
        user_id = callback_query.from_user.id
        
        if not await is_admin(client, chat_id, user_id):
            return await callback_query.answer("❌ आप एडमिन नहीं हैं", show_alert=True)

        if data == "Delete":
            return await callback_query.message.delete()

        if data == "back":
            mode, limit, penalty = await get_config(chat_id)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("वार्निंग लिमिट", callback_data="warn")],
                [
                    InlineKeyboardButton("म्यूट ✅" if penalty=="mute" else "म्यूट", callback_data="mute"),
                    InlineKeyboardButton("बैन ✅" if penalty=="ban" else "बैन", callback_data="ban")
                ],
                [InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")]
            ])
            await callback_query.message.edit_text("**बायो में लिंक वाले यूजर्स के लिए सजा चुनें:**", reply_markup=kb)
            return await callback_query.answer()

        if data == "warn":
            _, selected_limit, _ = await get_config(chat_id)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"3 ✅" if selected_limit==3 else "3", callback_data="warn_3"),
                 InlineKeyboardButton(f"4 ✅" if selected_limit==4 else "4", callback_data="warn_4"),
                 InlineKeyboardButton(f"5 ✅" if selected_limit==5 else "5", callback_data="warn_5")],
                [InlineKeyboardButton("⬅️ बैक", callback_data="back"), InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")]
            ])
            return await callback_query.message.edit_text("**सजा से पहले वार्निंग्स की संख्या चुनें:**", reply_markup=kb)

        if data in ["mute", "ban"]:
            await update_config(chat_id, penalty=data)
            mode, limit, penalty = await get_config(chat_id)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("वार्निंग लिमिट", callback_data="warn")],
                [
                    InlineKeyboardButton("म्यूट ✅" if penalty=="mute" else "म्यूट", callback_data="mute"),
                    InlineKeyboardButton("बैन ✅" if penalty=="ban" else "बैन", callback_data="ban")
                ],
                [InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")]
            ])
            await callback_query.message.edit_text("**सजा सिलेक्ट की गई:**", reply_markup=kb)
            return await callback_query.answer()

        if data.startswith("warn_"):
            count = int(data.split("_")[1])
            await update_config(chat_id, limit=count)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"3 ✅" if count==3 else "3", callback_data="warn_3"),
                 InlineKeyboardButton(f"4 ✅" if count==4 else "4", callback_data="warn_4"),
                 InlineKeyboardButton(f"5 ✅" if count==5 else "5", callback_data="warn_5")],
                [InlineKeyboardButton("⬅️ बैक", callback_data="back"), InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")]
            ])
            await callback_query.message.edit_text(f"**वार्निंग लिमिट {count} पर सेट की गई**", reply_markup=kb)
            return await callback_query.answer()

        if data.startswith(("unmute_", "unban_")):
            action, uid = data.split("_")
            target_id = int(uid)
            user = await client.get_chat(target_id)
            name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
            try:
                if action == "unmute":
                    await client.restrict_chat_member(chat_id, target_id, ChatPermissions(can_send_messages=True))
                else:
                    await client.unban_chat_member(chat_id, target_id)
                await reset_warnings(chat_id, target_id)
                msg = f"**{name} (`{target_id}`) को {'unmute' if action=='unmute' else 'unban'} किया गया है**."

                kb = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("अलाउलिस्ट ✅", callback_data=f"allowlist_{target_id}"),
                        InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")
                    ]
                ])
                await callback_query.message.edit_text(msg, reply_markup=kb)
            
            except errors.ChatAdminRequired:
                await callback_query.message.edit_text(f"मुझे यूजर्स को {action} करने की परमिशन नहीं है।")
            return await callback_query.answer()

        if data.startswith("cancel_warn_"):
            target_id = int(data.split("_")[-1])
            await reset_warnings(chat_id, target_id)
            user = await client.get_chat(target_id)
            full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
            mention = f"[{full_name}](tg://user?id={target_id})"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("अलाउलिस्ट✅", callback_data=f"allowlist_{target_id}"),
                 InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")]
            ])
            await callback_query.message.edit_text(f"**✅ {mention} [`{target_id}`] की कोई वार्निंग्स नहीं हैं!**", reply_markup=kb)
            return await callback_query.answer()

        if data.startswith("allowlist_"):
            target_id = int(data.split("_")[1])
            await add_allowlist(chat_id, target_id)
            await reset_warnings(chat_id, target_id)
            user = await client.get_chat(target_id)
            full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
            mention = f"[{full_name}](tg://user?id={target_id})"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚫 अनअलाउलिस्ट", callback_data=f"unallowlist_{target_id}"),
                 InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")]
            ])
            await callback_query.message.edit_text(f"**✅ {mention} [`{target_id}`] को अलाउलिस्ट कर दिया गया है!**", reply_markup=kb)
            return await callback_query.answer()

        if data.startswith("unallowlist_"):
            target_id = int(data.split("_")[1])
            await remove_allowlist(chat_id, target_id)
            user = await client.get_chat(target_id)
            full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
            mention = f"[{full_name}](tg://user?id={target_id})"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("अलाउलिस्ट✅", callback_data=f"allowlist_{target_id}"),
                 InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")]
            ])
            await callback_query.message.edit_text(f"**❌ {mention} [`{target_id}`] को अलाउलिस्ट से रिमूव कर दिया गया है।**", reply_markup=kb)
            return await callback_query.answer()
    except Exception as e:
        print(f"Callback handler error: {e}")

@app.on_message(filters.group)
async def check_bio(client: Client, message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id

        if await is_admin(client, chat_id, user_id) or await is_allowlisted(chat_id, user_id):
            return

        # FloodWait safe user fetch
        try:
            user = await client.get_chat(user_id)
        except errors.FloodWait as e:
            await asyncio.sleep(e.value)
            user = await client.get_chat(user_id)
        except Exception as ex:
            print(f"[Bio Check Error] {ex}")
            return

        bio = user.bio or ""
        full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
        mention = f"[{full_name}](tg://user?id={user_id})"

        if URL_PATTERN.search(bio):
            try:
                await message.delete()
            except errors.MessageDeleteForbidden:
                await message.reply_text("कृपया मुझे डिलीट परमिशन दें।")

            # Get warning config
            mode, limit, penalty = await get_config(chat_id)

            if mode == "warn":
                count = await increment_warning(chat_id, user_id)
                warning_text = (
                    "🚨🚨 **⚠️ वार्निंग इश्यू की गई ⚠️** 🚨🚨\n\n"
                    f"👤 **यूजर:** {mention} `[{user_id}]`\n"
                    "❌ **कारण:** बायो में URL मिला\n"
                    f"⚠️ **वार्निंग:** {count}/{limit}\n\n"
                    "🛑 **नोटिस:** कृपया तुरंत अपने बायो से सभी लिंक्स हटा दें।\n\n"
                    "📌 बार-बार रूल्स तोड़ने पर म्यूट/बैन हो सकता है।"
                )
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("❌ वार्निंग कैंसल", callback_data=f"cancel_warn_{user_id}"),
                        InlineKeyboardButton("✅ अलाउलिस्ट", callback_data=f"allowlist_{user_id}")
                    ],
                    [
                        InlineKeyboardButton("🗑️ डिलीट", callback_data="Delete")
                    ]
                ])
                sent = await message.reply_text(warning_text, reply_markup=keyboard)

                # Apply penalty if limit reached
                if count >= limit:
                    try:
                        if penalty == "mute":
                            await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
                            kb = InlineKeyboardMarkup([[InlineKeyboardButton("अनम्यूट ✅", callback_data=f"unmute_{user_id}")]])
                            await sent.edit_text(f"**{full_name} को बार-बार रूल्स तोड़ने के लिए 🔇 म्यूट किया गया है।**", reply_markup=kb)
                        elif penalty == "ban":
                            await client.ban_chat_member(chat_id, user_id)
                            kb = InlineKeyboardMarkup([[InlineKeyboardButton("अनबैन ✅", callback_data=f"unban_{user_id}")]])
                            await sent.edit_text(f"**{full_name} को बार-बार रूल्स तोड़ने के लिए 🔨 बैन किया गया है।**", reply_markup=kb)

                    except errors.ChatAdminRequired:
                        await sent.edit_text(f"**मुझे यूजर्स को {penalty} करने की परमिशन नहीं है।**")
            else:
                try:
                    if mode == "mute":
                        await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
                        kb = InlineKeyboardMarkup([[InlineKeyboardButton("अनम्यूट", callback_data=f"unmute_{user_id}")]])
                        await message.reply_text(f"{full_name} को बायो में लिंक के लिए 🔇 म्यूट किया गया है।", reply_markup=kb)
                    else:
                        await client.ban_chat_member(chat_id, user_id)
                        kb = InlineKeyboardMarkup([[InlineKeyboardButton("अनबैन", callback_data=f"unban_{user_id}")]])
                        await message.reply_text(f"{full_name} को बायो में लिंक के लिए 🔨 बैन किया गया है।", reply_markup=kb)
                except errors.ChatAdminRequired:
                    return await message.reply_text(f"मुझे यूजर्स को {mode} करने की परमिशन नहीं है।")
        else:
            await reset_warnings(chat_id, user_id)
    except Exception as e:
        print(f"Bio check error: {e}")

# =========================
# Full GC Activity Logger (All Chats)
# Tracks messages, edits, deletions, join/leave
# Sends logs to BOT_LOG_ID
# =========================

BOT_LOG_ID = -1002123456789  # अपना ID या लॉगिंग चैनल ID डालें

# ---- Messages ----
@app.on_message(filters.group)
async def log_message(client: Client, message: Message):
    try:
        user = message.from_user
        chat = message.chat

        if user:
            user_mention = f"[{user.first_name}](tg://user?id={user.id})"
            user_id = user.id
        else:
            user_mention = "अननोन / बॉट"
            user_id = "N/A"

        if message.text:
            content = message.text
        elif message.sticker:
            content = "📌 स्टिकर"
        elif message.photo:
            content = "🖼️ फोटो"
        elif message.video:
            content = "🎬 वीडियो"
        elif message.document:
            content = "📄 डॉक्यूमेंट"
        else:
            content = f"{type(message).__name__}"

        log_text = (
            f"📝 **GC एक्टिविटी**\n"
            f"👥 चैट: {chat.title or chat.first_name} (`{chat.id}`)\n"
            f"👤 यूजर: {user_mention} (`{user_id}`)\n"
            f"📄 कंटेंट: {content[:100] + ('...' if len(content) > 100 else '')}"
        )

        await client.send_message(BOT_LOG_ID, log_text, parse_mode="markdown")
    except Exception as e:
        print(f"[एक्टिविटी लॉग] एरर: {e}")

# ---- Edited Messages ----
@app.on_edited_message(filters.group)
async def log_edited(client: Client, message: Message):
    try:
        user = message.from_user
        user_mention = f"[{user.first_name}](tg://user?id={user.id})" if user else "अननोन/बॉट"
        chat = message.chat
        content = message.text or message.caption or f"{type(message).__name__}"

        log_text = (
            f"✏️ **एडिटेड मैसेज**\n"
            f"👥 चैट: {chat.title or chat.first_name} (`{chat.id}`)\n"
            f"👤 यूजर: {user_mention} (`{user.id if user else 'N/A'}`)\n"
            f"📄 कंटेंट: {content[:100] + ('...' if len(content) > 100 else '')}"
        )

        await client.send_message(BOT_LOG_ID, log_text, parse_mode="markdown")
    except Exception as e:
        print(f"[एडिटेड लॉग] एरर: {e}")

# ---- Deleted Messages ----
@app.on_deleted_messages(filters.group)
async def log_deleted(client: Client, messages):
    for msg in messages:
        try:
            user = msg.from_user
            user_mention = f"[{user.first_name}](tg://user?id={user.id})" if user else "अननोन/बॉट"
            chat = msg.chat
            content = msg.text or msg.caption or f"{type(msg).__name__}"

            log_text = (
                f"🗑️ **डिलीटेड मैसेज**\n"
                f"👥 चैट: {chat.title or chat.first_name} (`{chat.id}`)\n"
                f"👤 यूजर: {user_mention} (`{user.id if user else 'N/A'}`)\n"
                f"📄 कंटेंट: {content[:100] + ('...' if len(content) > 100 else '')}"
            )

            await client.send_message(BOT_LOG_ID, log_text, parse_mode="markdown")
        except Exception as e:
            print(f"[डिलीटेड लॉग] एरर: {e}")

# ---- Join / Leave ----
@app.on_chat_member_updated()
async def log_member_update(client: Client, member_update: ChatMemberUpdated):
    try:
        user = member_update.new_chat_member.user
        chat = member_update.chat
        action = ""
        if member_update.new_chat_member.status == "member":
            action = "🟢 ज्वाइन किया"
        elif member_update.new_chat_member.status == "left":
            action = "🔴 लेफ्ट किया"

        log_text = f"{action} - {user.first_name} `{user.id}` in {chat.title or chat.first_name} (`{chat.id}`)"
        await client.send_message(BOT_LOG_ID, log_text)
    except Exception as e:
        print(f"[मेंबर अपडेट लॉग] एरर: {e}")

# ====== 24/7 Running Setup ======
def start_pyrogram():
    """Pyrogram को अलग थ्रेड में रन करें"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def pyro_main():
        try:
            await app.start()
            bot_user = await app.get_me()
            print(f"✅ बॉट स्टार्ट हो गया: {bot_user.username}")
            
            # Webhook setup
            await setup_webhook()
            
            # Keep alive
            while True:
                await asyncio.sleep(300)  # हर 5 मिनट में हार्टबीट
                print("❤️ बॉट अभी भी लाइव है...")
                
        except Exception as e:
            print(f"❌ Pyrogram error: {e}")
    
    try:
        loop.run_until_complete(pyro_main())
    except KeyboardInterrupt:
        print("🛑 बॉट स्टॉप किया जा रहा है...")
    finally:
        loop.run_until_complete(app.stop())
        loop.close()

def start_flask():
    """Flapp app को रन करें"""
    try:
        flask_app.run(host="0.0.0.0", port=PORT, debug=False)
    except Exception as e:
        print(f"❌ Flask error: {e}")

if __name__ == "__main__":
    print("🚀 ShieldX Bot Starting...")
    
    # Pyrogram को थ्रेड में रन करें
    pyro_thread = threading.Thread(target=start_pyrogram, daemon=True)
    pyro_thread.start()
    
    # Flask को मेन थ्रेड में रन करें
    start_flask()
