import os
from pyrogram import Client, enums
from config import DEFAULT_CONFIG, DEFAULT_WARNING_LIMIT, DEFAULT_PUNISHMENT
from tinydb import TinyDB, Query

# TinyDB file
db = TinyDB('data.json')

# ==================== ADMIN CHECK ====================
async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
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
    config_table = db.table('config')
    config = config_table.get(Query().chat_id == chat_id)
    if config:
        return config.get('mode', 'warn'), config.get('limit', 3), config.get('penalty', 'mute')
    return 'warn', 3, 'mute'

async def update_config(chat_id: int, mode=None, limit=None, penalty=None):
    config_table = db.table('config')
    config = config_table.get(Query().chat_id == chat_id) or {'chat_id': chat_id}
    if mode: config['mode'] = mode
    if limit: config['limit'] = limit
    if penalty: config['penalty'] = penalty
    config_table.upsert(config, Query().chat_id == chat_id)

# ==================== WARNINGS ====================
async def increment_warning(chat_id: int, user_id: int) -> int:
    warnings_table = db.table('warnings')
    key = f"{chat_id}:{user_id}"
    warning = warnings_table.get(Query().key == key) or {'key': key, 'count': 0}
    warning['count'] += 1
    warnings_table.upsert(warning, Query().key == key)
    return warning['count']

async def reset_warnings(chat_id: int, user_id: int):
    warnings_table = db.table('warnings')
    key = f"{chat_id}:{user_id}"
    warnings_table.remove(Query().key == key)

# ==================== ALLOWLIST ====================
async def is_allowlisted(chat_id: int, user_id: int) -> bool:
    allowlist_table = db.table('allowlists')
    allowlist = allowlist_table.get(Query().chat_id == chat_id)
    return allowlist and user_id in allowlist.get('users', [])

async def add_allowlist(chat_id: int, user_id: int):
    allowlist_table = db.table('allowlists')
    allowlist = allowlist_table.get(Query().chat_id == chat_id) or {'chat_id': chat_id, 'users': []}
    if user_id not in allowlist['users']:
        allowlist['users'].append(user_id)
    allowlist_table.upsert(allowlist, Query().chat_id == chat_id)

async def remove_allowlist(chat_id: int, user_id: int):
    allowlist_table = db.table('allowlists')
    allowlist = allowlist_table.get(Query().chat_id == chat_id)
    if allowlist and user_id in allowlist.get('users', []):
        allowlist['users'].remove(user_id)
        allowlist_table.upsert(allowlist, Query().chat_id == chat_id)

async def get_allowlist(chat_id: int) -> list:
    allowlist_table = db.table('allowlists')
    allowlist = allowlist_table.get(Query().chat_id == chat_id)
    return allowlist.get('users', []) if allowlist else []
