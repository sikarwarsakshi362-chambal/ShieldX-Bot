import re
import os

# ======================= API & Bot Config =======================
# Get environment variables (required for Heroku / Render / VPS)
API_ID = int(os.environ.get("API_ID", "12345678"))  # Your Telegram API ID
API_HASH = os.environ.get("API_HASH", "12345678abcd")  # Your Telegram API Hash
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7267436522:XXXXXXXXXXXXXXXXXX")  # Your Bot Token# Owner ID for privileged commands like /broadcast
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))  # Set this to your Telegram user ID
ADD_TO_GROUP_USERNAME = "shieldprotector_bot"
SUPPORT_LINK = "https://t.me/+yGiJaSdHDoRlN2Zl"
SESSION_FILE = "ShieldX.session"

# ======================= Local JSON Database =======================
# MongoDB ki jagah ye file use hogi (auto create ho jaayegi)
DATA_FILE = "data.json"

# ======================= Default Config =======================
DEFAULT_WARNING_LIMIT = 3
DEFAULT_PUNISHMENT = "mute"  # Options: "mute", "ban"

# Original tuple ko dictionary se replace kar diya
DEFAULT_CONFIG = {
    "warn_type": "warn",
    "warning_limit": DEFAULT_WARNING_LIMIT,
    "punishment": DEFAULT_PUNISHMENT
}

# ======================= Regex Pattern =======================
URL_PATTERN = re.compile(
    r'(https?://|www\.)[a-zA-Z0-9.\-]+(\.[a-zA-Z]{2,})+(/[a-zA-Z0-9._%+-]*)*'
)
