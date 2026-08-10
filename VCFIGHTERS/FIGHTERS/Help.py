from pyrogram import filters as pyro_filters
from pyrogram.errors import MessageNotModified
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from VCFIGHTERS.core.bot import app
from VCFIGHTERS.FIGHTERS.sudo import is_authorized

async def _safe_edit(target, *args, **kwargs):
    """Edit a message/callback-query's text, silently ignoring Telegram's
    MESSAGE_NOT_MODIFIED error (raised when the new content is identical
    to what's already shown — e.g. a double-tap on the same button)."""
    try:
        await target.edit_message_text(*args, **kwargs)
    except MessageNotModified:
        pass


# ──────────────────────────────────────────────────────────────
# HELP CONTENT
# ──────────────────────────────────────────────────────────────

_SECTIONS = {
    "vc": (
        "🎙️ **ᴠᴄ ᴄᴏϻϻᴀηᴅs**\n\n"
        "`/stop` — ᴠᴄ ʙᴀηᴅ ᴋᴀʀᴏ & ʟєᴀᴠє\n"
        "`/pause` — ᴀᴜᴅιᴏ ρᴀᴜsє ᴋᴀʀᴏ\n"
        "`/resume` — ᴀᴜᴅιᴏ ᴡᴀᴘᴀs ᴄʜᴀʟᴀᴏ\n"
        "`/vcstatus` — ᴄᴜʀʀєηᴛ ᴠᴄ sᴛᴀᴛᴜs ᴅєᴋʜᴏ"
    ),
    "config": (
        "⚙️ **ᴄᴏηғιɢ ᴄᴏϻϻᴀηᴅs**\n\n"
        "`/config` — ϻᴀιη ᴄᴏηғιɢ ρᴀηєʟ ᴋʜᴏʟᴏ\n\n"
        "**ρᴀηєʟ ϻєηᴜ:**\n"
        "˹ 𝐋ᴏɢɢєʀ ˼ — ʟᴏɢ ɢʀᴏᴜρ sєᴛ ᴋᴀʀᴏ\n"
        "˹ 𝐅𝐅ϻρєɢ ˼ — ᴀᴜᴅιᴏ ᴡєᴀρᴏη ᴄᴏηᴛʀᴏʟs\n"
        "˹ 𝐌ᴏᴅє ˼ — ᴀᴜᴛᴏ ʏᴀ ᴅᴍ ϻᴏᴅє\n"
        "˹ 𝐔sєʀ𝐁ᴏᴛs ˼ — ᴜsєʀʙᴏᴛ ᴀᴅᴅ/ᴅєʟ\n"
        "˹ 𝐓ᴀʀɢєᴛ ˼ — ᴛᴀʀɢєᴛ ɢʀᴏᴜρ sєᴛ ᴋᴀʀᴏ\n"
        "˹ ρʏᴛɢ𝐂ᴀʟʟs ˼ — sᴛʀєᴀᴍ ϙᴜᴀʟιᴛʏ\n"
        "˹ ριηɢs ˼ — sʏsᴛєϻ ριηɢs ᴄʜєᴄᴋ"
    ),
    "modes": (
        "🎮 **ϻᴏᴅєs**\n\n"
        "🟢 **ᴀᴜᴛᴏ ϻᴏᴅє**\n"
        "ᴏᴡηєʀ/sᴜᴅᴏ ᴊᴀʙ ᴠᴄ ϻєιη ϻιᴄ ᴏη ᴋᴀʀє →\n"
        "ᴜsєʀʙᴏᴛ ᴀᴜᴛᴏ ʀєᴄᴏʀᴅ ᴋᴀʀɴᴀ sʜᴜʀᴜ\n"
        "ϻιᴄ ʙᴀηᴅ ᴋᴀʀᴏ → ʀєᴄᴏʀᴅιηɢ ʟᴏᴏρ ϻєιη ᴄʜᴀʟє\n\n"
        "🔵 **ᴅᴍ ϻᴏᴅє**\n"
        "ʙᴏᴛ ᴋᴇ ᴅᴍ ϻєιη ᴠᴏιᴄє ηᴏᴛє ʙʜєᴊᴏ →\n"
        "ᴜsєʀʙᴏᴛ ᴛᴀʀɢєᴛ ᴠᴄ ϻєιη ʟᴏᴏρ ᴄʜᴀʟᴀʏє\n"
        "ηʏᴀ ᴠᴏιᴄє ηᴏᴛє ʙʜєᴊᴏ → ρᴜʀᴀηᴀ ʀᴜᴋє, ηʏᴀ ᴄʜᴀʟє"
    ),
    "ffmpeg": (
        "🛠️ **𝐅𝐅ϻρєɢ ᴡєᴀρᴏηs**\n\n"
        "🔊 **ᴠᴏʟᴜϻє** — 100% sє MAX 💥 ᴛᴀᴋ\n"
        "🎛️ **ᴄᴏϻρʀєssᴏʀ** — ᴅʜєᴇᴍι ᴀᴀᴡᴀᴢ ʙᴏᴏsᴛ\n"
        "🔒 **ʟιϻιᴛєʀ** — ғᴀᴛι ᴀᴀᴡᴀᴢ ᴄᴏηᴛʀᴏʟ\n"
        "🎸 **ʙᴀss** — ηᴏʀϻᴀʟ → нєᴀᴠʏ → 🌍 єᴀʀᴛнϙᴜᴀᴋє\n"
        "👹 **ριᴛᴄн** — ηᴏʀϻᴀʟ → ᴅєϻᴏη → 🐹 ᴄʜιρϻᴜηᴋ\n"
        "🦇 **єᴄʜᴏ** — ɢʜᴏsᴛ ρʀᴏᴛᴏᴄᴏʟ ʀєᴠєʀʙ\n\n"
        "💀 **ɢᴀᴀηᴅ ғᴀᴀᴅ ϻᴏᴅє** = sᴀʙ ᴍᴀx ᴇᴋ sᴀᴀᴛʜ"
    ),
    "sudo": (
        "👑 **sᴜᴅᴏ sʏsᴛєϻ**\n\n"
        "`/addsudo` — ʀєρʟʏ ᴋᴀʀᴏ ʏᴀ ιᴅ ᴅᴏ → sᴜᴅᴏ ᴀᴅᴅ\n"
        "`/delsudo` — sᴜᴅᴏ ʀєϻᴏᴠє ᴋᴀʀᴏ\n"
        "`/sudolist` — sᴀʙ sᴜᴅᴏ ᴜsєʀs ᴅєᴋʜᴏ\n\n"
        "⚠️ sιʀғ **ᴏᴡηєʀ** нι sᴜᴅᴏ ᴀᴅᴅ/ᴅєʟ ᴋᴀʀ sᴋᴛᴀ нᴀι"
    ),
}

