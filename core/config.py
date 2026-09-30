"""Central configuration for Autonomous Instagram Dual-Slot Carousel Pipeline."""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
STATE_DIR = BASE_DIR / "state"
MOCK_PREVIEW_DIR = BASE_DIR / "mock_preview"

LAST_PROCESSED_ID_FILE = BASE_DIR / "last_processed_id.txt"
USAGE_FILE = BASE_DIR / "usage.json"
RUN_STATE_FILE = BASE_DIR / "run_state.json"
HEARTBEAT_FILE = BASE_DIR / "heartbeat.txt"
NEWS_HISTORY_FILE = STATE_DIR / "news_history.json"

# Load .env file automatically if present
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip("'\""))


# Scheduling & Slots
SLOT1_HOUR = int(os.getenv("SLOT1_HOUR", "1"))      # 01:30 UTC / 07:00 IST (Morning Daily Edition)
FORCE_SLOT = os.getenv("FORCED_SLOT", "auto").lower() # "auto", "slot1"

# Image Generation Providers
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "")
POLLINATIONS_BASE_URL = os.getenv("POLLINATIONS_BASE_URL", "https://gen.pollinations.ai")
IMAGE_PROVIDER_ORDER = [
    p.strip().lower() for p in os.getenv("IMAGE_PROVIDER_ORDER", "pollinations,cloudflare,huggingface,pillow").split(",")
]
IMAGE_MODEL_PREFERENCE = [
    m.strip() for m in os.getenv("IMAGE_MODEL_PREFERENCE", "flux,zimage,klein").split(",")
]
POLLINATIONS_MIN_INTERVAL_S = float(os.getenv("POLLINATIONS_MIN_INTERVAL_S", "5.0"))
MAX_AI_IMAGES_PER_POST = int(os.getenv("MAX_AI_IMAGES_PER_POST", "10"))
POLLEN_RESERVE_BUFFER = float(os.getenv("POLLEN_RESERVE_BUFFER", "0.0"))

# Secondary Providers (Optional)
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID", "")
CF_API_TOKEN = os.getenv("CF_API_TOKEN", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Text Models & Vision
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3-flash-preview")
GEMINI_PROMPT_TEMPERATURE = float(os.getenv("GEMINI_PROMPT_TEMPERATURE", "0.4"))
POLLINATIONS_CHAT_MODEL = os.getenv("POLLINATIONS_CHAT_MODEL", "openai")

# Dimensions & Normalization
CAROUSEL_WIDTH = 1080
CAROUSEL_HEIGHT = 1350
STORY_WIDTH = 1080
STORY_HEIGHT = 1920
ENABLE_STORY_GENERATION = os.getenv("ENABLE_STORY_GENERATION", "false").lower() == "true"
ENABLE_TYPOGRAPHY_OVERLAY = os.getenv("ENABLE_TYPOGRAPHY_OVERLAY", "false").lower() == "true"
ENABLE_STEP4_PROCESSING = os.getenv("ENABLE_STEP4_PROCESSING", "false").lower() == "true"



# Safe zone margins
SAFE_MARGIN_X = 108  # 10% outer margin
SAFE_MARGIN_Y = 135  # 10% outer margin

# News Configuration
NEWS_MAX_AGE_HOURS = int(os.getenv("NEWS_MAX_AGE_HOURS", "24"))
NEWS_MAX_STORIES = 9
NEWS_MIN_STORIES = 5
NEWS_MAX_PER_CATEGORY = 3

SKIP_KEYWORDS = [
    "rape", "molestation", "suicide", "porn", "nude", "sexual",
    "murder", "lynching", "assault", "gore"
]

SENSITIVE_KEYWORDS = [
    "violence", "riot", "disaster", "earthquake", "flood",
    "crash", "explosion", "terror", "killed", "dead", "fatal", "tragedy"
]

NEWS_FEEDS = [
    # Google News (India Top Stories)
    {"name": "Google News", "url": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en", "category": "Top News"}
]

# Caption & Hashtag Pyramid
HASHTAG_TIER_COUNTS = {
    "niche": int(os.getenv("TIER_NICHE", "6")),
    "aesthetic": int(os.getenv("TIER_AESTHETIC", "6")),
    "cultural": int(os.getenv("TIER_CULTURAL", "5")),
    "utility": int(os.getenv("TIER_UTILITY", "6")),
    "discovery": int(os.getenv("TIER_DISCOVERY", "5"))
}
MAX_CAPTION_CHARS = 2200
BRAND_HANDLE = os.getenv("BRAND_HANDLE", "@YourChannel")

# Cloudinary & Meta
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "")
CLEANUP_RETENTION_DAYS = int(os.getenv("CLEANUP_RETENTION_DAYS", "7"))
IG_USER_ID = os.getenv("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v20.0")

# Telemetry & Admin Alerts
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ADMIN_BOT_TOKEN = os.getenv("TELEGRAM_ADMIN_BOT_TOKEN", TELEGRAM_BOT_TOKEN)
TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", TELEGRAM_CHAT_ID)
REQUIRE_APPROVAL = os.getenv("REQUIRE_APPROVAL", "false").lower() == "true"
