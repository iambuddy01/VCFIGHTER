import asyncio
import random
import time

import aiohttp
import psutil
from pyrogram import filters as pyro_filters
from pyrogram.types import Message

import Config
from VCFIGHTERS.core.bot import app
from VCFIGHTERS.database.mangodb import (
    active_userbot_count,
    get_all_targets,
    get_mode,
)
from VCFIGHTERS.logging import LOGGER

log = LOGGER("Start")

_boot_time = time.time()

# ══════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════

EFFECT_FIRE     = "5104841245755180586"
EFFECT_CONFETTI = "5046509860389126442"

VC_PICS = getattr(Config, "VC_PICS", [
    "https://files.catbox.moe/eje8y8.jpeg",
    "https://files.catbox.moe/ey2jzp.jpeg",
    "https://files.catbox.moe/ah5y0f.jpeg",
    "https://files.catbox.moe/we4yju.jpeg",
])

FIRE_FRAMES = [
    "🔥",
    "🔥🔥",
    "🔥🔥🔥",
    "⚔️ ᴠᴄғɪɢʜᴛᴇʀ...",
    "⚡ sᴛᴀʀᴛɪɴɢ ᴜᴘ...",
    "💀 ᴀᴡᴀᴋᴇɴɪɴɢ...",
]
FIRE_DELAY = 0.4

# ══════════════════════════════════════════════════════════════
#  RAW BOT API HELPERS
# ══════════════════════════════════════════════════════════════

def _api_btn(
    text: str,
    callback_data: str = None,
    url: str = None,
    style: str = None,
    emoji_id: str = None,
) -> dict:
    btn = {"text": text}
    if callback_data:
        btn["callback_data"] = callback_data
    if url:
        if not url.startswith("http") and not url.startswith("tg://"):
            url = f"https://t.me/{url.replace('@', '')}"
        btn["url"] = url
    if style in ("primary", "danger", "success"):
        btn["style"] = style
    if emoji_id:
        btn["icon_custom_emoji_id"] = str(emoji_id)
    return btn


async def _raw_api(method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/{method}"
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload) as r:
            return await r.json()


