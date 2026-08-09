# ╔══════════════════════════════════════════════════════════════╗
# ║         VCFIGHTER — FFmpeg Weapon Controls                   ║
# ║         File: VCFIGHTERS/FIGHTERS/ffmpegsettings.py          ║
# ╚══════════════════════════════════════════════════════════════╝

from pyrogram import Client
from pyrogram import filters as pyro_filters
from pyrogram.errors import MessageNotModified
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import Config
from VCFIGHTERS.logging import LOGGER
from VCFIGHTERS.database.mangodb import (
    get_active_userbots,
    get_ffmpeg_settings,
    get_sudo_users,
    save_ffmpeg_settings,
    reset_ffmpeg_settings,
)

log = LOGGER("FFmpeg")


# ──────────────────────────────────────────────────────────────
# AUTH HELPERS
# ──────────────────────────────────────────────────────────────

def is_owner(user_id: int) -> bool:
    return user_id == int(Config.OWNER_ID)


async def is_sudo(user_id: int) -> bool:
    return user_id in await get_sudo_users()


async def is_authorized(user_id: int) -> bool:
    return is_owner(user_id) or await is_sudo(user_id)


# ──────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────

DEFAULT_FFMPEG = {
    "volume":     1.0,
    "compressor": False,
    "limiter":    False,
    "bass":       0,
    "pitch":      "normal",
    "echo":       False,
}


# ──────────────────────────────────────────────────────────────
# PROFILE DETECTOR
# ──────────────────────────────────────────────────────────────

def get_profile(s: dict) -> str:
    all_max = (
        s.get("volume", 1.0) >= 50.0
        and s.get("compressor", False)
        and s.get("limiter", False)
        and s.get("bass", 0) >= 40
        and s.get("pitch") == "demon"
        and s.get("echo", False)
    )
    all_default = (
        s.get("volume", 1.0) == 1.0
        and not s.get("compressor", False)
        and not s.get("limiter", False)
        and s.get("bass", 0) == 0
        and s.get("pitch") == "normal"
        and not s.get("echo", False)
    )
    if all_max:
        return "💀 ɢᴀᴀɴᴅ ғᴀᴀᴅ ᴍᴏᴅє"
    if all_default:
        return "😴 ᴅєғᴀᴜʟᴛ ᴍᴏᴅє"
    return "⚔️ ᴄᴜsᴛᴏᴍ ᴍᴏᴅє"


# ──────────────────────────────────────────────────────────────
# FILTER CHAIN BUILDER
# ──────────────────────────────────────────────────────────────

def build_filter_chain(s: dict) -> str | None:
    chain = []

    vol = s.get("volume", 1.0)
    if vol != 1.0:
        chain.append(f"volume={vol}")

    if s.get("compressor"):
        chain.append("acompressor=ratio=20:makeup=24")

    if s.get("limiter"):
        chain.append("alimiter=limit=-0.5dB")

    bass = s.get("bass", 0)
    if bass != 0:
        chain.append(f"bass=g={bass}")

    pitch = s.get("pitch", "normal")
    if pitch == "demon":
        chain.append("asetrate=44100*0.7,aresample=44100")
    elif pitch == "chipmunk":
        chain.append("asetrate=44100*1.6,aresample=44100")

    if s.get("echo"):
        chain.append("aecho=0.8:0.9:1000:0.3")

    return ",".join(chain) if chain else None


# ──────────────────────────────────────────────────────────────
# SAFE EDIT HELPER
# ──────────────────────────────────────────────────────────────

async def safe_edit(query: CallbackQuery, text: str, keyboard: InlineKeyboardMarkup):
    """Edit the panel message, ignoring Telegram's MESSAGE_NOT_MODIFIED error
    (raised when the new content is identical to what's already shown)."""
    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except MessageNotModified:
        pass


# ──────────────────────────────────────────────────────────────
# PANEL BUILDER
# ──────────────────────────────────────────────────────────────

