import asyncio
import time

from pyrogram import Client
from pyrogram import filters as pyro_filters
from pyrogram.errors import UserAlreadyParticipant
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
import re

import Config
from VCFIGHTERS.logging import LOGGER
from VCFIGHTERS.database.mangodb import (
    add_target,
    add_userbot,
    delete_all_userbots,
    delete_userbot,
    get_all_targets,
    get_all_userbots,
    get_pytgcalls_settings,
    get_settings,
    get_sudo_users,
    save_pytgcalls_settings,
    save_settings,
)
from VCFIGHTERS.FIGHTERS.ffmpegsettings import open_ffmpeg_panel

log = LOGGER("Settings")

# Telegram usernames: letters/digits/underscore, 5-32 chars, must start with a letter
_USERNAME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$')


def _is_valid_target_link(link: str) -> bool:
    """Private invite links (t.me/+..., joinchat/...), public t.me links
    (t.me/groupname), and bare @usernames are all accepted."""
    if "t.me/+" in link or "joinchat" in link:
        return True
    m = re.search(r't\.me/([a-zA-Z][a-zA-Z0-9_]{4,31})/?$', link)
    if m:
        return True
    bare = link.lstrip("@")
    return bool(_USERNAME_RE.match(bare))


def _is_chat_id_input(text: str) -> bool:
    """Numeric chat id, e.g. -1001234567890 (supergroup/channel) or a
    plain group id. Telegram group/channel ids are always negative.
    Used when a userbot is already a member but no working invite
    link is available."""
    return bool(re.match(r'^-\d+$', text))


# ──────────────────────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────────────────────

def is_owner(user_id: int) -> bool:
    return user_id == int(Config.OWNER_ID)

async def is_sudo(user_id: int) -> bool:
    return user_id in await get_sudo_users()

async def is_authorized(user_id: int) -> bool:
    return is_owner(user_id) or await is_sudo(user_id)


# ──────────────────────────────────────────────────────────────
# CONVERSATION STATE
# ──────────────────────────────────────────────────────────────

_state: dict[int, dict] = {}

def set_state(uid: int, step: str, **data):
    _state[uid] = {"step": step, **data}

def get_state(uid: int) -> dict:
    return _state.get(uid, {})

def clear_state(uid: int):
    _state.pop(uid, None)


from VCFIGHTERS.core.bot import app  # noqa: E402


# ══════════════════════════════════════════════════════════════
#  MAIN CONFIG PANEL
# ══════════════════════════════════════════════════════════════

def _main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("˹ 𝐋ᴏɢɢєʀ ˼",     callback_data="cfg_logger"),
            InlineKeyboardButton("˹ 𝐅𝐅ϻρєɢ ˼",     callback_data="cfg_ffmpeg"),
        ],
        [
            InlineKeyboardButton("˹ 𝐌ᴏᴅє ˼",       callback_data="cfg_mode"),
            InlineKeyboardButton("˹ 𝐔sєʀ𝐁ᴏᴛs ˼",   callback_data="cfg_ub_page_0"),
        ],
        [
            InlineKeyboardButton("˹ 𝐓ᴀʀɢєᴛ ˼",     callback_data="cfg_target"),
            InlineKeyboardButton("˹ ρʏᴛɢ𝐂ᴀʟʟs ˼",  callback_data="cfg_pytgcalls"),
        ],
        [
            InlineKeyboardButton("˹ ριηɢs ˼",       callback_data="cfg_pings"),
        ],
    ])


@app.on_message(pyro_filters.command("config") & pyro_filters.private)
async def cmd_config(client: Client, message: Message):
    if not await is_authorized(message.from_user.id):
        return
    await message.reply(
        "⚙️ **ᴠᴄғιɢнᴛєʀ ᴄᴏηғιɢ ρᴀηєʟ**",
        reply_markup=_main_menu_kb(),
    )


