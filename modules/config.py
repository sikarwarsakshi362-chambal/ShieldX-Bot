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

# ====================== MongoDB Config (Render Ready) ======================
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Local MongoDB URI for Render
MONGO_URI = "mongodb://shieldx_bot:shieldx_bot@mongo:27017/shieldxdb"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

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
