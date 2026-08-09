import asyncio
import os
import time
from typing import Optional

from pyrogram import filters as pyro_filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from VCFIGHTERS.core.bot import app
from VCFIGHTERS.core.call import vc
from VCFIGHTERS.database.mangodb import (
    get_mode,
    get_primary_target,
    save_recording,
    delete_recording,
)
from VCFIGHTERS.logging import LOGGER
from VCFIGHTERS.FIGHTERS.sudo import is_authorized, is_owner, is_sudo

log = LOGGER("Voice")

REC_DIR = "recordings"
os.makedirs(REC_DIR, exist_ok=True)

_auto_tracking: dict[int, dict] = {}
_dm_current: dict[int, str] = {}


async def _get_target_chat_id() -> Optional[int]:
    target = await get_primary_target()
    if not target:
        log.warning("⚠️ No target set. Use /config → Set Target first.")
        return None
    return target["chat_id"]


def _cleanup_old_recording(user_id: int):
    track    = _auto_tracking.get(user_id, {})
    old_path = track.get("rec_path")
    if old_path and os.path.exists(old_path):
        try:
            os.remove(old_path)
            log.info(f"🧹 Old recording deleted: {old_path}")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
#  AUTO MODE — ASSISTS AUDIO
#  Assists/Audios.mp3 use karo, fallback silent
# ══════════════════════════════════════════════════════════════

_ASSISTS_AUDIO = "VCFIGHTERS/Assists/Audios.mp3"
_SILENT_PATH   = "VCFIGHTERS/Assists/silent.ogg"


async def _ensure_silent_audio() -> str:
    if not os.path.exists(_SILENT_PATH):
        log.info("🔇 Generating silent fallback audio...")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", "86400",
            "-c:a", "libvorbis",
            _SILENT_PATH,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
    return _SILENT_PATH


async def _get_ready_audio() -> str:
    """
    Auto mode join ke liye audio decide karo.
    1. Assists/Audios.mp3  (agar valid file hai >1KB)
    2. Silent OGG fallback
    """
    if os.path.exists(_ASSISTS_AUDIO) and os.path.getsize(_ASSISTS_AUDIO) > 1024:
        log.info(f"🎵 Using Assists audio → {_ASSISTS_AUDIO}")
        return _ASSISTS_AUDIO
    log.info("🔇 Assists/Audios.mp3 invalid → silent fallback")
    return await _ensure_silent_audio()


# ══════════════════════════════════════════════════════════════
#  VC READY JOIN
# ══════════════════════════════════════════════════════════════

async def vc_join_ready() -> tuple[bool, str]:
    target = await get_primary_target()
    if not target:
        return False, "⚠️ ᴛᴀʀɢєᴛ sєᴛ ηᴀнιιη нᴀι! /config → ˹ 𝐓ᴀʀɢєᴛ ˼"

    chat_id = target["chat_id"]

    if chat_id in vc._active_ub:
        return True, "✅ ᴜsєʀʙᴏᴛ ρнʟє sє нι ᴠᴄ ϻєιη нᴀι!"

    ready_audio = await _get_ready_audio()
    success     = await vc.play_loop(chat_id, ready_audio)

    if success:
        log.info(f"📡 Userbot joined VC → chat {chat_id} | audio: {ready_audio}")
        return True, "✅ ᴜsєʀʙᴏᴛ ᴊᴏιη нᴏ ɢᴀʏᴀ ᴠᴄ ϻєιη!\n🎙️ ᴀʙ ᴀᴜᴛᴏ ϻᴏᴅє ϻιᴄ sᴜηєɢᴀ."
    else:
        return False, "❌ ᴠᴄ ϻєιη ᴊᴏιη ηᴀнιιη нᴏ sᴋᴀ. ᴄнєᴄᴋ ᴋᴀʀᴏ ᴋι ᴜsєʀʙᴏᴛ ᴀᴄᴛιᴠє нᴀι."


# ══════════════════════════════════════════════════════════════
#  AUTO MODE — RECORDING
# ══════════════════════════════════════════════════════════════