@app.on_callback_query(pyro_filters.regex("^config_main$"))
async def cb_config_main(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    clear_state(query.from_user.id)
    await query.edit_message_text(
        "⚙️ **ᴠᴄғιɢнᴛєʀ ᴄᴏηғιɢ ρᴀηєʟ**",
        reply_markup=_main_menu_kb(),
    )


# ══════════════════════════════════════════════════════════════
#  BUTTON 1 — FFmpeg (delegates to ffmpegsettings.py)
# ══════════════════════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^cfg_ffmpeg$"))
async def cb_ffmpeg(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    await open_ffmpeg_panel(client, query)


# ══════════════════════════════════════════════════════════════
#  BUTTON 2 — Set Logger
# ══════════════════════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^cfg_logger$"))
async def cb_logger(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    set_state(query.from_user.id, "await_logger_chat")
    await query.edit_message_text(
        "📋 **ʟᴏɢɢєʀ ᴄнᴀᴛ sєᴛ ᴋᴀʀᴏ**\n\n"
        "ʟᴏɢɢєʀ ɢʀᴏᴜρ ᴋᴀ **ᴄнᴀᴛ ιᴅ** ʙнєᴊᴏ.\n"
        "_(ᴜs ɢʀᴏᴜρ sє ᴋᴏι ʙнι ϻєssᴀɢє ғᴏʀᴡᴀʀᴅ ᴋᴀʀᴏ ʏᴀ ᴅιʀєᴄᴛ ιᴅ ρᴀsᴛє ᴋᴀʀᴏ)_",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="config_main")]
        ]),
    )


# ══════════════════════════════════════════════════════════════
#  BUTTON 3 — Set Mode
# ══════════════════════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^cfg_mode$"))
async def cb_mode(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    s   = await get_settings()
    cur = s.get("mode", "dm")
    await query.edit_message_text(
        f"🎮 **ϻᴏᴅє sєʟєᴄᴛ ᴋᴀʀᴏ**\n\nᴄᴜʀʀєηᴛ: `{cur.upper()}`",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{'✦ ' if cur=='auto' else ''}˹ 𝚫ᴜᴛᴏ 𝐌ᴏᴅє ˼",
                    callback_data="cfg_mode_auto",
                ),
                InlineKeyboardButton(
                    f"{'✦ ' if cur=='dm' else ''}˹ 𝐃𝐌 𝐌ᴏᴅє ˼",
                    callback_data="cfg_mode_dm",
                ),
            ],
            [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="config_main")],
        ]),
    )


@app.on_callback_query(pyro_filters.regex("^cfg_mode_dm$"))
async def cb_mode_dm(client: Client, query: CallbackQuery):
    """DM mode — seedha save karo."""
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    await save_settings({"mode": "dm"})
    await query.answer("✅ ᴅᴍ ϻᴏᴅє ᴀᴄᴛιᴠє", show_alert=False)
    await query.edit_message_text(
        "🎮 **ϻᴏᴅє sєʟєᴄᴛ ᴋᴀʀᴏ**\n\nᴄᴜʀʀєηᴛ: `DM`",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("˹ 𝚫ᴜᴛᴏ 𝐌ᴏᴅє ˼", callback_data="cfg_mode_auto"),
                InlineKeyboardButton("✦ ˹ 𝐃𝐌 𝐌ᴏᴅє ˼", callback_data="cfg_mode_dm"),
            ],
            [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="config_main")],
        ]),
    )


@app.on_callback_query(pyro_filters.regex("^cfg_mode_auto$"))
async def cb_mode_auto(client: Client, query: CallbackQuery):
    """Auto mode — 3 button panel: On, Ready, Back"""
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    s   = await get_settings()
    cur = s.get("mode", "dm")
    await query.edit_message_text(
        "🎮 **𝚫ᴜᴛᴏ 𝐌ᴏᴅє**\n\n"
        "🟢 **ᴏη** — ᴀᴜᴛᴏ ϻᴏᴅє sᴀᴠє ᴋᴀʀᴏ\n"
        "  _(ϻιᴄ ᴏη/ᴏff ᴅєᴛєᴄᴛ нᴏɢᴀ ᴀᴜᴛᴏ)_\n\n"
        "📡 **ʀєᴀᴅʏ** — ᴜsєʀʙᴏᴛ ᴛᴀʀɢєᴛ ᴠᴄ ϻєιη ᴊᴏιη ᴋʀᴀᴏ\n"
        "  _(ρнʟє ᴊᴏιη нᴏɢᴀ, ɢιʀ ϻιᴄ sᴜηєɢᴀ)_\n\n"
        f"ᴄᴜʀʀєηᴛ ϻᴏᴅє: `{cur.upper()}`",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🟢 ᴏη",    callback_data="cfg_auto_on"),
                InlineKeyboardButton("📡 ʀєᴀᴅʏ", callback_data="cfg_auto_ready"),
            ],
            [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="cfg_mode")],
        ]),
    )


