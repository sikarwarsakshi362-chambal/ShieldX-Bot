import re
import os
import motor.motor_asyncio

# ======================= API & Bot Config =======================
API_ID = 26250263
API_HASH = "24b066ce7a9020dfbd69b4dc593993f1"
BOT_TOKEN = "7981496411:AAHSjcC62nEmpkA2xXMUT4Tl1X3_9xFtZDE"
ADD_TO_GROUP_USERNAME = "shieldprotector_bot"
SUPPORT_LINK = "https://t.me/+yGiJaSdHDoRlN2Zl"
SESSION_FILE = "ShieldX.session"

# ======================= MongoDB Config =======================
mongo_url = os.environ.get("MONGO_URI")

try:
    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
    db = client["mydb"]
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

# ======================= Default Config =======================
DEFAULT_WARNING_LIMIT = 3
DEFAULT_PUNISHMENT = "mute"  # Options: "mute", "ban"
DEFAULT_CONFIG = ("warn", DEFAULT_WARNING_LIMIT, DEFAULT_PUNISHMENT)

# ======================= Regex Pattern =======================
URL_PATTERN = re.compile(
    r'(https?://|www\.)[a-zA-Z0-9.\-]+(\.[a-zA-Z]{2,})+(/[a-zA-Z0-9._%+-]*)*'
)