async def _start_recording(user_id: int, chat_id: int) -> str:
    timestamp = int(time.time())
    rec_path  = os.path.join(REC_DIR, f"rec_{user_id}_{timestamp}.ogg")
    await save_recording(rec_path, user_id)
    _auto_tracking[user_id] = {"chat_id": chat_id, "recording": True, "rec_path": rec_path}
    log.info(f"🎙️ Recording started → {rec_path}")
    return rec_path


async def _stop_recording(user_id: int) -> Optional[str]:
    track = _auto_tracking.get(user_id)
    if not track or not track.get("recording"):
        return None
    track["recording"] = False
    rec_path = track.get("rec_path")
    if rec_path and os.path.exists(rec_path):
        size = os.path.getsize(rec_path)
        log.info(f"🎙️ Recording stopped → {rec_path} ({size} bytes)")
        return rec_path if size > 0 else None
    return None


# ══════════════════════════════════════════════════════════════
#  AUTO MODE — PARTICIPANT MONITOR
# ══════════════════════════════════════════════════════════════

async def register_participant_handlers():
    from pytgcalls import filters as call_filters
    from pytgcalls.types import UpdatedGroupCallParticipant

    if not vc._instances:
        log.warning("⚠️ No PyTgCalls instances — participant handlers NOT registered")
        return

    for session, pytg in vc._instances.items():

        @pytg.on_update(call_filters.call_participant())
        async def _on_participant_change(_, update: UpdatedGroupCallParticipant):
            mode = await get_mode()
            if mode != "auto":
                return

            participant = update.participant
            uid = participant.user_id
            if not (is_owner(uid) or await is_sudo(uid)):
                return

            chat_id       = update.chat_id
            is_muted      = participant.muted
            track         = _auto_tracking.get(uid, {})
            was_recording = track.get("recording", False)

            if not is_muted and not was_recording:
                log.info(f"🎙️ {uid} mic ON → recording start")
                _cleanup_old_recording(uid)
                await _start_recording(uid, chat_id)

            elif is_muted and was_recording:
                log.info(f"🔇 {uid} mic OFF → playing recording")
                rec_path = await _stop_recording(uid)
                if not rec_path:
                    log.warning("⚠️ Recording empty, skipping")
                    return

                # NOTE: the current pytgcalls delivers one participant per
                # update (no more `update.participants` list), so we can no
                # longer check whether some OTHER participant is screen
                # sharing at this instant. Using this participant's own
                # `screen_sharing` state instead — closest available signal.
                screen_sharing = participant.screen_sharing
                await vc.play_loop(chat_id=chat_id, file_path=rec_path, is_video=screen_sharing)
                log.info(f"{'📺 video+audio' if screen_sharing else '🔊 audio'} loop → chat {chat_id}")

        log.info(f"✅ Participant handler registered → ...{session[-10:]}")


# ══════════════════════════════════════════════════════════════
#  DM MODE — COMMON PLAY HELPER
#  Voice note, Audio file (MP3/M4A/WAV) — sab yahan aate hain
# ══════════════════════════════════════════════════════════════

def _dm_stop_kb(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏹️ sᴛᴏρ ᴠᴄ", callback_data=f"dm_stop_{chat_id}"),
    ]])


