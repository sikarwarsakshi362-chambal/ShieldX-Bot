import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "modules"))

from pyrogram import Client, enums, filters
import redis.asyncio as aioredis
from config import redis, DEFAULT_CONFIG, DEFAULT_PUNISHMENT, DEFAULT_WARNING_LIMIT

# ====================== Redis Keys ======================
# Redis key format for warnings, punishments, allowlists
WARNING_KEY = "warnings:{chat_id}:{user_id}"
PUNISHMENT_KEY = "punishments:{chat_id}"
ALLOWLIST_KEY = "allowlist:{chat_id}"

# ====================== Warning Functions ======================
async def get_warnings(chat_id: str, user_id: str):
    """
    Retrieve the warning count for a specific user in a chat.
    """
    key = WARNING_KEY.format(chat_id=chat_id, user_id=user_id)
    warning_count = await redis.get(key)
    return int(warning_count) if warning_count else 0

async def increment_warning(chat_id: str, user_id: str) -> int:
    """
    Increment the warning count for a specific user in a chat.
    """
    key = WARNING_KEY.format(chat_id=chat_id, user_id=user_id)
    new_warning_count = await redis.incr(key)
    return new_warning_count

async def reset_warnings(chat_id: str, user_id: str):
    """
    Reset the warning count for a specific user in a chat.
    """
    key = WARNING_KEY.format(chat_id=chat_id, user_id=user_id)
    await redis.delete(key)

# ====================== Punishment Functions ======================
async def get_config(chat_id: str):
    """
    Retrieve the punishment configuration for a specific chat.
    """
    key = PUNISHMENT_KEY.format(chat_id=chat_id)
    punishment_config = await redis.hgetall(key)
    if punishment_config:
        return punishment_config.get("mode", DEFAULT_CONFIG[0]), \
               int(punishment_config.get("limit", DEFAULT_WARNING_LIMIT)), \
               punishment_config.get("penalty", DEFAULT_PUNISHMENT)
    return DEFAULT_CONFIG

async def update_config(chat_id: str, mode=None, limit=None, penalty=None):
    """
    Update the punishment configuration for a specific chat.
    """
    key = PUNISHMENT_KEY.format(chat_id=chat_id)
    if mode:
        await redis.hset(key, "mode", mode)
    if limit:
        await redis.hset(key, "limit", limit)
    if penalty:
        await redis.hset(key, "penalty", penalty)

# ====================== Allowlist Functions ======================
async def is_allowlisted(chat_id: str, user_id: str) -> bool:
    """
    Check if a user is in the allowlist for a specific chat.
    """
    key = ALLOWLIST_KEY.format(chat_id=chat_id)
    return await redis.sismember(key, user_id)

async def add_allowlist(chat_id: str, user_id: str):
    """
    Add a user to the allowlist for a specific chat.
    """
    key = ALLOWLIST_KEY.format(chat_id=chat_id)
    await redis.sadd(key, user_id)

async def remove_allowlist(chat_id: str, user_id: str):
    """
    Remove a user from the allowlist for a specific chat.
    """
    key = ALLOWLIST_KEY.format(chat_id=chat_id)
    await redis.srem(key, user_id)

async def get_allowlist(chat_id: str) -> list:
    """
    Get the list of users in the allowlist for a specific chat.
    """
    key = ALLOWLIST_KEY.format(chat_id=chat_id)
    allowlist = await redis.smembers(key)
    return list(allowlist)

# ====================== Misc Default Settings ======================
def get_default_settings():
    """
    Return default feature settings for the bot.
    """
    return {
        "abuse_on": True,
        "nsfw_on": True,
        "bio_link_on": True,
        "clean_on": False,
        "delete_minutes": 30
    }

