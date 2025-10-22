# -*- coding: utf-8 -*-
# ShieldX Protector Bot — JSON Fix (Ready-to-Use)

from pyrogram import Client, filters, errors, enums
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
    Message
)
import asyncio
import threading
import requests
import socket
from flask import Flask

# ====== Bot Config & Helpers ======
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

from config import API_ID, API_HASH, BOT_TOKEN, URL_PATTERN

# ====== Pyrogram Client (Main Bot Instance) ======
app = Client(
    "ShieldX-Bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ====== Example JSON Usage ======
@app.on_message()
async def example_json_usage(client, message: Message):
    # Ignore bots
    if message.from_user is None or message.from_user.is_bot:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if user is allowlisted
    if not await is_allowlisted(chat_id, user_id):
        # Increment warning count
        count = await increment_warning(chat_id, user_id)
        
        # Get chat-specific config
        mode, limit, penalty = await get_config(chat_id)
        
        # Example action based on warnings
        if count >= limit:
            await reset_warnings(chat_id, user_id)
            if penalty == "mute":
                try:
                    await client.restrict_chat_member(
                        chat_id,
                        user_id,
                        ChatPermissions(can_send_messages=False)
                    )
                    await message.reply_text(f"⚠️ User muted for exceeding {limit} warnings.")
                except errors.ChatAdminRequired:
                    await message.reply_text("❌ I need admin rights to mute members.")
            elif penalty == "ban":
                try:
                    await client.kick_chat_member(chat_id, user_id)
                    await message.reply_text(f"⛔ User banned for exceeding {limit} warnings.")
                except errors.ChatAdminRequired:
                    await message.reply_text("❌ I need admin rights to ban members.")
        else:
            await message.reply_text(f"⚠️ Warning {count}/{limit} for breaking rules.")

# ====== Flask Server & Health ======
flask_app = Flask("ShieldXBot")
RENDER_URL = "https://shieldx-bot-1.onrender.com"

@flask_app.route("/health")
def health():
    return "ShieldX Bot is running ✅"

def find_free_port(start_port=8080, max_port=8090):
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    return 8080  # fallback

def run_flask():
    port = find_free_port()
    print(f"✅ Flask server starting on port {port} (/health)")
    try:
        flask_app.run(host="0.0.0.0", port=port)
    except Exception as e:
        print(f"[Flask] Error: {e} | Retrying...")
        run_flask()  # self-restart on crash

# ====== Watchdog Ping (async, 30min DM) ======
async def watchdog_ping(client: Client):
    while True:
        try:
            r = requests.get(RENDER_URL + "/health", timeout=5)
            print(f"[Watchdog] Render pinged | Status: {r.status_code}")
            await client.send_message("7959353330", "⏰ ShieldX Bot is alive")
        except Exception as e:
            print(f"[Watchdog] Ping failed: {e}")
        await asyncio.sleep(1800)  # 30 min
# ====== TOP PATCH END ======
@app.on_message(filters.command("start"))
async def start_handler(client: Client, message):
    chat_id = message.chat.id
    bot = await client.get_me()

    # Safe user name fetch (fallback)
    user = message.from_user.first_name if message.from_user else "User"

    add_url = f"https://t.me/{bot.username}?startgroup=true"
    text = (
        f"✨ **Welcome, {user}!** ✨\n\n"
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

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Me to Your Group", url=add_url)],
        [
            InlineKeyboardButton("🛠️ Support", url="https://t.me/FakeSupportX"),
            InlineKeyboardButton("🗑️ Delete", callback_data="delete")
        ]
    ])

    await client.send_message(chat_id, text, reply_markup=kb)

@app.on_message(filters.command("help"))
async def help_handler(client: Client, message):
    chat_id = message.chat.id
    help_text = (
        "**🛠️ ShieldX Protector Bot — Commands & Features**\n\n"
        "`/config` – Set warn-limit & punishment mode (mute/ban)\n"
        "`/allow` – Allowlist a user (reply or user/id)\n"
        "`/unallow` – Remove user from allowlist\n"
        "`/allowlist` – Show all allowlisted users\n\n"
        "**🚨 Automatic Protections:**\n"
        " 1️⃣ ⚠️ Warn & delete messages containing abusive words automatically\n"
        " 2️⃣ ✏️ Detect & delete edited messages in groups\n"
        " 3️⃣ 🔗 Detect & delete messages with links in user bios\n"
        " 4️⃣ 🔇 Mute if violations exceed warn limit\n"
        " 5️⃣ 🔨 Ban if set to ban\n\n"
        "**💡 Interactive Buttons:**\n"
        "Use the inline buttons on warnings to cancel, allowlist, or delete messages instantly.\n\n"
        "**🛡️ Keep your group safe & clean with ShieldX Protector!**"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ ", callback_data="Delete")]
    ])
    await client.send_message(chat_id, help_text, reply_markup=kb)