@app.on_callback_query(pyro_filters.regex("^cfg_auto_on$"))
async def cb_auto_on(client: Client, query: CallbackQuery):
    """Auto mode ON — save karo."""
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    await save_settings({"mode": "auto"})
    await query.answer("✅ 𝚫ᴜᴛᴏ ϻᴏᴅє ᴏη!", show_alert=False)
    await query.edit_message_text(
        "✅ **𝚫ᴜᴛᴏ ϻᴏᴅє ᴀᴄᴛιᴠє!**\n\n"
        "🎙️ ᴀʙ ᴊᴀʙ ᴛᴜ ᴠᴄ ϻєιη ϻιᴄ ᴏη ᴋᴀʀєɢᴀ →\n"
        "ᴜsєʀʙᴏᴛ ᴀᴜᴛᴏ ʀєᴄᴏʀᴅ ᴋʀєɢᴀ ᴀᴜʀ ʟᴏᴏρ ᴄʜᴀʟᴀʏєɢᴀ.\n\n"
        "💡 ρнʟє **ʀєᴀᴅʏ** ᴅʙᴀᴏ ᴛᴀᴋι ᴜsєʀʙᴏᴛ ᴠᴄ ϻєιη ʙєᴛнє.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📡 ʀєᴀᴅʏ", callback_data="cfg_auto_ready")],
            [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="cfg_mode")],
        ]),
    )


@app.on_callback_query(pyro_filters.regex("^cfg_auto_ready$"))
async def cb_auto_ready(client: Client, query: CallbackQuery):
    """Ready — userbot target VC mein silently join karta hai."""
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    await query.answer("⏳ ᴊᴏιη ᴋʀ ʀᴀнᴀ нᴜη...", show_alert=False)
    from VCFIGHTERS.FIGHTERS.Voice import vc_join_ready
    success, msg = await vc_join_ready()
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🟢 ᴏη",    callback_data="cfg_auto_on"),
                InlineKeyboardButton("📡 ʀєᴀᴅʏ", callback_data="cfg_auto_ready"),
            ],
            [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="cfg_mode")],
        ]),
    )


# ══════════════════════════════════════════════════════════════
#  BUTTON 4 — USERBOTs Manager
# ══════════════════════════════════════════════════════════════

def _ub_panel(userbots: list, page: int) -> tuple[str, InlineKeyboardMarkup]:
    total = len(userbots)

    if total == 0:
        text = (
            "👥 **ᴜsєʀʙᴏᴛs ϻᴀηᴀɢєʀ**\n\n"
            "ᴋᴏι ᴜsєʀʙᴏᴛ ηᴀнι ᴀᴅᴅ нᴜᴀ ᴀʙнι."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("˹ sᴛʀιηɢ sєssιᴏη ˼", callback_data="cfg_ub_add_menu")],
            [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼",         callback_data="config_main")],
        ])
        return text, kb

    page   = max(0, min(page, total - 1))
    ub     = userbots[page]
    phone  = ub.get("phone", "ᴜηᴋηᴏᴡη")
    status = "✅ ᴀᴄᴛιᴠє" if ub.get("active") else "❌ ιηᴀᴄᴛιᴠє"

    text = (
        f"👥 **ᴜsєʀʙᴏᴛs ϻᴀηᴀɢєʀ**\n\n"
        f"ᴛᴏᴛᴀʟ: **{total}**\n\n"
        f"📱 `{phone}`  |  {status}"
    )

    nav = []
    if total > 1:
        nav = [
            InlineKeyboardButton("˹ ◀️ ρʀєᴠ ˼", callback_data=f"cfg_ub_page_{(page-1)%total}"),
            InlineKeyboardButton(f"{page+1}/{total}", callback_data="noop"),
            InlineKeyboardButton("˹ ηєxᴛ ▶️ ˼", callback_data=f"cfg_ub_page_{(page+1)%total}"),
        ]

    rows = []
    if nav:
        rows.append(nav)
    rows += [
        [InlineKeyboardButton("˹ sᴛʀιηɢ sєssιᴏη ˼", callback_data="cfg_ub_add_menu")],
        [
            InlineKeyboardButton("˹ ᴅєʟ sєssιᴏη ˼", callback_data=f"cfg_ub_del_{page}"),
            InlineKeyboardButton("˹ ᴅєʟ 𝚫ʟʟ ˼",     callback_data="cfg_ub_delall"),
        ],
        [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="config_main")],
    ]

    return text, InlineKeyboardMarkup(rows)


