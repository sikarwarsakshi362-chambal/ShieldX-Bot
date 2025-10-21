# modules/config.py
import re

# ======================= API & Bot Config =======================
API_ID = 26250263
API_HASH = "24b066ce7a9020dfbd69b4dc593993f1"
BOT_TOKEN = "7981496411:AAHSjcC62nEmpkA2xXMUT4Tl1X3_9xFtZDE"
ADD_TO_GROUP_USERNAME = "shieldprotector_bot"
SUPPORT_LINK = "https://t.me/+yGiJaSdHDoRlN2Zl"
SESSION_FILE = "ShieldX.session"

# ======================= URL Pattern =======================
# Regex pattern to detect URLs in user bios
URL_PATTERN = re.compile(
    r"(https?://|www\.)[a-zA-Z0-9.\-]+(\.[a-zA-Z]{2,})+(/[a-zA-Z0-9._%+-]*)*"
)

# ====================== MongoDB Config (Auto Detect) ======================
import socket

LOCAL_MONGO_URI = "mongodb://localhost:27017/shieldx_db"
CLOUD_MONGO_URI = "mongodb+srv://<user>:<password>@cluster0.mongodb.net/mydatabase?retryWrites=true&w=majority"

def get_mongo_uri():
    try:
        # try to connect to localhost MongoDB
        sock = socket.create_connection(("localhost", 27017), timeout=2)
        sock.close()
        print("✅ Using Local MongoDB (localhost:27017)")
        return LOCAL_MONGO_URI
    except Exception:
        print("☁️ Local MongoDB not found, using Cloud MongoDB")
        return CLOUD_MONGO_URI

MONGO_URI = get_mongo_uri()

# Default warning & punishment config
DEFAULT_WARNING_LIMIT = 3
DEFAULT_PUNISHMENT = "mute"  # Options: "mute", "ban"
DEFAULT_CONFIG = ("warn", DEFAULT_WARNING_LIMIT, DEFAULT_PUNISHMENT)


# ======================= Debug & Features =======================
DEBUG = False  # optional, True for debug prints

# Default feature toggles
DEFAULT_FEATURES = {
    "abuse_on": True,
    "nsfw_on": True,
    "bio_link_on": True
}
