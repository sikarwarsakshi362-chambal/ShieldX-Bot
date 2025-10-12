# modules/config.py - simple defaults
DEFAULT_DELETE_MINUTES = 60

def default_chat_settings():
    return {
        "clean_on": False,
        "delete_minutes": DEFAULT_DELETE_MINUTES,
        "abuse_on": True,
        "nsfw_on": True
    }
