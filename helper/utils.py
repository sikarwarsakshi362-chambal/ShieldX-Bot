import json
import os
from pyrogram import Client, enums
from config import DEFAULT_CONFIG, DEFAULT_WARNING_LIMIT, DEFAULT_PUNISHMENT

# ==================== MEMORY STORAGE ====================
# Memory storage for Render (no JSON file)
user_warnings = {}
chat_configs = {}
allowlists = {}

# ==================== ADMIN CHECK ====================
async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """
    Fixed admin check for Pyrogram 2.3+.
    Handles supergroups, channels, and avoids CHANNEL_INVALID error.
    """
    try:
        # For private and group chats
        async for member in client.get_chat_members(
            chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS
        ):
            if member.user.id == user_id:
                return True
    except Exception as e:
        print(f"[is_admin] Error: {e}")
        return False
    return False

# ==================== CONFIG ====================
async def get_config(chat_id: int):
    if chat_id in chat_configs:
        cfg = chat_configs[chat_id]
        mode = cfg.get("mode", DEFAULT_CONFIG.get("mode", "warn"))
        limit = cfg.get("limit", DEFAULT_CONFIG.get("limit", DEFAULT_WARNING_LIMIT))
        penalty = cfg.get("penalty", DEFAULT_CONFIG.get("penalty", DEFAULT_PUNISHMENT))
        return mode, limit, penalty
    else:
        mode = DEFAULT_CONFIG.get("mode", "warn")
        limit = DEFAULT_CONFIG.get("limit", DEFAULT_WARNING_LIMIT)
        penalty = DEFAULT_CONFIG.get("penalty", DEFAULT_PUNISHMENT)
        return mode, limit, penalty

async def update_config(chat_id: int, mode=None, limit=None, penalty=None):
    if chat_id not in chat_configs:
        chat_configs[chat_id] = {"mode": "warn", "limit": 3, "penalty": "mute"}
    
    if mode is not None:
        chat_configs[chat_id]["mode"] = mode
    if limit is not None:
        chat_configs[chat_id]["limit"] = limit
    if penalty is not None:
        chat_configs[chat_id]["penalty"] = penalty

# ==================== WARNINGS ====================
async def increment_warning(chat_id: int, user_id: int) -> int:
    key = f"{chat_id}:{user_id}"
    if key in user_warnings:
        user_warnings[key] += 1
    else:
        user_warnings[key] = 1
    return user_warnings[key]

async def reset_warnings(chat_id: int, user_id: int):
    key = f"{chat_id}:{user_id}"
    if key in user_warnings:
        user_warnings[key] = 0

# ==================== ALLOWLIST ====================
async def is_allowlisted(chat_id: int, user_id: int) -> bool:
    if chat_id in allowlists:
        return user_id in allowlists[chat_id]
    return False

async def add_allowlist(chat_id: int, user_id: int):
    if chat_id not in allowlists:
        allowlists[chat_id] = []
    if user_id not in allowlists[chat_id]:
        allowlists[chat_id].append(user_id)

async def remove_allowlist(chat_id: int, user_id: int):
    if chat_id in allowlists and user_id in allowlists[chat_id]:
        allowlists[chat_id].remove(user_id)

async def get_allowlist(chat_id: int) -> list:
    if chat_id in allowlists:
        return allowlists[chat_id]
    return []
