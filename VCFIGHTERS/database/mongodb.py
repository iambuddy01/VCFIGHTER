# ╔══════════════════════════════════════════════════════════════╗
# ║         VCFIGHTER — MongoDB Database Layer                   ║
# ║         File: VCFIGHTERS/database/mangodb.py                 ║
# ╚══════════════════════════════════════════════════════════════╝

import time
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument

import Config
from VCFIGHTERS.logging import LOGGER

log = LOGGER("MongoDB")

# ─────────────────────────────────────────────
# CONNECTION
# ─────────────────────────────────────────────

_client: AsyncIOMotorClient | None = None
db      = None   # exposed so Settings.py can ping it directly


async def init_db():
    """Connect to MongoDB. Called once at startup from __main__.py"""
    global _client, db
    _client = AsyncIOMotorClient(Config.MONGO_URI)
    db      = _client[Config.DB_NAME if hasattr(Config, "DB_NAME") else "vcfighter"]
    # Verify connection
    await db.command("ping")
    log.info("✅ MongoDB connected successfully")


def _col(name: str):
    """Shortcut — returns a collection handle."""
    if db is None:
        raise RuntimeError("DB not initialized. Call init_db() first.")
    return db[name]


# ══════════════════════════════════════════════
#  COLLECTION: settings
#  Fields: mode, logger_chat, pytgcalls { stream_type, quality, noise_suppression }
# ══════════════════════════════════════════════

_SETTINGS_ID = "global"

_DEFAULT_SETTINGS = {
    "_id":         _SETTINGS_ID,
    "mode":        "dm",
    "logger_chat": None,
    "pytgcalls": {
        "stream_type":       "audio",
        "quality":           "medium",
        "noise_suppression": False,
    },
}


async def get_settings() -> dict:
    doc = await _col("settings").find_one({"_id": _SETTINGS_ID})
    if not doc:
        await _col("settings").insert_one(_DEFAULT_SETTINGS.copy())
        return _DEFAULT_SETTINGS.copy()
    return doc


async def save_settings(fields: dict):
    """Partial update — only pass fields you want to change."""
    await _col("settings").update_one(
        {"_id": _SETTINGS_ID},
        {"$set": fields},
        upsert=True,
    )


async def get_mode() -> str:
    s = await get_settings()
    return s.get("mode", "dm")


async def set_mode(mode: str):
    await save_settings({"mode": mode})


async def get_logger_chat() -> int | None:
    s = await get_settings()
    return s.get("logger_chat")


async def get_pytgcalls_settings() -> dict:
    s = await get_settings()
    return s.get("pytgcalls", _DEFAULT_SETTINGS["pytgcalls"].copy())


async def save_pytgcalls_settings(pytg: dict):
    await save_settings({"pytgcalls": pytg})


# ══════════════════════════════════════════════
#  COLLECTION: ffmpeg
#  Fields: volume, compressor, limiter, bass, pitch, echo
# ══════════════════════════════════════════════

_FFMPEG_ID = "global"

_DEFAULT_FFMPEG = {
    "_id":        _FFMPEG_ID,
    "volume":     1.0,
    "compressor": False,
    "limiter":    False,
    "bass":       0,
    "pitch":      "normal",
    "echo":       False,
}


async def get_ffmpeg_settings() -> dict:
    doc = await _col("ffmpeg").find_one({"_id": _FFMPEG_ID})
    if not doc:
        await _col("ffmpeg").insert_one(_DEFAULT_FFMPEG.copy())
        return _DEFAULT_FFMPEG.copy()
    return doc


async def save_ffmpeg_settings(fields: dict):
    """Pass full dict or partial fields."""
    await _col("ffmpeg").update_one(
        {"_id": _FFMPEG_ID},
        {"$set": fields},
        upsert=True,
    )


async def reset_ffmpeg_settings():
    await _col("ffmpeg").replace_one(
        {"_id": _FFMPEG_ID},
        _DEFAULT_FFMPEG.copy(),
        upsert=True,
    )


# ══════════════════════════════════════════════
#  COLLECTION: userbots
#  Fields: session_string, phone, added_by, added_at, active
# ══════════════════════════════════════════════

async def get_all_userbots() -> list[dict]:
    return await _col("userbots").find().to_list(length=None)


async def get_active_userbots() -> list[dict]:
    return await _col("userbots").find({"active": True}).to_list(length=None)


async def get_all_sessions() -> list[str]:
    """Returns list of session_strings — used by __main__.py at startup."""
    docs = await _col("userbots").find({}).to_list(length=None)
    return [d["session_string"] for d in docs if d.get("session_string")]


async def get_userbot_by_phone(phone: str) -> dict | None:
    return await _col("userbots").find_one({"phone": phone})


async def get_userbot_by_session(session: str) -> dict | None:
    return await _col("userbots").find_one({"session_string": session})


async def add_userbot(data: dict):
    """
    data = {
        "session_string": "...",
        "phone": "+91...",
        "added_by": user_id,
        "added_at": timestamp,
        "active": True
    }
    """
    existing = await get_userbot_by_session(data["session_string"])
    if existing:
        await _col("userbots").update_one(
            {"session_string": data["session_string"]},
            {"$set": data},
        )
    else:
        await _col("userbots").insert_one(data)