# ──────────────────────────────────────────────────────────────
# KEYBOARDS
# ──────────────────────────────────────────────────────────────

def _main_help_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("˹ 🎙️ ᴠᴄ ᴄᴍᴅs ˼",    callback_data="hlp_vc"),
            InlineKeyboardButton("˹ ⚙️ ᴄᴏηғιɢ ˼",      callback_data="hlp_config"),
        ],
        [
            InlineKeyboardButton("˹ 🎮 ϻᴏᴅєs ˼",       callback_data="hlp_modes"),
            InlineKeyboardButton("˹ 🛠️ 𝐅𝐅ϻρєɢ ˼",      callback_data="hlp_ffmpeg"),
        ],
        [
            InlineKeyboardButton("˹ 👑 sᴜᴅᴏ ˼",        callback_data="hlp_sudo"),
        ],
        [
            InlineKeyboardButton("˹ ❌ ᴄʟᴏsє ˼",       callback_data="hlp_close"),
        ],
    ])


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="hlp_main")]
    ])


# ──────────────────────────────────────────────────────────────
# /help COMMAND
# ──────────────────────────────────────────────────────────────

@app.on_message(pyro_filters.command("help") & pyro_filters.private)
async def cmd_help(client, message: Message):
    if not await is_authorized(message.from_user.id):
        return
    await message.reply(
        "⚔️ **ᴠᴄғιɢнᴛєʀ ʜєʟρ**\n\nᴋᴀᴜηsᴀ sєᴄᴛιᴏη ᴄʜᴀʜιᴇ?",
        reply_markup=_main_help_kb(),
    )


# ──────────────────────────────────────────────────────────────
# CALLBACKS
# ──────────────────────────────────────────────────────────────

@app.on_callback_query(pyro_filters.regex("^hlp_main$"))
async def cb_hlp_main(client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    await _safe_edit(query, 
        "⚔️ **ᴠᴄғιɢнᴛєʀ ʜєʟρ**\n\nᴋᴀᴜηsᴀ sєᴄᴛιᴏη ᴄʜᴀʜιᴇ?",
        reply_markup=_main_help_kb(),
    )
    await query.answer()


@app.on_callback_query(pyro_filters.regex("^hlp_(vc|config|modes|ffmpeg|sudo)$"))
async def cb_hlp_section(client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    key  = query.data.split("_")[1]
    text = _SECTIONS.get(key, "ηᴏᴛ ғᴏᴜηᴅ.")
    await _safe_edit(query, text, reply_markup=_back_kb())
    await query.answer()


@app.on_callback_query(pyro_filters.regex("^hlp_close$"))
async def cb_hlp_close(client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        pass