async def _send_magic(
    chat_id: int,
    photo_url: str,
    caption: str,
    markup: list,
    reply_to: int = None,
    effect_id: str = None,
) -> int | None:
    payload = {
        "chat_id":    chat_id,
        "photo":      photo_url,
        "caption":    caption,
        "parse_mode": "HTML",
        "has_spoiler": True,
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    if effect_id:
        payload["message_effect_id"] = effect_id

    res = await _raw_api("sendPhoto", payload)

    # Effect ya spoiler fail hua → clean retry
    if not res.get("ok"):
        log.warning(f"sendPhoto attempt 1 failed: {res.get('description')} — retrying without effect/spoiler")
        payload.pop("message_effect_id", None)
        payload.pop("has_spoiler", None)
        res = await _raw_api("sendPhoto", payload)

    if not res.get("ok"):
        log.error(f"sendPhoto failed completely: {res.get('description')}")
        return None

    msg_id = res["result"]["message_id"]

    kb_res = await _raw_api("editMessageReplyMarkup", {
        "chat_id":      chat_id,
        "message_id":   msg_id,
        "reply_markup": {"inline_keyboard": markup},
    })
    if not kb_res.get("ok"):
        log.warning(f"editMessageReplyMarkup failed: {kb_res.get('description')}")

    return msg_id


# ══════════════════════════════════════════════════════════════
#  BUTTON PANELS
# ══════════════════════════════════════════════════════════════

async def _private_panel() -> list:
    me          = await app.get_me()
    support_url = getattr(Config, "SUPPORT_URL", "https://t.me/Zcziiy")
    source_url  = getattr(Config, "SOURCE_URL",  "https://github.com/YOURNAME/VCFIGHTER")
    owner_id    = Config.OWNER_ID

    return [
        [
            _api_btn("˹ 𝐒ᴜᴘᴘᴏʀᴛ ˼",    url=support_url,                  style="danger",  emoji_id="5413415116756500503"),
            _api_btn("˹ 𝐔ᴘᴅᴀᴛᴇs ˼",     url=support_url,                  style="primary", emoji_id="5253539825360843975"),
        ],
        [
            _api_btn("˹ 𝐂ᴏɴғɪɢ ˼",       callback_data="vc_config",        style="primary", emoji_id="5238162283368035495"),
            _api_btn("˹ 𝐇ᴇʟᴘ ˼",         callback_data="vc_help",           style="success", emoji_id="5249244862359812334"),
        ],
        [
            _api_btn("˹ 𝐒ᴏᴜʀᴄᴇ 𝐂ᴏᴅᴇ ˼", url=source_url,                   style="primary", emoji_id="5296631769112525274"),
        ],
        [
            _api_btn("˹ 𝚳ʏ 𝚳ᴀsᴛᴇʀ ˼",   url=f"tg://user?id={owner_id}",   style="danger",  emoji_id="5201875852735820002"),
        ],
    ]


async def _group_panel() -> list:
    me          = await app.get_me()
    support_url = getattr(Config, "SUPPORT_URL", "https://t.me/Zcziiy")

    return [
        [
            _api_btn("˹ 𝐒ᴜᴘᴘᴏʀᴛ ˼", url=support_url,                                        style="danger",  emoji_id="5413415116756500503"),
            _api_btn("˹ 𝐂ᴏɴғɪɢ ˼",  url=f"https://t.me/{me.username}?start=config",        style="primary", emoji_id="5238162283368035495"),
        ],
        [
            _api_btn("˹ 𝐃ᴍ 𝐌ᴇ ˼",   url=f"https://t.me/{me.username}",                      style="success", emoji_id="5471952986970267163"),
        ],
    ]


# ══════════════════════════════════════════════════════════════
#  STATS HELPERS
# ══════════════════════════════════════════════════════════════

def _uptime() -> str:
    secs = int(time.time() - _boot_time)
    h, r = divmod(secs, 3600)
    m, s = divmod(r, 60)
    return f"{h}ʜ:{m:02d}ᴍ:{s:02d}s"


def _sys_stats() -> tuple[float, float, float]:
    cpu  = psutil.cpu_percent(interval=0.1)
    ram  = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    return cpu, ram, disk


# ══════════════════════════════════════════════════════════════
#  CAPTIONS
# ══════════════════════════════════════════════════════════════

async def _private_caption(mention: str) -> str:
    me              = await app.get_me()
    cpu, ram, disk  = _sys_stats()
    ub_count        = await active_userbot_count()
    targets         = await get_all_targets()
    mode            = await get_mode()

    return (
        f"┌─── ˹ <b>ᴠᴄғɪɢʜᴛᴇʀ</b> ˼ ─── ⏤‌‌●\n"
        f"<emoji id=\"5262770659267735289\">😈</emoji> ┆ <b>ʜᴇʏ, {mention}</b>\n"
        f"<emoji id=\"6291835288561917135\">😎</emoji> ┆ <b>ɪ ᴀᴍ @{me.username}</b>\n"
        f"└──────────────────────•\n\n"
        f"<blockquote>"
        f"<spoiler><b><emoji id=\"6294070144729619431\">💀</emoji> ᴛʜᴇ ᴜʟᴛɪᴍᴀᴛᴇ ᴠᴄ ғɪɢʜᴛᴇʀ ʙᴏᴛ!</b></spoiler>"
        f"</blockquote>\n"
        f"<blockquote>"
        f"<b><emoji id=\"6294063539069917326\">😉</emoji> ᴜᴘᴛɪᴍᴇ:</b> {_uptime()}\n"
        f"<b><emoji id=\"5413415116756500503\">☠️</emoji> ᴄᴘᴜ ʟᴏᴀᴅ:</b> {cpu}%\n"
        f"<b><emoji id=\"6080176744709495278\">🐾</emoji> ʀᴀᴍ:</b> {ram}%\n"
        f"<b><emoji id=\"6291837599254322363\">💾</emoji> ᴅɪsᴋ:</b> {disk}%"
        f"</blockquote>\n"
        f"<blockquote>"
        f"<b><emoji id=\"5999100917645841519\">💀</emoji> ᴜsᴇʀʙᴏᴛs:</b> {ub_count} ᴀᴄᴛɪᴠᴇ\n"
        f"<b><emoji id=\"5413546177683539369\">😈</emoji> ᴛᴀʀɢᴇᴛs:</b> {len(targets)}\n"
        f"<b><emoji id=\"6001132493011425597\">⚡</emoji> ᴍᴏᴅᴇ:</b> {mode.upper()}"
        f"</blockquote>\n"
        f"•──────────────────────•\n"
        f"<blockquote>"
        f"<b><emoji id=\"6294023338176028117\">💀</emoji> ✦ᴘᴏᴡᴇʀᴇᴅ ʙʏ » "
        f"<a href=\"{getattr(Config, 'SUPPORT_URL', 'https://t.me/Zcziiy')}\">"
        f"<spoiler>── 𝛞 𝛜 𝛈 𝛔 𝛈</spoiler></a></b>"
        f"</blockquote>\n"
        f"•──────────────────────•"
    )


async def _group_caption(group_name: str) -> str:
    ub_count = await active_userbot_count()
    mode     = await get_mode()
    return (
        f"<blockquote>"
        f"<emoji id=\"6080176744709495278\">🐾</emoji> ʜᴇʟʟᴏ~ <b>ɪ'ᴍ ᴠᴄғɪɢʜᴛᴇʀ</b> ᴀɴᴅ ɪ'ᴍ ᴀʟɪᴠᴇ! ✨\n\n"
        f"<emoji id=\"5413415116756500503\">☠️</emoji> <b>ᴜᴘᴛɪᴍᴇ   :</b> <code>{_uptime()}</code>\n"
        f"<emoji id=\"5999100917645841519\">💀</emoji> <b>ᴜsᴇʀʙᴏᴛs:</b> {ub_count} ᴀᴄᴛɪᴠᴇ\n"
        f"<emoji id=\"6001132493011425597\">⚡</emoji> <b>ᴍᴏᴅᴇ    :</b> {mode.upper()}\n\n"
        f"<spoiler><emoji id=\"5262770659267735289\">⚡</emoji> ᴠᴄ ғɪɢʜᴛᴇʀ — ᴘᴏᴡᴇʀᴇᴅ ʙʏ ʏᴜᴋɪᴛᴇᴀᴍ</spoiler>"
        f"</blockquote>"
    )


# ══════════════════════════════════════════════════════════════
#  FIRE ANIMATION
# ══════════════════════════════════════════════════════════════

async def _fire_animation(message: Message) -> Message | None:
    try:
        anim = await message.reply_text(FIRE_FRAMES[0])
        for frame in FIRE_FRAMES[1:]:
            await asyncio.sleep(FIRE_DELAY)
            await anim.edit_text(frame)
        return anim
    except Exception as e:
        log.warning(f"Fire animation failed: {e}")
        return None


# ══════════════════════════════════════════════════════════════
#  /start — PRIVATE
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.command("start") & pyro_filters.private)
async def start_private(client, message: Message):
    user    = message.from_user
    mention = f"<a href=\"tg://user?id={user.id}\">{user.first_name}</a>"

    anim = await _fire_animation(message)

    caption = await _private_caption(mention)
    panel   = await _private_panel()

    sent_id = await _send_magic(
        chat_id=message.chat.id,
        photo_url=random.choice(VC_PICS),
        caption=caption,
        markup=panel,
        effect_id=EFFECT_FIRE,
    )

    if anim:
        try:
            await anim.delete()
        except Exception:
            pass

    if sent_id:
        try:
            await _raw_api("setMessageReaction", {
                "chat_id":    message.chat.id,
                "message_id": sent_id,
                "reaction":   [{"type": "emoji", "emoji": "🔥"}],
                "is_big":     True,
            })
        except Exception:
            pass

    if Config.LOG_CHANNEL:
        try:
            await client.send_message(
                Config.LOG_CHANNEL,
                f"<emoji id=\"6080176744709495278\">🐾</emoji> "
                f"{mention} started the bot.\n"
                f"<b>ɪᴅ ➠</b> <code>{user.id}</code>",
            )
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
#  /start — GROUP
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.command("start") & pyro_filters.group)
async def start_group(client, message: Message):
    try:
        await _raw_api("setMessageReaction", {
            "chat_id":    message.chat.id,
            "message_id": message.id,
            "reaction":   [{"type": "emoji", "emoji": "🔥"}],
            "is_big":     False,
        })
    except Exception:
        pass

    caption = await _group_caption(message.chat.title or "Group")
    panel   = await _group_panel()

    await _send_magic(
        chat_id=message.chat.id,
        photo_url=random.choice(VC_PICS),
        caption=caption,
        markup=panel,
        reply_to=message.id,
        effect_id=None,  # groups mein effect nahi chalta
    )