async def _handle_dm_play(client, message: Message, uid: int):
    """
    Audio ya voice note download karke VC mein play karo.
    10 min+ files bhi support hain.
    """
    chat_id = await _get_target_chat_id()
    if not chat_id:
        await message.reply(
            "⚠️ **ηᴏ ᴛᴀʀɢєᴛ sєᴛ!**\n"
            "ᴜsє `/config` → `˹ 𝐓ᴀʀɢєᴛ ˼` ғιʀsᴛ."
        )
        return

    # Media object nikalo
    media = message.voice or message.audio or message.video_note or message.document
    if not media:
        await message.reply("⚠️ **ᴋᴏι ᴀᴜᴅιᴏ/ᴠᴏιᴄє ηᴏᴛє ηᴀнιιη ϻιʟᴀ.**")
        return

    # Extension decide karo
    if message.voice or message.video_note:
        ext = "ogg"
    elif message.audio:
        fname = getattr(message.audio, "file_name", None) or "audio.mp3"
        ext   = fname.rsplit(".", 1)[-1] if "." in fname else "mp3"
    else:
        ext = "mp3"

    timestamp = int(time.time())
    dl_path   = os.path.join(REC_DIR, f"dm_{uid}_{timestamp}.{ext}")

    status_msg = await message.reply("⏳ **ᴅᴏᴡηʟᴏᴀᴅιηɢ...**")

    try:
        await message.download(file_name=dl_path)
        log.info(f"⬇️ Downloaded → {dl_path}")
    except Exception as e:
        log.error(f"❌ Download failed: {e}")
        await status_msg.edit("❌ **ᴅᴏᴡηʟᴏᴀᴅ ғᴀιʟєᴅ!** ᴛʀʏ ᴀɢᴀιη.")
        return

    size_mb = os.path.getsize(dl_path) / (1024 * 1024)
    log.info(f"📁 File size: {size_mb:.2f} MB")

    # Purana file delete
    old_file = _dm_current.get(chat_id)
    if old_file and os.path.exists(old_file) and old_file != dl_path:
        try:
            os.remove(old_file)
        except Exception:
            pass

    _dm_current[chat_id] = dl_path

    await status_msg.edit("🎵 **ρʀᴏᴄєssιηɢ & ρʟᴀʏιηɢ...**")
    await asyncio.sleep(0.5)

    if chat_id in vc._active_ub:
        log.info(f"🔄 Replacing audio → chat {chat_id}")
        success = await vc.replace_audio(chat_id, dl_path)
    else:
        log.info(f"▶️ Starting DM loop → chat {chat_id}")
        success = await vc.play_loop(chat_id, dl_path)

    if success:
        await status_msg.edit(
            f"✅ **ρʟᴀʏιηɢ ιη ᴠᴄ!** *(ʟᴏᴏρ ϻᴏᴅє)*\n"
            f"📁 `{os.path.basename(dl_path)}` ({size_mb:.1f} MB)\n"
            f"sєηᴅ ᴀηᴏᴛнєʀ ᴀᴜᴅιᴏ ᴛᴏ ʀєρʟᴀᴄє.",
            reply_markup=_dm_stop_kb(chat_id),
        )
    else:
        await status_msg.edit("❌ **ғᴀιʟєᴅ ᴛᴏ ρʟᴀʏ.** ᴄнєᴄᴋ ιғ ᴠᴄ ιs ᴀᴄᴛιᴠє.")


# ══════════════════════════════════════════════════════════════
#  DM MODE — VOICE NOTE HANDLER
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.private & pyro_filters.voice)
async def dm_voice_handler(client, message: Message):
    uid = message.from_user.id
    if not await is_authorized(uid):
        return
    mode = await get_mode()
    if mode != "dm":
        await message.reply("⚠️ ᴅᴍ ϻᴏᴅє ᴏff нᴀι. `/config` → ˹ 𝐌ᴏᴅє ˼ sє ᴅᴍ ᴄʜᴜηᴏ.")
        return
    log.info(f"📩 Voice note from {uid}")
    await _handle_dm_play(client, message, uid)


# ══════════════════════════════════════════════════════════════
#  DM MODE — AUDIO FILE HANDLER  ← NAYA
#  MP3, M4A, WAV, OGG — koi bhi audio file, koi bhi length
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.private & pyro_filters.audio)
async def dm_audio_handler(client, message: Message):
    uid = message.from_user.id
    if not await is_authorized(uid):
        return
    mode = await get_mode()
    if mode != "dm":
        await message.reply("⚠️ ᴅᴍ ϻᴏᴅє ᴏff нᴀι. `/config` → ˹ 𝐌ᴏᴅє ˼ sє ᴅᴍ ᴄʜᴜηᴏ.")
        return
    log.info(f"📩 Audio file from {uid}")
    await _handle_dm_play(client, message, uid)