@app.on_message(filters.group & filters.command("config"))
async def configure(client: Client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not await is_admin(client, chat_id, user_id):
        return

    mode, limit, penalty = await get_config(chat_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Warn", callback_data="warn")],
        [
            InlineKeyboardButton("Mute ✅" if penalty == "mute" else "Mute", callback_data="mute"),
            InlineKeyboardButton("Ban ✅" if penalty == "ban" else "Ban", callback_data="ban")
        ],
        [InlineKeyboardButton("Delete", callback_data="Delete")]
    ])
    await client.send_message(
        chat_id,
        "**Choose penalty for users with links in bio:**",
        reply_markup=keyboard
    )
    await message.delete()

@app.on_message(filters.group & filters.command("allow"))
async def command_allow(client: Client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not await is_admin(client, chat_id, user_id):
        return

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        arg = message.command[1]
        target = await client.get_users(int(arg) if arg.isdigit() else arg)
    else:
        return await client.send_message(chat_id, "**Reply or use /allow user or id to allowlist someone.**")

    await add_allowlist(chat_id, target.id)
    await reset_warnings(chat_id, target.id)

    text = f"**✅ {target.mention} has been added to the allowlist**"
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚫 Unallowlist", callback_data=f"unallowlist_{target.id}"),
            InlineKeyboardButton("🗑️ Close", callback_data="Delete")
        ]
    ])
    await client.send_message(chat_id, text, reply_markup=keyboard)

@app.on_message(filters.group & filters.command("unallow"))
async def command_unallow(client: Client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not await is_admin(client, chat_id, user_id):
        return

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        arg = message.command[1]
        target = await client.get_users(int(arg) if arg.isdigit() else arg)
    else:
        return await client.send_message(chat_id, "**Reply or use /unallow user or id to unallowlist someone.**")

    if await is_allowlisted(chat_id, target.id):
        await remove_allowlist(chat_id, target.id)
        text = f"**🚫 {target.mention} has been removed from the allowlist**"
    else:
        text = f"**ℹ️ {target.mention} is not allowlisted.**"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ allowlist", callback_data=f"allowlist_{target.id}"),
            InlineKeyboardButton("🗑️ Delete", callback_data="Delete")
        ]
    ])
    await client.send_message(chat_id, text, reply_markup=keyboard)

