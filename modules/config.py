import os
import re
import redis.asyncio as aioredis

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

# ====================== Redis Config (Render Ready) ======================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis = aioredis.from_url(REDIS_URL, decode_responses=True)

# ====================== Default Bot Config ======================
DEFAULT_WARNING_LIMIT = 3
DEFAULT_PUNISHMENT = "mute"  # Options: "mute", "ban"
DEFAULT_CONFIG = ("warn", DEFAULT_WARNING_LIMIT, DEFAULT_PUNISHMENT)

# Test connection (async) to Redis
async def test_redis_connection():
    try:
        pong = await redis.ping()
        if pong:
            print("✅ Redis connected successfully!")
    except Exception as e:
        print("❌ Redis connection failed:", e)

# ======================= Debug & Features =======================
DEBUG = False  # optional, True for debug prints

# Default feature toggles
DEFAULT_FEATURES = {
    "abuse_on": True,
    "nsfw_on": True,
    "bio_link_on": True
}
