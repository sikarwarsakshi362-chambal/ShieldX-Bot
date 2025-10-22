import re
import os

# ======================= API & Bot Config =======================
API_ID = 26250263
API_HASH = "24b066ce7a9020dfbd69b4dc593993f1"
BOT_TOKEN = "7981496411:AAHSjcC62nEmpkA2xXMUT4Tl1X3_9xFtZDE"
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