@app.on_message(filters.group & filters.command("allowlist"))
async def command_allowlist(client: Client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not await is_admin(client, chat_id, user_id):
        return

    ids = await get_allowlist(chat_id)
    if not ids:
        await client.send_message(chat_id, "**⚠️ No users are allowlisted in this group.**")
        return

    text = "**📋 allowlisted Users:**\n\n"
    for i, uid in enumerate(ids, start=1):
        try:
            user = await client.get_users(uid)
            name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
            text += f"{i}: {name} [`{uid}`]\n"
        except:
            text += f"{i}: [User not found] [`{uid}`]\n"

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Delete", callback_data="Delete")]])
    await client.send_message(chat_id, text, reply_markup=keyboard)

@app.on_callback_query()
async def callback_handler(client: Client, callback_query):
    data = callback_query.data
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    if not await is_admin(client, chat_id, user_id):
        return await callback_query.answer("❌ You are not administrator", show_alert=True)

    if data == "Delete":
        return await callback_query.message.delete()

    if data == "back":
        mode, limit, penalty = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Warn", callback_data="warn")],
            [
                InlineKeyboardButton("Mute ✅" if penalty=="mute" else "Mute", callback_data="mute"),
                InlineKeyboardButton("Ban ✅" if penalty=="ban" else "Ban", callback_data="ban")
            ],
            [InlineKeyboardButton("Delete", callback_data="Delete")]
        ])
        await callback_query.message.edit_text("**Choose penalty for users with links in bio:**", reply_markup=kb)
        return await callback_query.answer()

    if data == "warn":
        _, selected_limit, _ = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"3 ✅" if selected_limit==3 else "3", callback_data="warn_3"),
             InlineKeyboardButton(f"4 ✅" if selected_limit==4 else "4", callback_data="warn_4"),
             InlineKeyboardButton(f"5 ✅" if selected_limit==5 else "5", callback_data="warn_5")],
            [InlineKeyboardButton("Back", callback_data="back"), InlineKeyboardButton("Delete", callback_data="Delete")]
        ])
        return await callback_query.message.edit_text("**Select number of warns before penalty:**", reply_markup=kb)

    if data in ["mute", "ban"]:
        await update_config(chat_id, penalty=data)
        mode, limit, penalty = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Warn", callback_data="warn")],
            [
                InlineKeyboardButton("Mute ✅" if penalty=="mute" else "Mute", callback_data="mute"),
                InlineKeyboardButton("Ban ✅" if penalty=="ban" else "Ban", callback_data="ban")
            ],
            [InlineKeyboardButton("Delete", callback_data="Delete")]
        ])
        await callback_query.message.edit_text("**Punishment selected:**", reply_markup=kb)
        return await callback_query.answer()

    if data.startswith("warn_"):
        count = int(data.split("_")[1])
        await update_config(chat_id, limit=count)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"3 ✅" if count==3 else "3", callback_data="warn_3"),
             InlineKeyboardButton(f"4 ✅" if count==4 else "4", callback_data="warn_4"),
             InlineKeyboardButton(f"5 ✅" if count==5 else "5", callback_data="warn_5")],
            [InlineKeyboardButton("Back", callback_data="back"), InlineKeyboardButton("Delete", callback_data="Delete")]
        ])
        await callback_query.message.edit_text(f"**Warning limit set to {count}**", reply_markup=kb)
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
            msg = f"**{name} (`{target_id}`) has been {'unmuted' if action=='unmute' else 'unbanned'}**."

            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("allowlist ✅", callback_data=f"allowlist_{target_id}"),
                    InlineKeyboardButton("🗑️ Delete", callback_data="Delete")
                ]
            ])
            await callback_query.message.edit_text(msg, reply_markup=kb)
        
        except errors.ChatAdminRequired:
            await callback_query.message.edit_text(f"I don't have permission to {action} users.")
        return await callback_query.answer()

    if data.startswith("cancel_warn_"):
        target_id = int(data.split("_")[-1])
        await reset_warnings(chat_id, target_id)
        user = await client.get_chat(target_id)
        full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
        mention = f"[{full_name}](tg://user?id={target_id})"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("allowlist✅", callback_data=f"allowlist_{target_id}"),
             InlineKeyboardButton("🗑️ Delete", callback_data="Delete")]
        ])
        await callback_query.message.edit_text(f"**✅ {mention} [`{target_id}`] has no more warnings!**", reply_markup=kb)
        return await callback_query.answer()

    if data.startswith("allowlist_"):
        target_id = int(data.split("_")[1])
        await add_allowlist(chat_id, target_id)
        await reset_warnings(chat_id, target_id)
        user = await client.get_chat(target_id)
        full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
        mention = f"[{full_name}](tg://user?id={target_id})"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 Unallowlist", callback_data=f"unallowlist_{target_id}"),
             InlineKeyboardButton("🗑️ Delete", callback_data="Delete")]
        ])
        await callback_query.message.edit_text(f"**✅ {mention} [`{target_id}`] has been allowlisted!**", reply_markup=kb)
        return await callback_query.answer()

    if data.startswith("unallowlist_"):
        target_id = int(data.split("_")[1])
        await remove_allowlist(chat_id, target_id)
        user = await client.get_chat(target_id)
        full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
        mention = f"[{full_name}](tg://user?id={target_id})"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("allowlist✅", callback_data=f"allowlist_{target_id}"),
             InlineKeyboardButton("🗑️ Delete", callback_data="Delete")]
        ])
        await callback_query.message.edit_text(f"**❌ {mention} [`{target_id}`] has been removed from allowlist.**", reply_markup=kb)
        return await callback_query.answer()
