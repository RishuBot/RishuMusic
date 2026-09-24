# ============================================================
# start.py — v8
# CHANGELOG (v7 -> v8):
#   - FIX: 400 BUTTON_URL_INVALID on send_rich_message() in start_pm.
#     Causes removed:
#       * <tg-button type="url" data="tg://user?id=..."> inside the rich
#         body (tg:// deep links are rejected there) -> removed. The Owner
#         button still exists in the inline keyboard below
#         (private_panel uses user_id=config.OWNER_ID).
#       * config.SUPPORT_CHANNEL used raw -> now cleaned via safe_url()
#         (handles @user, t.me/xyz, empty value); button skipped if invalid.
#       * app.username could be None right after boot -> guarded.
#   - Safety net: if send_rich_message() still raises ButtonUrlInvalid, it
#     retries ONCE with the rich body WITHOUT its button rows (inline
#     keyboard below still shows), then only falls back to reply_photo.
#   - Everything else same as v7.
# ============================================================

import random
import time
import traceback
from html import escape

from py_yt import VideosSearch
from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.errors import ButtonUrlInvalid
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


def safe_url(u):
    """
    Cleans a URL for Telegram buttons. Returns a valid https:// URL or None.
    Handles: empty, '@username', 't.me/xyz', 'http(s)://...'.
    tg:// links are NOT accepted here (Telegram rejects them in rich-body buttons).
    """
    u = (str(u) if u is not None else "").strip()
    if not u:
        return None
    if u.startswith("@"):
        return "https://t.me/" + u[1:]
    if u.startswith(("t.me/", "telegram.me/")):
        return "https://" + u
    if u.startswith(("http://", "https://")):
        return u
    return None


def get_start_img() -> str:
    """Returns a random start image URL (used by both the slideshow and the fallback photo)."""
    return random.choice(Kanha_Pic)


def rich_start_html(
    _,
    user_mention: str,
    bot_mention: str,
    uptime: str,
    is_admin: bool = False,
    with_buttons: bool = True,
) -> str:
    """
    Real Bot API 10.3 rich-message body for the private /start screen:
    <tg-slideshow> + heading + feature list + snapshot blockquote + <tg-button-row>s.
    with_buttons=False builds the body without any button rows (retry path).
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

    table = (
        "<h2>BOT SNAPSHOT</h2>"
        "<table>"
        "<tr><th>Field</th><th>Value</th></tr>"
        f"<tr><td>Status</td><td>{custom_emoji('✅')} Online</td></tr>"
        f"<tr><td>Uptime</td><td>{escape(uptime)}</td></tr>"
        f"<tr><td>Plan</td><td>{'Admin' if is_admin else 'Free'}</td></tr>"
        "</table>"
    )

    body = slideshow + heading + features + table
    if not with_buttons:
        return body

    # ---- button rows (only URLs that pass safe_url are added) ----
    buttons = ""

    add_url = safe_url(f"https://t.me/{app.username}?startgroup=true") if getattr(app, "username", None) else None
    if add_url:
        buttons += (
            '<tg-button-row align="center">'
            f'<tg-button type="url" style="primary" data="{escape(add_url, quote=True)}">'
            f"{escape(_['S_B_3'])}</tg-button>"
            "</tg-button-row>"
        )

    support_url = safe_url(getattr(config, "SUPPORT_CHANNEL", None))
    if support_url:
        buttons += (
            '<tg-button-row align="center">'
            f'<tg-button type="url" style="primary" data="{escape(support_url, quote=True)}">'
            f"{escape(_['S_B_5'])}</tg-button>"
            "</tg-button-row>"
        )

    buttons += (
        '<tg-button-row align="center">'
        f'<tg-button type="callback_data" style="success" data="settings_back_helper">'
        f"{escape(_['S_B_4'])}</tg-button>"
        "</tg-button-row>"
    )
    if is_admin:
        buttons += (
            '<tg-button-row align="center">'
            f'<tg-button type="callback_data" style="danger" data="admin_panel">'
            f"{custom_emoji('⚙️')} Admin Panel</tg-button>"
            "</tg-button-row>"
        )

    return body + buttons


def build_reply_markup(_, is_admin: bool = False) -> InlineKeyboardMarkup:
    """
    Real button set — reuses RishuMusic.utils.inline.private_panel() as-is
    (correct string keys, real callback_data 'settings_back_helper', and
    user_id=config.OWNER_ID for the Owner button) instead of inventing new
    buttons with no matching handler. Only the admin row is new.
    """
    buttons = list(private_panel(_))
    if is_admin:
        buttons = buttons + [[InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")]]
    return InlineKeyboardMarkup(buttons)


async def _send_rich_start(client, message: Message, _, uptime: str, is_admin: bool, with_buttons: bool):
    rich_html = rich_start_html(
        _,
        user_mention=message.from_user.mention,
        bot_mention=app.mention,
        uptime=uptime,
        is_admin=is_admin,
        with_buttons=with_buttons,
    )
    await client.send_rich_message(
        chat_id=message.chat.id,
        rich_message=InputRichMessage(html=rich_html),
        reply_parameters=ReplyParameters(message_id=message.id),
        effect_id=random.choice(EFFECT_ID),
        reply_markup=build_reply_markup(_, is_admin=is_admin),
    )


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
        uptime = get_readable_time(int(time.time() - _boot_))
        is_admin = message.from_user.id in getattr(config, "SUDO_USERS", set()) or message.from_user.id == getattr(config, "OWNER_ID", None)

        sent = False
        if RICH_MESSAGES_SUPPORTED:
            try:
                await _send_rich_start(client, message, _, uptime, is_admin, with_buttons=True)
                sent = True
            except ButtonUrlInvalid as ex:
                # A button URL in the rich body was rejected — retry without body buttons.
                print(f"[start_pm] BUTTON_URL_INVALID in rich body, retrying without buttons: {ex}")
                try:
                    await _send_rich_start(client, message, _, uptime, is_admin, with_buttons=False)
                    sent = True
                except Exception as ex2:
                    print(f"[start_pm] retry without buttons failed, falling back: {ex2}")
                    traceback.print_exc()
            except Exception as ex:
                # Fork/server doesn't actually support it yet — fall back below.
                print(f"[start_pm] send_rich_message failed, falling back: {ex}")
                traceback.print_exc()

        if not sent:
            await message.reply_photo(
                photo=get_start_img(),
                has_spoiler=True,
                effect_id=random.choice(EFFECT_ID),
                caption=_["start_2"].format(message.from_user.mention, app.mention),
                reply_markup=build_reply_markup(_, is_admin=is_admin),
            )

        if await is_on_off(2):
            return await app.send_message(
                chat_id=config.LOGGER_ID,
                text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
            )


# "settings_back_helper" is handled by your existing settings plugin.
# "admin_panel" is new, so it has its own handler here.
@app.on_callback_query(filters.regex("^admin_panel$"))
async def on_admin_panel_callback(client, callback_query):
    is_admin = callback_query.from_user.id in getattr(config, "SUDO_USERS", set()) or callback_query.from_user.id == getattr(config, "OWNER_ID", None)
    if not is_admin:
        return await callback_query.answer("Admins only.", show_alert=True)
    await callback_query.answer()
    await callback_query.message.reply_text("⚙️ Admin panel — wire this up to your actual admin commands.")


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