# ══════════════════════════════════════════════════════════════
#  /play COMMAND  ← NAYA
#  1. Audio file ke saath /play
#  2. Kisi audio/voice pe reply karke /play
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.command("play") & pyro_filters.private)
async def play_command_handler(client, message: Message):
    uid = message.from_user.id
    if not await is_authorized(uid):
        return

    mode = await get_mode()
    if mode != "dm":
        await message.reply(
            "⚠️ ᴅᴍ ϻᴏᴅє ᴏff нᴀι.\n"
            "`/config` → ˹ 𝐌ᴏᴅє ˼ sє ᴅᴍ ᴄʜᴜηᴏ."
        )
        return

    # Target message nikalo
    target_msg = None

    if message.audio or message.voice or message.video_note:
        target_msg = message
    elif message.reply_to_message:
        rep = message.reply_to_message
        if rep.audio or rep.voice or rep.video_note or rep.document:
            target_msg = rep

    if not target_msg:
        await message.reply(
            "📎 **ᴋιsι ᴀᴜᴅιᴏ ρє ʀєρʟʏ ᴋᴀʀᴋє `/play` ʙʜєᴊᴏ**\n"
            "ʏᴀ ᴀᴜᴅιᴏ ᴋє sᴀᴀᴛн ᴄᴀρsʜη ϻєιη `/play` ʟιᴋʜᴏ.\n\n"
            "**sᴜρρᴏʀᴛєᴅ:** 🎵 MP3, M4A, OGG, WAV · 🎙️ ᴠᴏιᴄє ηᴏᴛє"
        )
        return

    log.info(f"▶️ /play from {uid}")
    await _handle_dm_play(client, target_msg, uid)


# ══════════════════════════════════════════════════════════════
#  DM STOP CALLBACK
# ══════════════════════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex(r"^dm_stop_(-?\d+)$"))
async def cb_dm_stop(client, cq):
    uid = cq.from_user.id
    if not await is_authorized(uid):
        return await cq.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)

    chat_id = int(cq.data.split("_")[2])

    for user_id, track in list(_auto_tracking.items()):
        if track.get("chat_id") == chat_id:
            await _stop_recording(user_id)
            _cleanup_old_recording(user_id)
            _auto_tracking.pop(user_id, None)

    old_file = _dm_current.pop(chat_id, None)
    if old_file and os.path.exists(old_file):
        try:
            os.remove(old_file)
        except Exception:
            pass

    await vc.stop(chat_id)
    await cq.answer("⏹️ ᴠᴄ sᴛᴏρρєᴅ!", show_alert=False)
    try:
        await cq.message.edit_text("⏹️ **ᴠᴄ sᴛᴏρρєᴅ & ʟєғᴛ.**")
    except Exception:
        pass
    log.info(f"⏹️ DM Stop by {uid} → chat {chat_id}")


# ══════════════════════════════════════════════════════════════
#  /fstop
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.command("fstop") & pyro_filters.private)
async def fstop_handler(client, message: Message):
    uid = message.from_user.id
    if not await is_authorized(uid):
        return
    target = await get_primary_target()
    if not target:
        await message.reply("⚠️ ᴛᴀʀɢєᴛ sєᴛ ηᴀнιιη нᴀι.")
        return
    chat_id = target["chat_id"]
    for user_id, track in list(_auto_tracking.items()):
        if track.get("chat_id") == chat_id:
            await _stop_recording(user_id)
            _cleanup_old_recording(user_id)
            _auto_tracking.pop(user_id, None)
    old_file = _dm_current.pop(chat_id, None)
    if old_file and os.path.exists(old_file):
        try:
            os.remove(old_file)
        except Exception:
            pass
    await vc.stop(chat_id)
    await message.reply("⏹️ **ᴠᴄ ғᴏʀᴄє sᴛᴏρρєᴅ & ʟєғᴛ.**")
    log.info(f"⏹️ /fstop by {uid} → chat {chat_id}")


# ══════════════════════════════════════════════════════════════
#  /stop — GROUP
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.command("stop") & pyro_filters.group)
async def stop_handler(client, message: Message):
    uid = message.from_user.id
    if not await is_authorized(uid):
        return
    chat_id = message.chat.id
    for user_id, track in list(_auto_tracking.items()):
        if track.get("chat_id") == chat_id:
            await _stop_recording(user_id)
            _cleanup_old_recording(user_id)
            _auto_tracking.pop(user_id, None)
    _dm_current.pop(chat_id, None)
    await vc.stop(chat_id)
    await message.reply("⏹️ **sᴛᴏρρєᴅ & ʟєғᴛ ᴠᴄ.**")
    log.info(f"⏹️ /stop by {uid} → chat {chat_id}")


