import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "modules"))

from pyrogram import Client, enums, filters
from motor.motor_asyncio import AsyncIOMotorClient
from config import (
    MONGO_URI,
    DEFAULT_CONFIG,
    DEFAULT_PUNISHMENT,
    DEFAULT_WARNING_LIMIT
)

# ✅ Use consistent Mongo variable
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client['telegram_bot_db']

warnings_collection = db['warnings']
punishments_collection = db['punishments']
allowlists_collection = db['whitelists']  # collection name same as before

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    async for member in client.get_chat_members(
        chat_id,
        filter=enums.ChatMembersFilter.ADMINISTRATORS
    ):
        if member.user.id == user_id:
            return True
    return False

async def get_config(chat_id: int):
    doc = await punishments_collection.find_one({'chat_id': chat_id})
    if doc:
        return doc.get('mode', 'warn'), doc.get('limit', DEFAULT_WARNING_LIMIT), doc.get('penalty', DEFAULT_PUNISHMENT)
    return DEFAULT_CONFIG

async def update_config(chat_id: int, mode=None, limit=None, penalty=None):
    update = {}
    if mode is not None:
        update['mode'] = mode
    if limit is not None:
        update['limit'] = limit
    if penalty is not None:
        update['penalty'] = penalty
    if update:
        await punishments_collection.update_one(
            {'chat_id': chat_id},
            {'$set': update},
            upsert=True
        )

async def increment_warning(chat_id: int, user_id: int) -> int:
    await warnings_collection.update_one(
        {'chat_id': chat_id, 'user_id': user_id},
        {'$inc': {'count': 1}},
        upsert=True
    )
    doc = await warnings_collection.find_one({'chat_id': chat_id, 'user_id': user_id})
    return doc['count']

async def reset_warnings(chat_id: int, user_id: int):
    await warnings_collection.delete_one({'chat_id': chat_id, 'user_id': user_id})

# ================ Allowlist functions ================
async def is_allowlisted(chat_id: int, user_id: int) -> bool:
    doc = await allowlists_collection.find_one({'chat_id': chat_id, 'user_id': user_id})
    return bool(doc)

async def add_allowlist(chat_id: int, user_id: int):
    await allowlists_collection.update_one(
        {'chat_id': chat_id, 'user_id': user_id},
        {'$set': {'user_id': user_id}},
        upsert=True
    )

async def remove_allowlist(chat_id: int, user_id: int):
    await allowlists_collection.delete_one({'chat_id': chat_id, 'user_id': user_id})

async def get_allowlist(chat_id: int) -> list:
    cursor = allowlists_collection.find({'chat_id': chat_id})
    docs = await cursor.to_list(length=None)
    return [doc['user_id'] for doc in docs]


# Default settings for new chats (used by abuse/bio/nsfw modules)
def get_default_settings():
    return {
        "abuse_on": True,
        "nsfw_on": True,
        "bio_link_on": True,
        "clean_on": False,
        "delete_minutes": 30
    }