# ══════════════════════════════════════════════════════════════
#  CONFIG / HELP CALLBACKS
# ══════════════════════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^vc_config$"))
async def cb_config(client, cq):
    from VCFIGHTERS.FIGHTERS.Settings import is_authorized
    if not await is_authorized(cq.from_user.id):
        return await cq.answer("⛔ 𝚫ᴄᴄᴇss ᴅᴇɴɪᴇᴅ", show_alert=True)
    await cq.answer()
    await client.send_message(cq.message.chat.id, "⚙️ /config")


@app.on_callback_query(pyro_filters.regex("^vc_help$"))
async def cb_help(client, cq):
    await cq.answer()
    await client.send_message(cq.message.chat.id, "ℹ️ /help")


# ══════════════════════════════════════════════════════════════
#  BOT ADDED TO GROUP
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.new_chat_members)
async def on_bot_added(client, message: Message):
    me = await client.get_me()
    for member in message.new_chat_members:
        if member.id != me.id:
            continue

        caption = await _group_caption(message.chat.title or "Group")
        panel   = await _group_panel()

        run = await message.reply_text(
            f"<emoji id=\"6080202089311507876\">😎</emoji> "
            f"<b>ʜᴇʟʟᴏ {message.chat.title}!</b>\n"
            f"<emoji id=\"6001132493011425597\">💖</emoji> "
            f"ᴛʜᴀɴᴋs ғᴏʀ ᴀᴅᴅɪɴɢ ᴍᴇ!"
        )
        await _raw_api("editMessageReplyMarkup", {
            "chat_id":      message.chat.id,
            "message_id":   run.id,
            "reply_markup": {"inline_keyboard": panel},
        })

        async def _auto_del():
            await asyncio.sleep(15)
            try:
                await run.delete()
            except Exception:
                pass

        asyncio.create_task(_auto_del())

        if Config.LOG_CHANNEL:
            try:
                await client.send_message(
                    Config.LOG_CHANNEL,
                    f"<emoji id=\"6293940475371986355\">🎉</emoji> "
                    f"<b>ᴀᴅᴅᴇᴅ ᴛᴏ ɢʀᴏᴜᴘ!</b>\n\n"
                    f"<b>📌 ɴᴀᴍᴇ :</b> {message.chat.title}\n"
                    f"<b>🆔 ɪᴅ :</b> <code>{message.chat.id}</code>",
                )
            except Exception:
                pass
        break
    
