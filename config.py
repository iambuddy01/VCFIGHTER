import os
import sys

from dotenv import load_dotenv

# ══════════════════════════════════════════════════════════════
#  VCFIGHTER — Config
#  Loads from .env file or system environment variables
#  Copy .env.example → .env and fill in your values
# ══════════════════════════════════════════════════════════════

load_dotenv()


def _get(key: str, default=None, required: bool = False):
    val = os.environ.get(key, default)
    if required and not val:
        print(f"[VCFIGHTER] ❌ Missing required config: {key}")
        sys.exit(1)
    return val


def _int(key: str, default: int, required: bool = False) -> int:
    val = _get(key, str(default), required)
    try:
        return int(val)
    except (TypeError, ValueError):
        print(f"[VCFIGHTER] ⚠️  {key} must be an integer. Using default: {default}")
        return default


def _bool(key: str, default: bool = False) -> bool:
    val = _get(key, str(default)).strip().lower()
    return val in ("true", "1", "yes", "on")


def _list(key: str, default: list | None = None) -> list[int]:
    raw = _get(key, "")
    if not raw:
        return default or []
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError:
        print(f"[VCFIGHTER] ⚠️  {key} must be comma-separated integers.")
        return default or []


# ══════════════════════════════════════════════════════════════
#  REQUIRED — Telegram
# ══════════════════════════════════════════════════════════════

API_ID    = _int("API_ID",    0, required=True)
API_HASH  = _get("API_HASH",  required=True)
BOT_TOKEN = _get("BOT_TOKEN", required=True)

# ══════════════════════════════════════════════════════════════
#  REQUIRED — Database
# ══════════════════════════════════════════════════════════════

MONGO_URI = _get("MONGO_URI", required=True)
DB_NAME   = _get("DB_NAME",   default="vcfighter")

# ══════════════════════════════════════════════════════════════
#  REQUIRED — Owner
# ══════════════════════════════════════════════════════════════

OWNER_ID = _int("OWNER_ID", 0, required=True)

# ══════════════════════════════════════════════════════════════
#  OPTIONAL — Sudo Users
#  Comma-separated IDs: 123456,789012
# ══════════════════════════════════════════════════════════════

SUDO_USERS: list[int] = _list("SUDO_USERS", default=[])

# ══════════════════════════════════════════════════════════════
#  OPTIONAL — Logger / Log Channel
# ══════════════════════════════════════════════════════════════

LOG_CHANNEL = _int("LOG_CHANNEL", 0)

# ══════════════════════════════════════════════════════════════
#  OPTIONAL — PyTgCalls defaults
#  These are overridden by /config panel values in DB
# ══════════════════════════════════════════════════════════════

DEFAULT_STREAM_TYPE       = _get("DEFAULT_STREAM_TYPE",       default="audio")    # audio | video
DEFAULT_QUALITY           = _get("DEFAULT_QUALITY",           default="medium")   # low | medium | high
DEFAULT_NOISE_SUPPRESSION = _bool("DEFAULT_NOISE_SUPPRESSION", default=False)

# ══════════════════════════════════════════════════════════════
#  OPTIONAL — FFmpeg defaults
#  Overridden by /config → FFmpeg panel values in DB
# ══════════════════════════════════════════════════════════════

DEFAULT_VOLUME     = float(_get("DEFAULT_VOLUME",     default="1.0"))   # 1.0 = 100%
DEFAULT_BASS       = _int("DEFAULT_BASS",             default=0)        # 0 to 40
DEFAULT_PITCH      = _get("DEFAULT_PITCH",            default="normal") # normal | demon | chipmunk
DEFAULT_ECHO       = _bool("DEFAULT_ECHO",            default=False)
DEFAULT_COMPRESSOR = _bool("DEFAULT_COMPRESSOR",      default=False)
DEFAULT_LIMITER    = _bool("DEFAULT_LIMITER",         default=False)

# ══════════════════════════════════════════════════════════════
#  OPTIONAL — VC Behaviour
# ══════════════════════════════════════════════════════════════

DEFAULT_MODE      = _get("DEFAULT_MODE", default="dm")    # dm | auto
RECORDINGS_DIR    = _get("RECORDINGS_DIR", default="recordings")
MAX_RECORDING_AGE = _int("MAX_RECORDING_AGE", default=3600)  # seconds — cleanup old recordings

# ══════════════════════════════════════════════════════════════
#  OPTIONAL — Startup String Sessions (comma-separated)
#  Fallback if no userbots in DB yet
# ══════════════════════════════════════════════════════════════

STARTUP_SESSIONS: list[str] = [
    s.strip()
    for s in _get("STARTUP_SESSIONS", default="").split(",")
    if s.strip()
]

# ══════════════════════════════════════════════════════════════
#  OPTIONAL — Branding
# ══════════════════════════════════════════════════════════════

BOT_NAME    = _get("BOT_NAME",    default="VCFighter")
BOT_VERSION = _get("BOT_VERSION", default="2.0")
SUPPORT_URL = _get("SUPPORT_URL", default="https://t.me/Zcziiy")
SOURCE_URL  = _get("SOURCE_URL",  default="https://github.com/YOURNAME/VCFIGHTER")

# ══════════════════════════════════════════════════════════════
#  DERIVED / CONSTANTS
# ══════════════════════════════════════════════════════════════

AUDIO_QUALITIES = {
    "low":    {"bitrate": 32000,  "channels": 1},
    "medium": {"bitrate": 48000,  "channels": 2},
    "high":   {"bitrate": 96000,  "channels": 2},
}

PITCH_RATES = {
    "normal":   1.0,
    "demon":    0.7,
    "chipmunk": 1.6,
}

BASS_LEVELS = {
    0:  "Normal",
    15: "Heavy",
    30: "Earthquake",
    40: "💀 MAX",
}

# ══════════════════════════════════════════════════════════════
#  OPTIONAL — Support & Community Links
# ══════════════════════════════════════════════════════════════

SUPPORT_CHAT    = _get("SUPPORT_CHAT",    default="https://t.me/Zcziiy")       # Support group link
SUPPORT_CHANNEL = _get("SUPPORT_CHANNEL", default="https://t.me/Zcziiy")       # Updates channel link

# ══════════════════════════════════════════════════════════════
#  OPTIONAL — Bot Pictures (used in /start, /help etc)
#  Comma-separated direct image URLs
# ══════════════════════════════════════════════════════════════

_raw_pics = _get("VC_PICS", default="")
VC_PICS: list[str] = (
    [p.strip() for p in _raw_pics.split(",") if p.strip()]
    if _raw_pics else [
        "https://files.catbox.moe/eje8y8.jpeg",
        "https://files.catbox.moe/ey2jzp.jpeg",
        "https://files.catbox.moe/ah5y0f.jpeg",
        "https://files.catbox.moe/we4yju.jpeg",
    ]
)

# ══════════════════════════════════════════════════════════════
#  OPTIONAL — Start Animation
# ══════════════════════════════════════════════════════════════

START_FIRE_EFFECT  = _bool("START_FIRE_EFFECT",  default=True)   # Fire effect on /start
FIRE_FRAME_DELAY   = float(_get("FIRE_FRAME_DELAY", default="0.4"))
DING_DONG_DELETE   = _bool("DING_DONG_DELETE",   default=True)   # Delete animation after