@app.on_callback_query(pyro_filters.regex(r"^cfg_ub_page_(\d+)$"))
async def cb_ub_page(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    page     = int(query.data.split("_")[-1])
    userbots = await get_all_userbots()
    text, kb = _ub_panel(userbots, page)
    await query.edit_message_text(text, reply_markup=kb)


@app.on_callback_query(pyro_filters.regex("^cfg_ub_add_menu$"))
async def cb_ub_add_menu(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    await query.edit_message_text(
        "➕ **ᴜsєʀʙᴏᴛ ᴀᴅᴅ ᴋᴀʀᴏ**\n\nᴋᴀisє ᴀᴅᴅ ᴋᴀʀηᴀ нᴀι?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("˹ ρнᴏηє ηᴜϻ𝐁єʀ ˼", callback_data="cfg_ub_by_phone")],
            [InlineKeyboardButton("˹ ϻᴀηᴜᴀʟ sєᴛ ˼",    callback_data="cfg_ub_manual")],
            [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼",        callback_data="cfg_ub_page_0")],
        ]),
    )


# ── By Phone Number ────────────────────────────────────────────

@app.on_callback_query(pyro_filters.regex("^cfg_ub_by_phone$"))
async def cb_ub_by_phone(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    set_state(query.from_user.id, "await_phone")
    await query.edit_message_text(
        "📱 **ρнᴏηє ηᴜϻʙєʀ sє ᴀᴅᴅ ᴋᴀʀᴏ**\n\n"
        "ᴄᴏᴜηᴛʀʏ ᴄᴏᴅє ᴋє sᴀᴀᴛн ηᴜϻʙєʀ ʙнєᴊᴏ:\n`+91XXXXXXXXXX`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="cfg_ub_add_menu")]
        ]),
    )


# ── Manual Session ─────────────────────────────────────────────

@app.on_callback_query(pyro_filters.regex("^cfg_ub_manual$"))
async def cb_ub_manual(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    set_state(query.from_user.id, "await_session_string")
    await query.edit_message_text(
        "🖊️ **ϻᴀηᴜᴀʟ sєssιᴏη sєᴛ**\n\n**sᴛʀιηɢ sєssιᴏη** ηιᴄнє ρᴀsᴛє ᴋᴀʀᴏ:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="cfg_ub_add_menu")]
        ]),
    )


@app.on_message(pyro_filters.command("setsession") & pyro_filters.private)
async def cmd_setsession(client: Client, message: Message):
    if not await is_authorized(message.from_user.id):
        return
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply("ᴜsᴀɢє: `/setsession <string_session>`")
        return
    await _save_manual_session(client, message, parts[1].strip(), message.from_user.id)


async def _save_manual_session(client, msg_or_query, session: str, user_id: int):
    try:
        from pyrogram import Client as PyroClient
        tmp = PyroClient(
            "tmp_verify",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            session_string=session,
            no_updates=True,
        )
        await tmp.start()
        me    = await tmp.get_me()
        phone = me.phone_number or "ᴜηᴋηᴏᴡη"
        await tmp.stop()
    except Exception as e:
        err = f"❌ ιηᴠᴀʟιᴅ sєssιᴏη: `{e}`"
        if isinstance(msg_or_query, Message):
            await msg_or_query.reply(err)
        else:
            await msg_or_query.edit_message_text(err)
        return

    await add_userbot({
        "session_string": session,
        "phone":          phone,
        "added_by":       user_id,
        "added_at":       int(time.time()),
        "active":         True,
    })

    try:
        from VCFIGHTERS.core.userbot import userbot_manager
        await userbot_manager.start_userbot(session)
    except Exception as e:
        log.warning(f"DB saved but client failed to start: {e}")

    ok = f"✅ ᴜsєʀʙᴏᴛ `{phone}` ᴀᴅᴅєᴅ & sᴛᴀʀᴛєᴅ!"
    if isinstance(msg_or_query, Message):
        await msg_or_query.reply(ok)
    else:
        await msg_or_query.edit_message_text(
            ok,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="cfg_ub_page_0")]
            ]),
        )


# ── Delete ──────────────────────────────────────────────────────