# ══════════════════════════════════════════════════════════════
#  /vcoff
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.command("vcoff"))
async def vcoff_handler(client, message: Message):
    uid = message.from_user.id
    if not await is_authorized(uid):
        return
    if message.chat.type in ("group", "supergroup"):
        chat_id = message.chat.id
    else:
        target = await get_primary_target()
        if not target:
            await message.reply("⚠️ ᴛᴀʀɢєᴛ sєᴛ ηᴀнιιη нᴀι.")
            return
        chat_id = target["chat_id"]
    await vc.stop(chat_id, leave_vc=True)
    await message.reply(
        "📴 **ᴠᴄ sє ʟєғᴛ ᴋʀ ᴅιʏᴀ.**\n"
        "ᴀɢʟι ᴀᴜᴅιᴏ ʏᴀ `/resume` sє ᴡᴀρᴀs ᴊᴏιη нᴏɢᴀ."
    )
    log.info(f"📴 /vcoff by {uid} → left chat {chat_id}")


# ══════════════════════════════════════════════════════════════
#  /pause  /resume
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.command("pause") & pyro_filters.group)
async def pause_handler(client, message: Message):
    uid = message.from_user.id
    if not await is_authorized(uid):
        return
    if await vc.pause(message.chat.id):
        await message.reply("⏸️ **ρᴀᴜsєᴅ.** ᴜsє `/resume` ᴛᴏ ᴄᴏηᴛιηᴜє.")
    else:
        await message.reply("⚠️ ᴋᴜᴄн нι ρʟᴀʏ ηᴀнιιη нᴏ ʀᴀнᴀ нᴀι ιs ᴄнᴀᴛ ϻєιη.")


@app.on_message(pyro_filters.command("resume") & pyro_filters.group)
async def resume_handler(client, message: Message):
    uid = message.from_user.id
    if not await is_authorized(uid):
        return
    chat_id = message.chat.id

    if await vc.resume(chat_id):
        await message.reply("▶️ **ʀєsᴜϻєᴅ!**")
        return

    # Fallback: no tracked paused stream (e.g. after a bot restart) —
    # restart playback from the last known DM file for this chat.
    file = _dm_current.get(chat_id)
    if not file or not os.path.exists(file):
        await message.reply("⚠️ ᴋᴜᴄн ρᴀᴜsєᴅ ηᴀнιιη ϻιʟᴀ. sєηᴅ ᴀη ᴀᴜᴅιᴏ ғιʟє ғιʀsᴛ.")
        return
    success = await vc.play_loop(chat_id, file)
    if success:
        await message.reply("▶️ **ʀєsᴜϻєᴅ** *(ʟᴀsᴛ ᴀᴜᴅιᴏ sє ʀєsᴛᴀʀᴛ)*!")
    else:
        await message.reply("❌ **ғᴀιʟєᴅ ᴛᴏ ʀєsᴜϻє.**")


# ══════════════════════════════════════════════════════════════
#  /vcstatus
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.command("vcstatus"))
async def vcstatus_handler(client, message: Message):
    if not is_owner(message.from_user.id):
        return
    mode   = await get_mode()
    status = vc.status()
    target = await get_primary_target()
    text = (
        f"⚔️ **ᴠᴄғιɢнᴛєʀ sᴛᴀᴛᴜs**\n\n"
        f"🎮 ϻᴏᴅє: `{mode.upper()}`\n"
        f"📡 ρʏᴛɢᴄᴀʟʟs ιηsᴛᴀηᴄєs: `{status['pytgcalls_instances']}`\n"
        f"▶️ ᴀᴄᴛιᴠє sᴛʀєᴀϻs: `{status['active_streams']}`\n"
        f"🔁 ʟᴏᴏρ ᴄнᴀᴛs: `{status['loop_active_chats']}`\n"
        f"🎯 ᴛᴀʀɢєᴛ: `{target['chat_id'] if target else 'ηᴏᴛ sєᴛ'}`\n"
        f"🎙️ ᴀᴜᴛᴏ ᴛʀᴀᴄᴋιηɢ: `{len(_auto_tracking)} ᴜsєʀ(s)`"
    )
    await message.reply(text)
    