def build_panel(s: dict) -> tuple[str, InlineKeyboardMarkup]:

    profile = get_profile(s)

    vol   = s.get("volume", 1.0)
    comp  = s.get("compressor", False)
    lim   = s.get("limiter", False)
    bass  = s.get("bass", 0)
    pitch = s.get("pitch", "normal")
    echo  = s.get("echo", False)

    vol_pct  = {1.0: "100%", 5.0: "500%", 20.0: "2000%", 50.0: "ϻᴀx 💥"}.get(vol, f"{int(vol*100)}%")
    bass_lbl = {0: "ηᴏʀϻᴀʟ", 20: "нєᴀᴠʏ", 40: "🌍 єᴀʀᴛн"}.get(bass, str(bass))
    pitch_lbl = {"normal": "ηᴏʀϻᴀʟ", "demon": "👹 ᴅєϻᴏη", "chipmunk": "🐹 ᴄнιρ"}.get(pitch, pitch)

    text = (
        "🛠️ **𝐅𝐅ϻρєɢ 𝐖єᴀρᴏη ᴄᴏηᴛʀᴏʟs** 🛠️\n"
        f"ᴄᴜʀʀєηᴛ ρʀᴏғιʟє: {profile}\n\n"
        f"🔊 **𝐕ᴏʟᴜϻє:** {vol_pct}\n"
        f"🎛️ **𝐂ᴏϻρʀєssᴏʀ:** {'ᴏη ✅' if comp else 'ᴏғғ ❌'}   |   "
        f"🔒 **ʟιϻιᴛєʀ:** {'ᴏη ✅' if lim else 'ᴏғғ ❌'}\n"
        f"🎸 **𝐁ᴀss:** {bass_lbl}\n"
        f"👹 **ριᴛᴄн:** {pitch_lbl}\n"
        f"🦇 **єᴄнᴏ:** {'ᴏη ✅' if echo else 'ᴏғғ ❌'}"
    )

    # Active marker
    def sel(cond): return "✦ " if cond else ""

    keyboard = InlineKeyboardMarkup([

        # ── Volume ────────────────────────────────────────────
        [
            InlineKeyboardButton(f"{sel(vol==1.0)}˹ 𝐕ᴏʟ: 𝟏𝟎𝟎% ˼",  callback_data="ff_vol_1"),
            InlineKeyboardButton(f"{sel(vol==5.0)}˹ 𝐕ᴏʟ: 𝟓𝟎𝟎% ˼",  callback_data="ff_vol_5"),
            InlineKeyboardButton(f"{sel(vol==20.0)}˹ 𝐕ᴏʟ: 𝟐𝟎𝟎𝟎% ˼", callback_data="ff_vol_20"),
            InlineKeyboardButton(f"{sel(vol==50.0)}˹ 𝐕ᴏʟ: ϻᴀx 💥 ˼",  callback_data="ff_vol_50"),
        ],

        # ── Compressor + Limiter ──────────────────────────────
        [
            InlineKeyboardButton(
                f"˹ 𝐂ᴏϻρ: {'ᴏғғ ❌' if comp else 'ᴏη ✅'} ˼",
                callback_data="ff_comp",
            ),
            InlineKeyboardButton(
                f"˹ ʟιϻιᴛ: {'ᴏғғ ❌' if lim else 'ᴏη ✅'} ˼",
                callback_data="ff_lim",
            ),
        ],

        # ── Bass ──────────────────────────────────────────────
        [
            InlineKeyboardButton(f"{sel(bass==0)}˹ 𝐁ᴀss: ηᴏʀϻᴀʟ ˼",     callback_data="ff_bass_0"),
            InlineKeyboardButton(f"{sel(bass==20)}˹ 𝐁ᴀss: нєᴀᴠʏ ˼",      callback_data="ff_bass_20"),
            InlineKeyboardButton(f"{sel(bass==40)}˹ 𝐁ᴀss: 🌍 єᴀʀᴛн ˼",   callback_data="ff_bass_40"),
        ],

        # ── Pitch ─────────────────────────────────────────────
        [
            InlineKeyboardButton(f"{sel(pitch=='normal')}˹ ριᴛᴄн: ηᴏʀϻᴀʟ ˼",   callback_data="ff_pitch_normal"),
            InlineKeyboardButton(f"{sel(pitch=='demon')}˹ ριᴛᴄн: 👹 ᴅєϻᴏη ˼",   callback_data="ff_pitch_demon"),
            InlineKeyboardButton(f"{sel(pitch=='chipmunk')}˹ ριᴛᴄн: 🐹 ᴄнιρ ˼", callback_data="ff_pitch_chipmunk"),
        ],

        # ── Echo + Reset ──────────────────────────────────────
        [
            InlineKeyboardButton(
                f"˹ єᴄнᴏ: {'ᴏғғ ❌' if echo else 'ᴏη 🦇'} ˼",
                callback_data="ff_echo",
            ),
            InlineKeyboardButton("˹ 🔄 ʀєsєᴛ ˼", callback_data="ff_reset"),
        ],

        # ── Save ──────────────────────────────────────────────
        [InlineKeyboardButton("˹ 💾 sᴀᴠє & 𝚫ρρʟʏ ˼", callback_data="ff_save")],

        # ── Back ──────────────────────────────────────────────
        [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="config_main")],
    ])

    return text, keyboard


