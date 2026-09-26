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
FESTIVALS_FILE = BASE_DIR / "festivals.json"
EVERGREEN_THEMES_FILE = BASE_DIR / "evergreen_themes.json"
NEWS_HISTORY_FILE = STATE_DIR / "news_history.json"

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
POLLINATIONS_CHAT_MODEL = os.getenv("POLLINATIONS_CHAT_MODEL", "openai")

# Dimensions & Normalization
CAROUSEL_WIDTH = 1080
CAROUSEL_HEIGHT = 1350
STORY_WIDTH = 1080
STORY_HEIGHT = 1920

# Safe zone margins
SAFE_MARGIN_X = 108  # 10% outer margin
SAFE_MARGIN_Y = 135  # 10% outer margin

# News Configuration
NEWS_MAX_AGE_HOURS = int(os.getenv("NEWS_MAX_AGE_HOURS", "24"))
NEWS_MAX_STORIES = 10
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
    # Google News RSS (India edition)
    {"name": "Google News India", "url": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en", "category": "Top"},
    {"name": "Google News National", "url": "https://news.google.com/rss/headlines/section/topic/NATION?hl=en-IN&gl=IN&ceid=IN:en", "category": "India"},
    {"name": "Google News Business", "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-IN&gl=IN&ceid=IN:en", "category": "Business"},
    {"name": "Google News Technology", "url": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-IN&gl=IN&ceid=IN:en", "category": "Technology"},
    {"name": "Google News Sports", "url": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-IN&gl=IN&ceid=IN:en", "category": "Sports"},
    # Publisher Direct RSS Feeds
    {"name": "The Hindu", "url": "https://www.thehindu.com/news/national/feeder/default.rss", "category": "India"},
    {"name": "Indian Express", "url": "https://indianexpress.com/section/india/feed/", "category": "India"},
    {"name": "Hindustan Times", "url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "category": "India"},
    {"name": "NDTV", "url": "https://feeds.feedburner.com/ndtvnews-india-news", "category": "India"},
    {"name": "Times of India", "url": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms", "category": "Top"}
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
IG_USER_ID = os.getenv("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v20.0")

# Telemetry
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
REQUIRE_APPROVAL = os.getenv("REQUIRE_APPROVAL", "false").lower() == "true"
