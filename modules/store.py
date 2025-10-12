import json
import threading
from pathlib import Path

_LOCK = threading.Lock()
STORE_PATH = Path("data_store.json")

_default = {
  "chats": {},
  "users": {}
}

def _load():
    if STORE_PATH.exists():
        try:
            return json.loads(STORE_PATH.read_text(encoding="utf-8"))
        except:
            return _default.copy()
    return _default.copy()

def _save(data):
    with _LOCK:
        STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

def ensure_chat(chat_id):
    data = _load()
    sid = str(chat_id)
    if sid not in data["chats"]:
        data["chats"][sid] = {
            "clean_on": False,
            "delete_minutes": 60,
            "abuse_on": True,
            "nsfw_on": True
        }
        _save(data)

def get_chat(chat_id):
    data = _load()
    sid = str(chat_id)
    ensure_chat(chat_id)
    return data["chats"][sid]

def set_chat(chat_id, key, value):
    data = _load()
    sid = str(chat_id)
    ensure_chat(chat_id)
    data["chats"][sid][key] = value
    _save(data)

def add_warning(user_id):
    data = _load()
    uid = str(user_id)
    u = data["users"].setdefault(uid, {"warnings":0, "nsfw_history":[],"muted":False})
    u["warnings"] += 1
    _save(data)
    return u["warnings"]

def add_nsfw_event(user_id, ts):
    data = _load()
    uid = str(user_id)
    u = data["users"].setdefault(uid, {"warnings":0, "nsfw_history":[],"muted":False})
    u["nsfw_history"].append(ts)
    u["nsfw_history"] = u["nsfw_history"][-100:]
    _save(data)
    return u["nsfw_history"]

def set_muted(user_id):
    data = _load()
    uid = str(user_id)
    u = data["users"].setdefault(uid, {"warnings":0, "nsfw_history":[],"muted":False})
    u["muted"] = True
    _save(data)

def is_muted(user_id):
    data = _load()
    return data["users"].get(str(user_id), {}).get("muted", False)
