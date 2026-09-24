# ============================================================
# start.py — v5
# CHANGELOG (v4 -> v5):
#   - PRODUCTION CRASH FIX: your logs showed
#       TypeError: Message.reply_photo() got an unexpected keyword
#       argument 'message_effect_id'
#     at plugins/bot/start.py line 118 — that's the fallback branch
#     (send_rich_message isn't landing, so it's falling back to
#     reply_photo()). Checked Kurigram's real reply_photo() signature:
#     the param is effect_id, not message_effect_id (I'd only fixed
#     this on the send_rich_message() call in v4, not on the
#     reply_photo() fallback — fixed now on both).
#   - Also added a startup log line so you can see in the container
#     logs whether RICH_MESSAGES_SUPPORTED came back True or False,
#     and the full exception if send_rich_message() itself raises —
#     so we know for sure whether it's actually landing on your
#     install or silently falling back every time.
# CHANGELOG (v3 -> v4):
#   - CONFIRMED against the actual Kurigram 2.2.26 source: your Kurigram
#     already ships send_rich_message natively (pyrogram/methods/messages/
#     send_rich_message.py + pyrogram/types/input_content/input_rich_message.py)
#     — no pyrogrammod/ftmgram switch needed, and the ImportError fallback
#     path is now just a safety net for an OLDER Kurigram install, not the
#     expected path.
#   - Fixed two param names to match the real send_rich_message() signature:
#       * reply_to_message_id -> reply_parameters=ReplyParameters(message_id=...)
#       * message_effect_id   -> effect_id
#     (both taken from Kurigram's own send_rich_message docstring/signature)
#   - Everything else (the <tg-slideshow>/<tg-button-row>/<tg-emoji> body,
#     the fallback screen, group /start, welcome, help/sud/info branches)
#     is unchanged from v3.
#   - If you're on an older kurigram, run: pip install -U kurigram
# ============================================================

import random
import time
from html import escape

from py_yt import VideosSearch
from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

try:
    # Bot API 10.1+ rich messages — present natively in Kurigram >= 2.2.26.
    from pyrogram.types import InputRichMessage, ReplyParameters
    RICH_MESSAGES_SUPPORTED = True
except ImportError:
    # Older Kurigram install — update with: pip install -U kurigram
    RICH_MESSAGES_SUPPORTED = False

print(f"[start.py] RICH_MESSAGES_SUPPORTED = {RICH_MESSAGES_SUPPORTED}")
if not RICH_MESSAGES_SUPPORTED:
    print(
        "[start.py] InputRichMessage/ReplyParameters not importable from "
        "pyrogram.types — run `pip show kurigram` and confirm it's >= 2.2.26, "
        "then `pip install -U kurigram` if not."
    )

import config
from RishuMusic import app
from RishuMusic.misc import _boot_
from RishuMusic.plugins.sudo.sudoers import sudoers_list
from RishuMusic.utils.database import (add_served_chat, add_served_user,
                                       blacklisted_chats, get_lang,
                                       is_banned_user, is_on_off)
from RishuMusic.utils.decorators.language import LanguageStart
from RishuMusic.utils.formatters import get_readable_time
from RishuMusic.utils.inline import help_pannel, private_panel, start_panel
from config import BANNED_USERS
from strings import get_string

EFFECT_ID = [
    5104841245755180586,
    5107584321108051014,
    5044134455711629726,
    5046509860389126442,
    5046589136895476101,
    5104858069142078462,
    5104841245755180586,
    5107584321108051014,
    5046589136895476101,
    5104858069142078462,
    5104841245755180586,
    5107584321108051014,
]

Kanha_Pic = [
    "https://files.catbox.moe/v00l7e.jpg",
    "https://files.catbox.moe/uow54p.jpg",
    "https://files.catbox.moe/z0t6l3.jpg",
    "https://files.catbox.moe/jdw0il.jpg",
    "https://files.catbox.moe/izfi0y.jpg",
    "https://files.catbox.moe/7wx3ha.jpg",
    "https://files.catbox.moe/2u0srm.jpg",
    "https://files.catbox.moe/tqwy0q.jpg",
    "https://files.catbox.moe/vbgrx1.jpg",
]

# ---- Custom-emoji icon map (trimmed to what's used on this screen) ----
CUSTOM_EMOJI_MAP = {
    "🚀": "6140920041975061182",
    "💎": "5944994203846054620",
    "👤": "5258011929993026890",
    "🔗": "5767297774584339394",
    "❤️": "6136415987081157088",
    "🏠": "5416041192905265756",
    "⚙️": "5308624268255460504",
    "✅": "6172517356162520126",
    "📊": "4958621433509970793",
    "🎉": "6134194260628479379",
    "📢": "5298609030321691620",
    "🆘": "5947494995798789024",
}


