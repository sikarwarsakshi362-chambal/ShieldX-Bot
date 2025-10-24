# -*- coding: utf-8 -*-
# ShieldX Protector Bot — 24/7 Live on Render
import os
import asyncio
import threading
from flask import Flask, request, jsonify
from pyrogram import Client, filters, errors
from pyrogram.types import Message, ChatMemberUpdated, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
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
PORT = int(os.getenv("PORT", 8080))

# ====== Pyrogram Setup ======
app = Client("ShieldX-Bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ====== Flask Server ======
flask_app = Flask("ShieldXBot")

@flask_app.route("/")
def home():
    return "🛡️ ShieldX Bot is Running - 24/7 Active 🚀"

@flask_app.route("/health")
def health():
    return jsonify({"status": "✅ Bot is running"}), 200

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print(f"[Webhook] Received data")
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

# ====== BOT HANDLERS ======
@app.on_message(filters.command("start"))
async def start_handler(client: Client, message):
    try:
        chat_id = message.chat.id
        bot_user = await client.get_me()

        user = message.from_user.first_name if message.from_user else "User"

        add_url = f"https://t.me/{bot_user.username}?startgroup=true"
        text = (
            f"✨ **Hello, {user}!** ✨\n\n"
            "I am 🛡️ **ShieldX Protector** 🤖 Bot — your all-in-one AI Group Security system.\n\n"
            "🔹 **Key Protections:**\n"
            "   ✨🛡️ **Bio Shield:** Automatically scans & removes links from user bios 🔗\n"
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
    except Exception as e:
        print(f"Start handler error: {e}")

@app.on_message(filters.command("help"))
async def help_handler(client: Client, message):
    try:
        chat_id = message.chat.id
        help_text = (
            "**🛠️ ShieldX Protector Bot — Commands & Features**\n\n"
            "`/config` – Set warn-limit & punishment mode (mute/ban)\n"
            "`/allow` – Allowlist a user (reply or user/id)\n"
            "`/unallow` – Remove user from allowlist\n"
            "`/allowlist` – Show all allowlisted users\n\n"
            "**🚨 Automatic Protections:**\n"
            " 1️⃣ ⚠️ Warn & delete messages containing abusive words\n"
            " 2️⃣ ✏️ Detect & delete edited messages in groups\n"
            " 3️⃣ 🔗 Detect & delete messages with links in user bios\n"
            " 4️⃣ 🔇 Mute if violations exceed warn limit\n"
            " 5️⃣ 🔨 Ban if set to ban\n\n"
            "**💡 Interactive Buttons:**\n"
            "Use inline buttons on warnings to cancel, allowlist, or delete.\n\n"
            "**🛡️ Keep your group safe & clean with ShieldX Protector!**"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Delete", callback_data="Delete")]
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
            return await message.reply("❌ You are not admin!")

        mode, limit, penalty = await get_config(chat_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Warn Limit", callback_data="warn")],
            [
                InlineKeyboardButton("Mute ✅" if penalty == "mute" else "Mute", callback_data="mute"),
                InlineKeyboardButton("Ban ✅" if penalty == "ban" else "Ban", callback_data="ban")
            ],
            [InlineKeyboardButton("🗑️ Delete", callback_data="Delete")]
        ])
        await client.send_message(
            chat_id,
            "**Choose penalty for users with links in bio:**",
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
            return await message.reply("❌ You are not admin!")

        if message.reply_to_message:
            target = message.reply_to_message.from_user
        elif len(message.command) > 1:
            arg = message.command[1]
            target = await client.get_users(int(arg) if arg.isdigit() else arg)
        else:
            return await client.send_message(chat_id, "**Reply or use /allow user or id to allowlist someone.**")

        await add_allowlist(chat_id, target.id)
        await reset_warnings(chat_id, target.id)

        text = f"**✅ {target.mention} has been added to allowlist**"
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🚫 Unallow", callback_data=f"unallowlist_{target.id}"),
                InlineKeyboardButton("🗑️ Delete", callback_data="Delete")
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
            return await message.reply("❌ You are not admin!")

        if message.reply_to_message:
            target = message.reply_to_message.from_user
        elif len(message.command) > 1:
            arg = message.command[1]
            target = await client.get_users(int(arg) if arg.isdigit() else arg)
        else:
            return await client.send_message(chat_id, "**Reply or use /unallow user or id to remove from allowlist.**")

        if await is_allowlisted(chat_id, target.id):
            await remove_allowlist(chat_id, target.id)
            text = f"**🚫 {target.mention} has been removed from allowlist**"
        else:
            text = f"**ℹ️ {target.mention} is not allowlisted.**"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Allow", callback_data=f"allowlist_{target.id}"),
                InlineKeyboardButton("🗑️ Delete", callback_data="Delete")
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
            return await message.reply("❌ You are not admin!")

        ids = await get_allowlist(chat_id)
        if not ids:
            await client.send_message(chat_id, "**⚠️ No users are allowlisted in this group.**")
            return

        text = "**📋 Allowlisted Users:**\n\n"
        for i, uid in enumerate(ids, start=1):
            try:
                user = await client.get_users(uid)
                name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
                text += f"{i}: {name} [`{uid}`]\n"
            except:
                text += f"{i}: [User not found] [`{uid}`]\n"

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Delete", callback_data="Delete")]])
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
            return await callback_query.answer("❌ You are not administrator", show_alert=True)

        if data == "Delete":
            return await callback_query.message.delete()

        if data == "back":
            mode, limit, penalty = await get_config(chat_id)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Warn Limit", callback_data="warn")],
                [
                    InlineKeyboardButton("Mute ✅" if penalty=="mute" else "Mute", callback_data="mute"),
                    InlineKeyboardButton("Ban ✅" if penalty=="ban" else "Ban", callback_data="ban")
                ],
                [InlineKeyboardButton("🗑️ Delete", callback_data="Delete")]
            ])
            await callback_query.message.edit_text("**Choose penalty for users with links in bio:**", reply_markup=kb)
            return await callback_query.answer()

        if data == "warn":
            _, selected_limit, _ = await get_config(chat_id)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"3 ✅" if selected_limit==3 else "3", callback_data="warn_3"),
                 InlineKeyboardButton(f"4 ✅" if selected_limit==4 else "4", callback_data="warn_4"),
                 InlineKeyboardButton(f"5 ✅" if selected_limit==5 else "5", callback_data="warn_5")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back"), InlineKeyboardButton("🗑️ Delete", callback_data="Delete")]
            ])
            return await callback_query.message.edit_text("**Select number of warns before penalty:**", reply_markup=kb)

        if data in ["mute", "ban"]:
            await update_config(chat_id, penalty=data)
            mode, limit, penalty = await get_config(chat_id)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Warn Limit", callback_data="warn")],
                [
                    InlineKeyboardButton("Mute ✅" if penalty=="mute" else "Mute", callback_data="mute"),
                    InlineKeyboardButton("Ban ✅" if penalty=="ban" else "Ban", callback_data="ban")
                ],
                [InlineKeyboardButton("🗑️ Delete", callback_data="Delete")]
            ])
            await callback_query.message.edit_text("**Penalty selected:**", reply_markup=kb)
            return await callback_query.answer()

        if data.startswith("warn_"):
            count = int(data.split("_")[1])
            await update_config(chat_id, limit=count)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"3 ✅" if count==3 else "3", callback_data="warn_3"),
                 InlineKeyboardButton(f"4 ✅" if count==4 else "4", callback_data="warn_4"),
                 InlineKeyboardButton(f"5 ✅" if count==5 else "5", callback_data="warn_5")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back"), InlineKeyboardButton("🗑️ Delete", callback_data="Delete")]
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
                        InlineKeyboardButton("✅ Allowlist", callback_data=f"allowlist_{target_id}"),
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
                [InlineKeyboardButton("✅ Allowlist", callback_data=f"allowlist_{target_id}"),
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
                [InlineKeyboardButton("🚫 Unallow", callback_data=f"unallowlist_{target_id}"),
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
                [InlineKeyboardButton("✅ Allow", callback_data=f"allowlist_{target_id}"),
                 InlineKeyboardButton("🗑️ Delete", callback_data="Delete")]
            ])
            await callback_query.message.edit_text(f"**❌ {mention} [`{target_id}`] has been removed from allowlist.**", reply_markup=kb)
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
                        InlineKeyboardButton("✅ Allowlist", callback_data=f"allowlist_{user_id}")
                    ],
                    [
                        InlineKeyboardButton("🗑️ Delete", callback_data="Delete")
                    ]
                ])
                sent = await message.reply_text(warning_text, reply_markup=keyboard)

                if count >= limit:
                    try:
                        if penalty == "mute":
                            await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
                            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unmute ✅", callback_data=f"unmute_{user_id}")]])
                            await sent.edit_text(f"**{full_name} has been 🔇 muted for repeated violations.**", reply_markup=kb)
                        elif penalty == "ban":
                            await client.ban_chat_member(chat_id, user_id)
                            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unban ✅", callback_data=f"unban_{user_id}")]])
                            await sent.edit_text(f"**{full_name} has been 🔨 banned for repeated violations.**", reply_markup=kb)

                    except errors.ChatAdminRequired:
                        await sent.edit_text(f"**I don't have permission to {penalty} users.**")
            else:
                try:
                    if mode == "mute":
                        await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
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
    except Exception as e:
        print(f"Bio check error: {e}")