@app.on_callback_query(pyro_filters.regex(r"^cfg_ub_del_(\d+)$"))
async def cb_ub_del(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    page     = int(query.data.split("_")[-1])
    userbots = await get_all_userbots()
    if not userbots or page >= len(userbots):
        await query.answer("ηᴏ ᴜsєʀʙᴏᴛ ᴀᴛ ᴛнιs ιηᴅєx.", show_alert=True)
        return
    ub = userbots[page]
    await delete_userbot(ub["session_string"])
    try:
        from VCFIGHTERS.core.userbot import userbot_manager
        await userbot_manager.stop_userbot(ub["session_string"])
    except Exception:
        pass
    await query.answer(f"🗑️ {ub.get('phone','?')} ᴅєʟєᴛєᴅ.", show_alert=False)
    userbots = await get_all_userbots()
    text, kb = _ub_panel(userbots, max(0, page - 1))
    await query.edit_message_text(text, reply_markup=kb)


@app.on_callback_query(pyro_filters.regex("^cfg_ub_delall$"))
async def cb_ub_delall(client: Client, query: CallbackQuery):
    if not is_owner(query.from_user.id):
        await query.answer("⛔ ᴏᴡηєʀ ᴏηʟʏ", show_alert=True)
        return
    await delete_all_userbots()
    try:
        from VCFIGHTERS.core.userbot import userbot_manager
        await userbot_manager.stop_all()
    except Exception:
        pass
    await query.answer("🗑️ sᴀʙ ᴜsєʀʙᴏᴛs ᴅєʟєᴛє нᴏ ɢᴀʏє.", show_alert=True)
    text, kb = _ub_panel([], 0)
    await query.edit_message_text(text, reply_markup=kb)


# ══════════════════════════════════════════════════════════════
#  BUTTON 5 — Set Target
# ══════════════════════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^cfg_target$"))
async def cb_target(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    targets = await get_all_targets()
    await _show_targets(query, targets, page=0, ask_new=True)


async def _show_targets(query: CallbackQuery, targets: list, page: int, ask_new: bool = False):
    if not targets or ask_new:
        set_state(query.from_user.id, "await_target_link")
        await query.edit_message_text(
            "🎯 **ᴛᴀʀɢєᴛ sєᴛ ᴋᴀʀᴏ**\n\n"
            "ɢʀᴏᴜρ ʟιηᴋ ʙнєᴊᴏ:\n"
            "`t.me/+xxxx` (ρʀιᴠᴀᴛє) ʏᴀ `t.me/groupname` / `@groupname` (ρᴜʙʟιᴄ)\n\n"
            "ʏᴀ ᴀɢᴀʀ ᴜsєʀʙᴏᴛ ᴀʟʀєᴀᴅʏ ᴜs ɢʀᴏᴜρ ϻєιη нᴀι ᴛᴏ **ᴄʜᴀᴛ ID** ʙнєᴊᴏ: `-1001234567890`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="config_main")]
            ]),
        )
        return

    total  = len(targets)
    page   = max(0, min(page, total - 1))
    t      = targets[page]
    chat   = t.get("chat_id", "N/A")
    link   = t.get("invite_link", "")
    joined = len(t.get("userbots_joined", []))

    text = (
        f"🎯 **ᴛᴀʀɢєᴛ ρᴀηєʟ**\n\n"
        f"ᴄнᴀᴛ ιᴅ: `{chat}`\n"
        f"ʟιηᴋ: {link}\n"
        f"ᴜsєʀʙᴏᴛs ᴊᴏιηєᴅ: **{joined}**"
    )

    nav = []
    if total > 1:
        nav = [
            InlineKeyboardButton("˹ ◀️ ρʀєᴠ ˼", callback_data=f"cfg_tgt_page_{(page-1)%total}"),
            InlineKeyboardButton(f"{page+1}/{total}", callback_data="noop"),
            InlineKeyboardButton("˹ ηєxᴛ ▶️ ˼", callback_data=f"cfg_tgt_page_{(page+1)%total}"),
        ]

    rows = []
    if nav:
        rows.append(nav)
    rows += [
        [InlineKeyboardButton("˹ sєᴛ ʟιηᴋ ˼",    callback_data="cfg_target_new")],
        [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="config_main")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))


@app.on_callback_query(pyro_filters.regex(r"^cfg_tgt_page_(\d+)$"))
async def cb_tgt_page(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    page    = int(query.data.split("_")[-1])
    targets = await get_all_targets()
    await _show_targets(query, targets, page)


@app.on_callback_query(pyro_filters.regex("^cfg_target_new$"))
async def cb_target_new(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    set_state(query.from_user.id, "await_target_link")
    await query.edit_message_text(
        "🎯 **ηʏᴀ ᴛᴀʀɢєᴛ**\n\n"
        "ɢʀᴏᴜρ ʟιηᴋ ʙнєᴊᴏ:\n"
        "`t.me/+xxxx` (ρʀιᴠᴀᴛє) ʏᴀ `t.me/groupname` / `@groupname` (ρᴜʙʟιᴄ)\n\n"
        "ʏᴀ ᴀɢᴀʀ ᴜsєʀʙᴏᴛ ᴀʟʀєᴀᴅʏ ᴜs ɢʀᴏᴜρ ϻєιη нᴀι ᴛᴏ **ᴄʜᴀᴛ ID** ʙнєᴊᴏ: `-1001234567890`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="config_main")]
        ]),
    )