def custom_emoji(name: str) -> str:
    """
    Real Bot API custom-emoji HTML tag: <tg-emoji emoji-id="...">🔥</tg-emoji>.
    Falls back to the plain emoji if it's not in the map.
    """
    emoji_id = CUSTOM_EMOJI_MAP.get(name)
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{name}</tg-emoji>'
    return name


def get_start_img() -> str:
    """Returns a random start image URL (used by both the slideshow and the fallback photo)."""
    return random.choice(Kanha_Pic)


def rich_start_html(_, user_mention: str, bot_mention: str, uptime: str, is_admin: bool = False) -> str:
    """
    Real Bot API 10.3 rich-message body for the private /start screen:
    <tg-slideshow> + heading + feature list + snapshot blockquote + <tg-button-row>s.
    """
    slideshow = (
        "<tg-slideshow>"
        + "".join(f'<img src="{url}"/>' for url in Kanha_Pic)
        + f"<figcaption>{escape(str(app.name if hasattr(app, 'name') else 'RishuMusic'))} — Swipe to explore</figcaption>"
        + "</tg-slideshow>"
    )

    heading = (
        f"<h1>{custom_emoji('💎')} {bot_mention} • Music Hub</h1>"
        f"<p><i>Fast • clean • powerful voice-chat streaming</i></p>"
        f"<p>{custom_emoji('❤️')} <b>Welcome, {user_mention}</b><br/>"
        f"<i>Send /play with a song name or link to get started.</i></p>"
    )

    features = (
        "<h2>WHAT I CAN DO</h2>"
        "<blockquote>"
        f"{custom_emoji('🚀')} Stream music &amp; video in voice chats<br/>"
        f"{custom_emoji('🔗')} Play from YouTube, Spotify links &amp; more<br/>"
        f"{custom_emoji('📊')} Smart autoplay with mood-based picks<br/>"
        f"{custom_emoji('🏠')} Reliable, MongoDB-backed play history"
        "</blockquote>"
    )

    snapshot = (
        "<h2>BOT SNAPSHOT</h2>"
        "<blockquote>"
        f"├ Status • {custom_emoji('✅')} <b>Online</b><br/>"
        f"└ Uptime • <b>{escape(uptime)}</b>"
        "</blockquote>"
    )

    buttons = (
        '<tg-button-row align="center">'
        f'<tg-button type="url" style="primary" url="https://t.me/{app.username}?startgroup=true">'
        f"{custom_emoji('🚀')} Add Me To Your Chat</tg-button>"
        "</tg-button-row>"
        '<tg-button-row align="center">'
        f'<tg-button type="callback_data" style="primary" data="help_callback">'
        f"{custom_emoji('🚀')} Commands</tg-button>"
        f'<tg-button type="url" style="primary" url="https://t.me/{getattr(config, "OWNER_USERNAME", "RishuCoder")}">'
        f"{custom_emoji('💎')} Owner</tg-button>"
        "</tg-button-row>"
        '<tg-button-row align="center">'
        f'<tg-button type="url" style="success" url="{config.SUPPORT_CHANNEL if hasattr(config, "SUPPORT_CHANNEL") else config.SUPPORT_CHAT}">'
        f"{custom_emoji('📢')} Updates</tg-button>"
        f'<tg-button type="url" style="success" url="{config.SUPPORT_CHAT}">'
        f"{custom_emoji('🆘')} Support</tg-button>"
        "</tg-button-row>"
    )
    if is_admin:
        buttons += (
            '<tg-button-row align="center">'
            f'<tg-button type="callback_data" style="danger" data="admin_panel">'
            f"{custom_emoji('⚙️')} Admin Panel</tg-button>"
            "</tg-button-row>"
        )

    return slideshow + heading + features + snapshot + buttons