# ──────────────────────────────────────────────────────────────
# OPEN PANEL (called from Settings.py)
# ──────────────────────────────────────────────────────────────

async def open_ffmpeg_panel(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    s = await get_ffmpeg_settings()
    text, keyboard = build_panel(s)
    await safe_edit(query, text, keyboard)


# ──────────────────────────────────────────────────────────────
# CALLBACK HANDLER
# ──────────────────────────────────────────────────────────────

from VCFIGHTERS.core.bot import app  # noqa: E402


@app.on_callback_query(pyro_filters.regex(r"^ff_"))
async def ffmpeg_callback_handler(client: Client, query: CallbackQuery):

    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return

    data = query.data
    s    = await get_ffmpeg_settings()

    # ── Volume ────────────────────────────────────────────────
    if   data == "ff_vol_1":   s["volume"] = 1.0
    elif data == "ff_vol_5":   s["volume"] = 5.0
    elif data == "ff_vol_20":  s["volume"] = 20.0
    elif data == "ff_vol_50":  s["volume"] = 50.0

    # ── Compressor toggle ─────────────────────────────────────
    elif data == "ff_comp":
        s["compressor"] = not s.get("compressor", False)

    # ── Limiter toggle ────────────────────────────────────────
    elif data == "ff_lim":
        s["limiter"] = not s.get("limiter", False)

    # ── Bass ──────────────────────────────────────────────────
    elif data == "ff_bass_0":   s["bass"] = 0
    elif data == "ff_bass_20":  s["bass"] = 20
    elif data == "ff_bass_40":  s["bass"] = 40

    # ── Pitch ─────────────────────────────────────────────────
    elif data == "ff_pitch_normal":   s["pitch"] = "normal"
    elif data == "ff_pitch_demon":    s["pitch"] = "demon"
    elif data == "ff_pitch_chipmunk": s["pitch"] = "chipmunk"

    # ── Echo toggle ───────────────────────────────────────────
    elif data == "ff_echo":
        s["echo"] = not s.get("echo", False)

    # ── Reset Defaults ────────────────────────────────────────
    elif data == "ff_reset":
        s = DEFAULT_FFMPEG.copy()
        await save_ffmpeg_settings(s)
        await query.answer("🔄 ʀєsєᴛ ᴅᴏηє ✅", show_alert=False)
        text, keyboard = build_panel(s)
        await safe_edit(query, text, keyboard)
        return

    # ── Save & Apply ──────────────────────────────────────────
    elif data == "ff_save":
        await save_ffmpeg_settings(s)
        filter_chain = build_filter_chain(s)
        log.info(f"🔧 Filter chain saved: {filter_chain or 'passthrough'}")

        applied = 0
        try:
            from VCFIGHTERS.core.call import vc
            applied = await vc.apply_filters_to_all()
        except Exception as e:
            log.warning(f"⚠️ apply_filters_to_all error: {e}")

        userbots = await get_active_userbots()
        total    = len(userbots)
        msg = (
            f"✅ sᴀᴠєᴅ & ᴀρρʟιєᴅ ᴛᴏ {applied}/{total} ᴜsєʀʙᴏᴛs"
            if total else
            "💾 sєᴛᴛιηɢs sᴀᴠєᴅ (ηᴏ ᴀᴄᴛιᴠє sᴛʀєᴀϻs)"
        )
        await query.answer(msg, show_alert=True)
        text, keyboard = build_panel(s)
        await safe_edit(query, text, keyboard)
        return

    # ── Rebuild panel after any toggle ───────────────────────
    await save_ffmpeg_settings(s)
    await query.answer()
    text, keyboard = build_panel(s)
    await safe_edit(query, text, keyboard)
    