@app.on_message(filters.group)
async def check_bio(client: Client, message):
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
            await message.reply_text("Please grant me delete permission.")

        # Get warning config
        mode, limit, penalty = await get_config(chat_id)

        if mode == "warn":
            count = await increment_warning(chat_id, user_id)
            warning_text = (
                "🚨🚨 **⚠️ Warning Issued ⚠️** 🚨🚨\n\n"
                f"👤 **User:** {mention} `[{user_id}]`\n"
                "❌ **Reason:** URL detected in bio\n"
                f"⚠️ **Warning:** {count}/{limit}\n\n"
                "🛑 **Notice:** Please remove any links from your bio immediately.\n\n"
                "📌 Repeated violations may lead to mute/ban."
            )
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("❌ Cancel Warning", callback_data=f"cancel_warn_{user_id}"),
                    InlineKeyboardButton("✅ allowlist", callback_data=f"allowlist_{user_id}")
                ],
                [
                    InlineKeyboardButton("🗑️ Delete", callback_data="Delete")
                ]
            ])
            sent = await message.reply_text(warning_text, reply_markup=keyboard)

            # Apply penalty if limit reached
            if count >= limit:
                try:
                    if penalty == "mute":
                        await client.restrict_chat_member(chat_id, user_id, until_date=None, can_send_messages=False)
                        await sent.edit_text(f"🔇 {mention} has been muted due to repeated violations.")
                    elif penalty == "ban":
                        await client.ban_chat_member(chat_id, user_id)
                        await sent.edit_text(f"🚫 {mention} has been banned due to repeated violations.")
                except Exception as e:
                    print(f"[PENALTY Handler] {e}")

                try:
                    if penalty == "mute":
                        await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
                        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unmute ✅", callback_data=f"unmute_{user_id}")]])
                        await sent.edit_text(f"**{full_name} has been 🔇 muted for [Link In Bio].**", reply_markup=kb)
                    else:
                        await client.ban_chat_member(chat_id, user_id)
                        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unban ✅", callback_data=f"unban_{user_id}")]])
                        await sent.edit_text(f"**{full_name} has been 🔨 banned for [Link In Bio].**", reply_markup=kb)

                except errors.ChatAdminRequired:
                    await sent.edit_text(f"**I don't have permission to {penalty} users.**")
        else:
            try:
                if mode == "mute":
                    await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unmute", callback_data=f"unmute_{user_id}")]])
                    await message.reply_text(f"{full_name} has been 🔇 muted for [Link In Bio].", reply_markup=kb)
                else:
                    await client.ban_chat_member(chat_id, user_id)
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unban", callback_data=f"unban_{user_id}")]])
                    await message.reply_text(f"{full_name} has been 🔨 banned for [Link In Bio].", reply_markup=kb)
            except errors.ChatAdminRequired:
                return await message.reply_text(f"I don't have permission to {mode} users.")
    else:
        await reset_warnings(chat_id, user_id)

# =========================
# Edited Message Block Handler
# Blocks text edits in groups
# Ignores emoji reactions, media edits, and service messages
# Integrated with warning system
# =========================

from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio

@app.on_edited_message(filters.group)
async def handle_edited_message(client: Client, message: Message):
    # 1️⃣ Ignore non-text edits (stickers, media, reactions)
    if not message.text or message.text == "":
        return

    # 2️⃣ Ignore service messages (like join/leave, pinned, reactions)
    if message.service:
        return

    try:
        user = message.from_user
        if not user:
            return

        # Delete the edited message
        await message.delete()

        # Send warning to the user
        warn = await message.reply_text(
            f"⚠️ {user.mention}, editing messages is not allowed!",
            quote=True
        )

        # Auto-delete warning after 10 seconds
        await asyncio.sleep(10)
        await warn.delete()

    except Exception as e:
        print(f"[Edit Block Handler] {e}")

import threading
import asyncio

# ====== Flask Health Server ======
threading.Thread(target=run_flask, daemon=True).start()
print("✅ Flask server running in background")

# ====== Watchdog Ping ======
async def start_watchdog():
    await watchdog_ping(app)

# Create background asyncio task for watchdog
loop = asyncio.get_event_loop()
loop.create_task(start_watchdog())

# ====== Start Bot ======
print("✅ ShieldX Bot running...")
app.run()  # synchronous, bot events fully responsive

