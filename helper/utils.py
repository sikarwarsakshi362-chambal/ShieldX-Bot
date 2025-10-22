import json
import os
from pyrogram import Client, enums
from config import DEFAULT_CONFIG, DEFAULT_WARNING_LIMIT, DEFAULT_PUNISHMENT

# JSON data file path
DATA_FILE = "data.json"

# ========== Strict Mode JSON Helper ==========
def load_data():
    """Load JSON data safely."""
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"warnings": {}, "punishments": {}, "allowlists": {}}, f)
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("❌ JSON corrupt — resetting to default (strict mode).")
        data = {"warnings": {}, "punishments": {}, "allowlists": {}}
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
        return data

def save_data(data):
    """Save data safely with overwrite (strict mode)."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ========== Bot Utility Functions ==========
async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    async for member in client.get_chat_members(
        chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS
    ):
        if member.user.id == user_id:
            return True
    return False

# ==================== CONFIG ====================
async def get_config(chat_id: int):
    data = load_data()
    cfg = data["punishments"].get(str(chat_id))
    if cfg:
        return cfg.get("mode", "warn"), cfg.get("limit", DEFAULT_WARNING_LIMIT), cfg.get("penalty", DEFAULT_PUNISHMENT)
    return DEFAULT_CONFIG

async def update_config(chat_id: int, mode=None, limit=None, penalty=None):
    data = load_data()
    chat_id = str(chat_id)
    update = data["punishments"].get(chat_id, {})
    if mode is not None:
        update["mode"] = mode
    if limit is not None:
        update["limit"] = limit
    if penalty is not None:
        update["penalty"] = penalty
    data["punishments"][chat_id] = update
    save_data(data)

# ==================== WARNINGS ====================
async def increment_warning(chat_id: int, user_id: int) -> int:
    data = load_data()
    chat_id = str(chat_id)
    user_id = str(user_id)
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
    return str(user_id) in data["allowlists"].get(str(chat_id), [])

async def add_allowlist(chat_id: int, user_id: int):
    data = load_data()
    chat_id = str(chat_id)
    data["allowlists"].setdefault(chat_id, [])
    if str(user_id) not in data["allowlists"][chat_id]:
        data["allowlists"][chat_id].append(str(user_id))
    save_data(data)

async def remove_allowlist(chat_id: int, user_id: int):
    data = load_data()
    chat_id = str(chat_id)
    if chat_id in data["allowlists"]:
        data["allowlists"][chat_id] = [
            uid for uid in data["allowlists"][chat_id] if uid != str(user_id)
        ]
    save_data(data)

async def get_allowlist(chat_id: int) -> list:
    data = load_data()
    return data["allowlists"].get(str(chat_id), [])