def fallback_start_buttons(is_admin: bool = False):
    """Plain InlineKeyboardMarkup used only if send_rich_message isn't available."""
    rows = [
        [InlineKeyboardButton("🚀 Add Me To Your Chat", url=f"https://t.me/{app.username}?startgroup=true")],
        [
            InlineKeyboardButton("🚀 Commands", callback_data="help_callback"),
            InlineKeyboardButton("💎 Owner", url=f"https://t.me/{getattr(config, 'OWNER_USERNAME', 'RishuCoder')}"),
        ],
        [
            InlineKeyboardButton("📢 Updates", url=config.SUPPORT_CHANNEL if hasattr(config, "SUPPORT_CHANNEL") else config.SUPPORT_CHAT),
            InlineKeyboardButton("🆘 Support", url=config.SUPPORT_CHAT),
        ],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    return rows


@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    await add_served_user(message.from_user.id)
    await message.react("🍓", big=True)
    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]
        if name[0:4] == "help":
            keyboard = help_pannel(_)
            return await message.reply_photo(
                photo=get_start_img(),
                has_spoiler=False,
                caption=_["help_1"].format(config.SUPPORT_CHAT),
                reply_markup=keyboard,
            )
        if name[0:3] == "sud":
            await sudoers_list(client=client, message=message, _=_)
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>sᴜᴅᴏʟɪsᴛ</b>.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
                )
            return
        if name[0:3] == "inf":
            m = await message.reply_text("👀")
            query = (str(name)).replace("info_", "", 1)
            query = f"https://www.youtube.com/watch?v={query}"
            results = VideosSearch(query, limit=1)
            for result in (await results.next())["result"]:
                title = result["title"]
                duration = result["duration"]
                views = result["viewCount"]["short"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                channellink = result["channel"]["link"]
                channel = result["channel"]["name"]
                link = result["link"]
                published = result["publishedTime"]
            searched_text = _["start_6"].format(
                title, duration, views, published, channellink, channel, app.mention
            )
            key = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text=_["S_B_8"], url=link),
                        InlineKeyboardButton(text=_["S_B_9"], url=config.SUPPORT_CHAT),
                    ],
                ]
            )
            await m.delete()
            await app.send_photo(
                chat_id=message.chat.id,
                photo=thumbnail,
                has_spoiler=True,
                caption=searched_text,
                reply_markup=key,
            )
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>ᴛʀᴀᴄᴋ ɪɴғᴏʀᴍᴀᴛɪᴏɴ</b>.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
                )
    else:
        # ---- v3: real Bot API 10.3 rich message for the plain /start screen ----
        uptime = get_readable_time(int(time.time() - _boot_))
        is_admin = message.from_user.id in getattr(config, "SUDO_USERS", set()) or message.from_user.id == getattr(config, "OWNER_ID", None)

        sent = False
        if RICH_MESSAGES_SUPPORTED:
            try:
                rich_html = rich_start_html(
                    _,
                    user_mention=message.from_user.mention,
                    bot_mention=app.mention,
                    uptime=uptime,
                    is_admin=is_admin,
                )
                await client.send_rich_message(
                    chat_id=message.chat.id,
                    rich_message=InputRichMessage(html=rich_html),
                    reply_parameters=ReplyParameters(message_id=message.id),
                    effect_id=random.choice(EFFECT_ID),
                )
                sent = True
            except Exception as ex:
                # Fork/server doesn't actually support it yet — fall back below.
                import traceback
                print(f"[start_pm] send_rich_message failed, falling back: {ex}")
                traceback.print_exc()

        if not sent:
            keyboard = fallback_start_buttons(is_admin=is_admin)
            await message.reply_photo(
                photo=get_start_img(),
                has_spoiler=True,
                effect_id=random.choice(EFFECT_ID),
                caption=_["start_2"].format(message.from_user.mention, app.mention),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        if await is_on_off(2):
            return await app.send_message(
                chat_id=config.LOGGER_ID,
                text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
            )


@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    out = start_panel(_)
    uptime = int(time.time() - _boot_)
    await message.reply_photo(
        photo=get_start_img(),
        has_spoiler=True,
        caption=_["start_1"].format(app.mention, get_readable_time(uptime)),
        reply_markup=InlineKeyboardMarkup(out),
    )
    return await add_served_chat(message.chat.id)


@app.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)
            if await is_banned_user(member.id):
                try:
                    await message.chat.ban_member(member.id)
                except:
                    pass
            if member.id == app.id:
                if message.chat.type != ChatType.SUPERGROUP:
                    await message.reply_text(_["start_4"])
                    return await app.leave_chat(message.chat.id)
                if message.chat.id in await blacklisted_chats():
                    await message.reply_text(
                        _["start_5"].format(
                            app.mention,
                            f"https://t.me/{app.username}?start=sudolist",
                            config.SUPPORT_CHAT,
                        ),
                        disable_web_page_preview=True,
                    )
                    return await app.leave_chat(message.chat.id)

                out = start_panel(_)
                await message.reply_photo(
                    photo=get_start_img(),
                    has_spoiler=True,
                    caption=_["start_3"].format(
                        message.from_user.first_name,
                        app.mention,
                        message.chat.title,
                        app.mention,
                    ),
                    reply_markup=InlineKeyboardMarkup(out),
                )
                await add_served_chat(message.chat.id)
                await message.stop_propagation()
        except Exception as ex:
            print(ex)