# ====== EDITED TEXT MESSAGE DELETE ======
@app.on_edited_message(filters.group & filters.text)
async def delete_edited_text_messages(client, message):
    try:
        # Owner ko exempt karo
        if message.from_user.id == OWNER_ID:
            return
            
        # Bot khud ko exempt karo  
        if message.from_user.is_self:
            return
        
        # Message delete karo
        await message.delete()
        
        # Success notification
        user_mention = f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"
        notification = await message.reply_text(
            f"✏️ {user_mention} ka edited text delete kiya gaya."
        )
        
        # Notification ko 3 second baad delete karo
        await asyncio.sleep(3)
        await notification.delete()
        
    except Exception as e:
        # Error handle karo silently
        pass

# Owner-only broadcast command
@app.on_message(filters.private & filters.command("broadcast"))
async def broadcast_handler(client: Client, message):
    # Only the configured OWNER_ID can use this command
    if OWNER_ID <= 0 or message.from_user.id != OWNER_ID:
        return

    # Extract broadcast text
    if len(message.command) > 1:
        text = message.text.split(maxsplit=1)[1]
    elif message.reply_to_message:
        text = message.reply_to_message.text or message.reply_to_message.caption or ""
    else:
        return await message.reply_text("Send /broadcast <text> or reply to a message.")

    # Fetch all known chats and send concurrently with small throttling
    chat_ids = await get_all_chats()
    if not chat_ids:
        return await message.reply_text("No chats registered.")

    await message.reply_text(f"Broadcasting to {len(chat_ids)} chats...")

    async def _send(cid: int):
        try:
            await client.send_message(cid, text)
        except errors.ChatWriteForbidden:
            # Bot removed or can't write; ignore
            pass
        except Exception:
            # Any other send error; ignore to continue broadcast
            pass

    # Limit concurrency to avoid hitting flood limits
    sem = asyncio.Semaphore(10)

    async def _worker(cid: int):
        async with sem:
            await _send(cid)
            await asyncio.sleep(0.1)  # light spacing

    await asyncio.gather(*(_worker(cid) for cid in chat_ids))
    await message.reply_text("Broadcast finished.")

# ====== 24/7 RUNNING SETUP ======
def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, debug=False)

if __name__ == "__main__":
    print("🚀 ShieldX Bot Starting...")
    # Start Flask in thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    # Start Pyrogram
    app.run()
