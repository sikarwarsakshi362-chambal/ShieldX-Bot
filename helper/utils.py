import json
import os
from pyrogram import Client, enums
from config import DEFAULT_CONFIG, DEFAULT_WARNING_LIMIT, DEFAULT_PUNISHMENT

# JSON data file path
DATA_FILE = "data.json"

# Default structure
DEFAULT_DATA = {
    "warnings": {},        # user_id: warning_count
    "punishments": {},     # user_id: punishment_type
    "settings": {
        "strict_mode": True,
        "warning_limit": 3,
        "default_punishment": "kick"  # kick, ban, mute
    }
}

# Load or initialize JSON data
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump(DEFAULT_DATA, f, indent=4)
        return DEFAULT_DATA
    else:
        with open(DATA_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                # corrupted file reset
                with open(DATA_FILE, "w") as fw:
                    json.dump(DEFAULT_DATA, fw, indent=4)
                return DEFAULT_DATA

# Save JSON data
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

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
    data = load_data()
    cfg = data["punishments"].get(str(chat_id), {})
    mode = cfg.get("mode", DEFAULT_CONFIG.get("mode", "warn"))
    limit = cfg.get("limit", DEFAULT_CONFIG.get("limit", DEFAULT_WARNING_LIMIT))
    penalty = cfg.get("penalty", DEFAULT_CONFIG.get("penalty", DEFAULT_PUNISHMENT))
    return mode, limit, penalty

async def update_config(chat_id: int, mode=None, limit=None, penalty=None):
    data = load_data()
    chat_id = str(chat_id)
    data.setdefault("punishments", {}).setdefault(chat_id, {})
    if mode is not None:
        data["punishments"][chat_id]["mode"] = mode
    if limit is not None:
        data["punishments"][chat_id]["limit"] = limit
    if penalty is not None:
        data["punishments"][chat_id]["penalty"] = penalty
    save_data(data)

# ==================== WARNINGS ====================
async def increment_warning(chat_id: int, user_id: int) -> int:
    data = load_data()
    chat_id, user_id = str(chat_id), str(user_id)
    data.setdefault("warnings", {}).setdefault(chat_id, {}).setdefault(user_id, {"count": 0})
    data["warnings"][chat_id][user_id]["count"] += 1
    count = data["warnings"][chat_id][user_id]["count"]
    save_data(data)
    return count

async def reset_warnings(chat_id: int, user_id: int):
    data = load_data()
    chat_id, user_id = str(chat_id), str(user_id)
    if chat_id in data["warnings"] and user_id in data["warnings"][chat_id]:
        del data["warnings"][chat_id][user_id]
    save_data(data)

# ==================== ALLOWLIST ====================
async def is_allowlisted(chat_id: int, user_id: int) -> bool:
    data = load_data()
    return str(user_id) in data.get("allowlists", {}).get(str(chat_id), [])

async def add_allowlist(chat_id: int, user_id: int):
    data = load_data()
    chat_id = str(chat_id)
    data.setdefault("allowlists", {}).setdefault(chat_id, [])
    if str(user_id) not in data["allowlists"][chat_id]:
        data["allowlists"][chat_id].append(str(user_id))
    save_data(data)

async def remove_allowlist(chat_id: int, user_id: int):
    data = load_data()
    chat_id = str(chat_id)
    if chat_id in data.get("allowlists", {}):
        data["allowlists"][chat_id] = [uid for uid in data["allowlists"][chat_id] if uid != str(user_id)]
    save_data(data)

async def get_allowlist(chat_id: int) -> list:
    data = load_data()
    return data.get("allowlists", {}).get(str(chat_id), [])import json
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