# ══════════════════════════════════════════════════════════════
#  BUTTON 6 — PyTgCalls Settings
# ══════════════════════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^cfg_pytgcalls$"))
async def cb_pytgcalls(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    s = await get_pytgcalls_settings()
    await _show_pytg_panel(query, s)


async def _show_pytg_panel(query: CallbackQuery, s: dict):
    st = s.get("stream_type", "audio")
    ql = s.get("quality",     "medium")
    ns = s.get("noise_suppression", False)

    def sel(cond): return "✦ " if cond else ""

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{sel(st=='audio')}˹ 🔊 𝚫ᴜᴅιᴏ ᴏηʟʏ ˼",  callback_data="cfg_ptg_st_audio"),
            InlineKeyboardButton(f"{sel(st=='video')}˹ 🎥 𝐕ιᴅєᴏ+𝚫ᴜᴅ ˼",   callback_data="cfg_ptg_st_video"),
        ],
        [
            InlineKeyboardButton(f"{sel(ql=='low')}˹ ʟᴏᴡ ˼",    callback_data="cfg_ptg_ql_low"),
            InlineKeyboardButton(f"{sel(ql=='medium')}˹ ϻєᴅ ˼",  callback_data="cfg_ptg_ql_medium"),
            InlineKeyboardButton(f"{sel(ql=='high')}˹ нιɢн ˼",   callback_data="cfg_ptg_ql_high"),
        ],
        [
            InlineKeyboardButton(
                f"˹ ηᴏιsє: {'ᴏη ✅' if ns else 'ᴏғғ ❌'} ˼",
                callback_data="cfg_ptg_ns",
            )
        ],
        [InlineKeyboardButton("˹ 💾 sᴀᴠє ˼",    callback_data="cfg_ptg_save")],
        [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="config_main")],
    ])

    text = (
        "📡 **ρʏᴛɢᴄᴀʟʟs sєᴛᴛιηɢs**\n\n"
        f"sᴛʀєᴀϻ: `{st.upper()}`\n"
        f"ϙᴜᴀʟιᴛʏ: `{ql.upper()}`\n"
        f"ηᴏιsє sᴜρρʀєssιᴏη: `{'ON' if ns else 'OFF'}`"
    )
    await query.edit_message_text(text, reply_markup=kb)



@app.on_callback_query(pyro_filters.regex(r"^cfg_ptg_(st|ql|ns|save)"))
async def cb_pytg_toggle(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    s = await get_pytgcalls_settings()
    d = query.data

    if   d == "cfg_ptg_st_audio":  s["stream_type"] = "audio"
    elif d == "cfg_ptg_st_video":  s["stream_type"] = "video"
    elif d == "cfg_ptg_ql_low":    s["quality"] = "low"
    elif d == "cfg_ptg_ql_medium": s["quality"] = "medium"
    elif d == "cfg_ptg_ql_high":   s["quality"] = "high"
    elif d == "cfg_ptg_ns":        s["noise_suppression"] = not s.get("noise_suppression", False)
    elif d == "cfg_ptg_save":
        await save_pytgcalls_settings(s)
        await query.answer("💾 sᴀᴠєᴅ ✅", show_alert=False)

    await _show_pytg_panel(query, s)


# ══════════════════════════════════════════════════════════════
#  BUTTON 7 — Pings
# ══════════════════════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^cfg_pings$|^cfg_pings_refresh$"))
async def cb_pings(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝚫ᴄᴄєss ᴅєηιєᴅ", show_alert=True)
        return
    await _show_pings(query)


async def _show_pings(query: CallbackQuery):
    from VCFIGHTERS.database.mangodb import db

    t0     = time.monotonic()
    await query.answer()
    bot_ms = int((time.monotonic() - t0) * 1000)

    try:
        t0       = time.monotonic()
        await db.command("ping")
        mongo_ms = int((time.monotonic() - t0) * 1000)
        mongo_str = f"{mongo_ms}ms"
    except Exception:
        mongo_str = "❌ ᴅєᴀᴅ"

    userbots = await get_all_userbots()
    ub_lines = []
    for i, ub in enumerate(userbots, 1):
        try:
            from VCFIGHTERS.core.userbot import userbot_manager
            ub_client = userbot_manager.get_client(ub["session_string"])
            t0 = time.monotonic()
            await ub_client.get_me()
            ms = int((time.monotonic() - t0) * 1000)
            ub_lines.append(f"👤 ᴜsєʀʙᴏᴛ {i}: **{ms}ms** ✅")
        except Exception:
            ub_lines.append(f"👤 ᴜsєʀʙᴏᴛ {i}: ❌ ᴅєᴀᴅ")

    ub_text = "\n".join(ub_lines) if ub_lines else "_(ᴋᴏι ᴜsєʀʙᴏᴛ ηᴀнι)_"

    text = (
        "🏓 **sʏsᴛєϻ ριηɢs**\n\n"
        f"🤖 ʙᴏᴛ sєʀᴠєʀ: **{bot_ms}ms**\n"
        f"🗄️ ϻᴏηɢᴏᴅʙ: **{mongo_str}**\n\n"
        f"{ub_text}"
    )
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("˹ 🔄 ʀєғʀєsн ˼", callback_data="cfg_pings_refresh"),
                InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼",     callback_data="config_main"),
            ]
        ]),
    )