async def delete_userbot(session: str):
    await _col("userbots").delete_one({"session_string": session})


async def delete_all_userbots():
    await _col("userbots").delete_many({})


async def set_userbot_active(session: str, active: bool):
    await _col("userbots").update_one(
        {"session_string": session},
        {"$set": {"active": active}},
    )


async def userbot_count() -> int:
    return await _col("userbots").count_documents({})


async def active_userbot_count() -> int:
    return await _col("userbots").count_documents({"active": True})


# ══════════════════════════════════════════════
#  COLLECTION: targets
#  Fields: chat_id, invite_link, userbots_joined, added_at
# ══════════════════════════════════════════════

async def get_all_targets() -> list[dict]:
    return await _col("targets").find().to_list(length=None)


async def get_target_by_chat_id(chat_id: int) -> dict | None:
    return await _col("targets").find_one({"chat_id": chat_id})


async def get_primary_target() -> dict | None:
    """Returns the most recently added target."""
    return await _col("targets").find_one(sort=[("added_at", -1)])


async def add_target(data: dict):
    """
    data = {
        "chat_id": -100xxx,
        "invite_link": "t.me/+xxx",
        "userbots_joined": ["+91..."],
        "added_at": timestamp
    }
    """
    existing = await get_target_by_chat_id(data["chat_id"])
    if existing:
        await _col("targets").update_one(
            {"chat_id": data["chat_id"]},
            {"$set": data},
        )
    else:
        await _col("targets").insert_one(data)


async def delete_target(chat_id: int):
    await _col("targets").delete_one({"chat_id": chat_id})


async def delete_all_targets():
    await _col("targets").delete_many({})


async def update_target_joined(chat_id: int, phone: str):
    """Add a phone to userbots_joined list for a target (no duplicates)."""
    await _col("targets").update_one(
        {"chat_id": chat_id},
        {"$addToSet": {"userbots_joined": phone}},
    )


# ══════════════════════════════════════════════
#  COLLECTION: sudo
#  Fields: user_id, added_by, added_at
# ══════════════════════════════════════════════

async def get_sudo_users() -> list[int]:
    """Returns list of sudo user_ids."""
    docs = await _col("sudo").find().to_list(length=None)
    return [d["user_id"] for d in docs]


async def get_sudo_users_full() -> list[dict]:
    """Returns full sudo docs (with added_by, added_at)."""
    return await _col("sudo").find().to_list(length=None)


async def add_sudo_user(data: dict):
    """
    data = {
        "user_id":  123456789,
        "added_by": owner_id,
        "added_at": timestamp
    }
    """
    existing = await _col("sudo").find_one({"user_id": data["user_id"]})
    if not existing:
        await _col("sudo").insert_one(data)


async def remove_sudo_user(user_id: int):
    await _col("sudo").delete_one({"user_id": user_id})


async def is_sudo_user(user_id: int) -> bool:
    doc = await _col("sudo").find_one({"user_id": user_id})
    return doc is not None


# ══════════════════════════════════════════════
#  COLLECTION: recordings
#  Fields: file_path, user_id, timestamp
#  Note: Temp files — auto-deleted after use
# ══════════════════════════════════════════════

async def save_recording(file_path: str, user_id: int) -> str:
    """Save a recording entry. Returns inserted _id as string."""
    result = await _col("recordings").insert_one({
        "file_path": file_path,
        "user_id":   user_id,
        "timestamp": int(time.time()),
    })
    return str(result.inserted_id)


async def get_recording(user_id: int) -> dict | None:
    """Get latest recording for a user."""
    return await _col("recordings").find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)],
    )


async def delete_recording(file_path: str):
    """Remove recording entry from DB (call after file deleted from disk)."""
    await _col("recordings").delete_one({"file_path": file_path})


async def delete_all_recordings_for_user(user_id: int):
    await _col("recordings").delete_many({"user_id": user_id})


async def cleanup_old_recordings(older_than_seconds: int = 3600):
    """Delete recording entries older than X seconds (default 1 hour)."""
    cutoff = int(time.time()) - older_than_seconds
    result = await _col("recordings").delete_many({"timestamp": {"$lt": cutoff}})
    if result.deleted_count:
        log.info(f"🧹 Cleaned up {result.deleted_count} old recording(s)")


# ══════════════════════════════════════════════
#  UTILITY — Generic helpers
# ══════════════════════════════════════════════

async def get_value(collection: str, key: str, default: Any = None) -> Any:
    """Generic key-value get from any collection (for future use)."""
    doc = await _col(collection).find_one({"_id": key})
    return doc.get("value", default) if doc else default


async def set_value(collection: str, key: str, value: Any):
    """Generic key-value set in any collection (for future use)."""
    await _col(collection).update_one(
        {"_id": key},
        {"$set": {"value": value}},
        upsert=True,
    )


async def db_stats() -> dict:
    """Returns basic DB stats — used by Pings panel."""
    return {
        "userbots":  await userbot_count(),
        "active_ub": await active_userbot_count(),
        "targets":   await _col("targets").count_documents({}),
        "sudo":      await _col("sudo").count_documents({}),
}
  