# ══════════════════════════════════════════════════════════════
#  NOOP
# ══════════════════════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^noop$"))
async def cb_noop(client: Client, query: CallbackQuery):
    await query.answer()


# ══════════════════════════════════════════════════════════════
#  CONVERSATION HANDLER — Multi-step flows
# ══════════════════════════════════════════════════════════════

@app.on_message(
    pyro_filters.private
    & ~pyro_filters.command(["start", "config", "setsession", "addsudo", "delsudo", "sudolist"])
)
async def conversation_handler(client: Client, message: Message):
    uid   = message.from_user.id
    state = get_state(uid)
    step  = state.get("step")

    if not step:
        return

    # ── Logger chat ──────────────────────────────────────────
    if step == "await_logger_chat":
        try:
            chat_id = int(message.text.strip())
            await client.send_message(chat_id, "✅ ʟᴏɢɢєʀ ᴄᴏηηєᴄᴛєᴅ!")
            await save_settings({"logger_chat": chat_id})
            clear_state(uid)
            await message.reply(
                f"✅ ʟᴏɢɢєʀ sєᴛ: `{chat_id}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="config_main")]
                ]),
            )
        except Exception as e:
            await message.reply(f"❌ ғᴀιʟєᴅ: `{e}`\nᴅᴏʙᴀʀᴀ ᴛʀʏ ᴋᴀʀᴏ.")

    # ── Phone number ─────────────────────────────────────────
    elif step == "await_phone":
        phone = message.text.strip()
        try:
            from pyrogram import Client as PyroClient
            tmp  = PyroClient("tmp_login", api_id=Config.API_ID, api_hash=Config.API_HASH)
            await tmp.connect()
            sent = await tmp.send_code(phone)
            set_state(uid, "await_otp", phone=phone, phone_code_hash=sent.phone_code_hash, tmp=tmp)
            await message.reply(
                f"📲 OTP sєηᴅ нᴏ ɢᴀʏᴀ `{phone}` ρє\n\nᴀʙ OTP ʙнєᴊᴏ:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("˹ ◀️ ᴄᴀηᴄєʟ ˼", callback_data="config_main")]
                ]),
            )
        except Exception as e:
            clear_state(uid)
            await message.reply(f"❌ OTP sєηᴅ ηᴀнι нᴜᴀ: `{e}`")

    # ── OTP ──────────────────────────────────────────────────
    elif step == "await_otp":
        otp   = message.text.strip().replace(" ", "")
        phone = state.get("phone")
        hash_ = state.get("phone_code_hash")
        tmp   = state.get("tmp")
        try:
            await tmp.sign_in(phone, hash_, otp)
            session = await tmp.export_session_string()
            await tmp.stop()
            clear_state(uid)
            await _save_manual_session(client, message, session, uid)
        except Exception as e:
            await message.reply(f"❌ OTP ɢʟᴀᴛ нᴀι: `{e}`\nᴅᴏʙᴀʀᴀ ʙнєᴊᴏ:")

    # ── Manual session ───────────────────────────────────────
    elif step == "await_session_string":
        session = message.text.strip()
        clear_state(uid)
        await _save_manual_session(client, message, session, uid)

    # ── Target link ──────────────────────────────────────────
    elif step == "await_target_link":
        raw = message.text.strip()

        # Numeric chat id path — for userbots already in the group but
        # with no working invite link (e.g. link expired/revoked).
        if _is_chat_id_input(raw):
            target_chat_id = int(raw)
            clear_state(uid)
            status_msg = await message.reply("⏳ ᴄʜᴀᴛ ID sє ᴠєʀιғʏ ᴋʀ ʀᴀнᴀ нᴜη...")

            userbots = await get_all_userbots()
            joined   = []

            from VCFIGHTERS.core.userbot import userbot_manager
            for ub in userbots:
                try:
                    ub_client = userbot_manager.get_client(ub["session_string"])
                    await ub_client.get_chat(target_chat_id)
                    joined.append(ub.get("phone", "?"))
                    await asyncio.sleep(1)
                except Exception as e:
                    log.warning(f"Verify failed {ub.get('phone')}: {e}")

            if joined:
                await add_target({
                    "chat_id":         target_chat_id,
                    "invite_link":     None,
                    "userbots_joined": joined,
                    "added_at":        int(time.time()),
                })
                await status_msg.edit(
                    f"✅ **{len(joined)} ᴜsєʀʙᴏᴛs ᴀʟʀєᴀᴅʏ ϻєϻʙєʀ ᴠᴇʀιғιєᴅ**\n"
                    f"🎯 ᴛᴀʀɢєᴛ sᴀᴠєᴅ: `{target_chat_id}`",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="config_main")]
                    ]),
                )
            else:
                await status_msg.edit(
                    "❌ ᴋᴏι ʙнι ᴜsєʀʙᴏᴛ ιs ᴄнᴀᴛ ID ϻєιη ηᴀнιιη ϻιʟᴀ.\n"
                    "ᴜsєʀʙᴏᴛ ᴋᴏ ρнʟє ᴜs ɢʀᴏᴜρ ϻєιη ϻᴀηᴜᴀʟʟʏ ᴀᴅᴅ ᴋʀᴏ, ʏᴀ ᴠᴀʟιᴅ ʟιηᴋ ʙнєᴊᴏ."
                )
            return

        link = raw
        if not _is_valid_target_link(link):
            await message.reply(
                "❌ ιηᴠᴀʟιᴅ ʟιηᴋ.\n\n"
                "sυρρᴏʀᴛєᴅ ғᴏʀϻᴀᴛs:\n"
                "• ρʀιᴠᴀᴛє: `t.me/+xxxx`\n"
                "• ρᴜʙʟιᴄ: `t.me/groupname` ʏᴀ `@groupname`\n"
                "• ᴄʜᴀᴛ ID (ᴀɢᴀʀ ᴜsєʀʙᴏᴛ ᴀʟʀєᴀᴅʏ ϻєϻʙєʀ нᴀι): `-1001234567890`"
            )
            return
        clear_state(uid)
        status_msg = await message.reply("⏳ sᴀʙ ᴜsєʀʙᴏᴛs sє ᴊᴏιη ᴋʀ ʀᴀнᴀ нᴜη...")

        userbots = await get_all_userbots()
        joined   = []
        chat_id  = None

        from VCFIGHTERS.core.userbot import userbot_manager
        for ub in userbots:
            try:
                ub_client = userbot_manager.get_client(ub["session_string"])
                try:
                    chat = await ub_client.join_chat(link)
                except UserAlreadyParticipant:
                    # Userbot is already a member — fetch the chat instead of joining
                    chat = await ub_client.get_chat(link)
                    log.info(f"{ub.get('phone')} already in chat — using existing membership")
                chat_id = chat.id
                joined.append(ub.get("phone", "?"))
                await asyncio.sleep(3)
            except Exception as e:
                log.warning(f"Join failed {ub.get('phone')}: {e}")

        if chat_id:
            await add_target({
                "chat_id":         chat_id,
                "invite_link":     link,
                "userbots_joined": joined,
                "added_at":        int(time.time()),
            })
            await status_msg.edit(
                f"✅ **{len(joined)} ᴜsєʀʙᴏᴛs ᴊᴏιη нᴏ ɢᴀʏє**\n"
                f"🎯 ᴛᴀʀɢєᴛ sᴀᴠєᴅ: `{chat_id}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("˹ ◀️ 𝐁ᴀᴄᴋ ˼", callback_data="config_main")]
                ]),
            )
        else:
            await status_msg.edit("❌ ᴋᴏι ʙнι ᴜsєʀʙᴏᴛ ᴊᴏιη ηᴀнι ᴋʀ sᴋᴀ. ʟιηᴋ ᴄнєᴄᴋ ᴋᴀʀᴏ.")
