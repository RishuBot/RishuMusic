# ============================================================
# start.py — v12
# CHANGELOG (v11 -> v12):
#   - Added more body text: extra items in WHAT I CAN DO, a new
#     "WHY THIS BOT" paragraph, and a footer tip line below the buttons.
#   - Buttons themselves are unchanged from v11 — still need your logs
#     (the [rich_start_html] add_url=/support_url= print + whichever
#     exception fires after /start) to confirm they're landing now.
# CHANGELOG (v10 -> v11):
#   - Your logs showed TWO separate errors:
#       1) ButtonUrlInvalid on the first send (a url-type <tg-button> —
#          Add to Group or Support — was rejected).
#       2) EffectIdInvalid on the retry — this only surfaced once buttons
#          were dropped, proving effect_id itself is the problem on
#          send_rich_message (random.choice(EFFECT_ID) picks a different id
#          each retry, and this endpoint doesn't accept these ids the same
#          way normal send_message does).
#   - FIX: dropped effect_id from send_rich_message entirely (kept only on
#     the reply_photo fallback, where it's known to work).
#   - FIX: retry cascade is now 3-level instead of 2:
#       all buttons -> callback-only buttons (drops Add to Group/Support
#       URLs, keeps Help/Admin) -> no buttons at all -> reply_photo.
#     Added a debug print of add_url/support_url so the container logs show
#     exactly which URL value is being sent (check SUPPORT_CHANNEL / bot
#     username in your logs after the next /start if it still fails).
# CHANGELOG (v9 -> v10):
#   - REAL FIX for rich buttons never appearing: your rich_ui.py reference
#     confirms the actual Bot API 10.3 tag is
#         <tg-button url="...">text</tg-button>
#         <tg-button callback_data="...">text</tg-button>
#     My earlier <tg-button-row><tg-button type="url" data="...">...
#     was an invented tag/attrs from before I had this reference — Telegram
#     silently dropped the whole unknown block, which is why nothing showed.
#     Rewrote all rich buttons with the confirmed url=/callback_data= form.
#   - Table IS a real rich tag (confirmed by rich_ui.py's rich_table()) — no
#     need to avoid it. "BOT SNAPSHOT" is now a real open/close element too:
#     wrapped in <details><summary>...</summary><table>...</table></details>,
#     so it's collapsed-by-default AND still a table, not a tradeoff.
#   - Both button paths are kept, as asked: the rich <tg-button> elements
#     inside the message body, AND the normal inline reply_markup keyboard
#     below the message (build_reply_markup / private_panel) — Telegram
#     renders both at once.
# CHANGELOG (v8 -> v9):
#   - "BOT SNAPSHOT" is no longer a <table> (Telegram's supported HTML tag
#     set for messages does NOT include table/tr/td/th, so it either did
#     nothing or rendered as raw text). Replaced with a real Bot API
#     feature: <blockquote expandable="expandable"> — a genuine collapsed
#     "Show more / Show less" block. This is the "open/close type" you
#     asked for, and it's standard HTML-mode Telegram, not fork-specific.
#   - HTML tightened: every dynamic value going into the rich body now
#     goes through escape() (uptime, plan already did; nothing user-typed
#     was unescaped, kept it that way).
#   - Buttons: unchanged from v8 — they're built in rich_start_html()
#     (Add to Group / Support / Help / Admin) AND passed again as a normal
#     inline reply_markup via build_reply_markup(), which is the
#     guaranteed-to-render path regardless of rich-body button support.
#     If they still don't show after this deploy, send a screenshot
#     scrolled to the very bottom of the message (buttons render after
#     the blockquote) plus the container logs right after /start.
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


def rich_user_name(user) -> str:
    """
    HTML-safe bold name for the rich body. Do NOT use user.mention here:
    Kurigram's .mention returns a raw <a href=tg://...> string which the rich
    parser shows as literal text (and names like '</3' would break the HTML).
    """
    name = " ".join(p for p in [user.first_name, user.last_name] if p) or "User"
    return f"<b>{escape(name)}</b>"


def rich_bot_name() -> str:
    """HTML-safe bot name, linked to the bot via a normal https://t.me link."""
    name = escape(str(getattr(app, "name", None) or getattr(app, "first_name", None) or "RishuMusic"))
    username = getattr(app, "username", None)
    if username:
        return f'<a href="https://t.me/{username}">{name}</a>'
    return name


def rich_button(text: str, url: str = None, callback_data: str = None, style: str = None) -> str:
    """
    Real Bot API 10.3 rich-message button: <tg-button url="..."> or
    <tg-button callback_data="...">. NOT <tg-button-row>/type=/data= — that
    was an invented tag/attrs from an earlier version and Telegram silently
    dropped it, which is why no rich buttons ever appeared.
    """
    style_attr = f' style="{escape(style, quote=True)}"' if style else ""
    if callback_data:
        return f'<tg-button callback_data="{escape(callback_data, quote=True)}"{style_attr}>{text}</tg-button>'
    if url:
        return f'<tg-button url="{escape(url, quote=True)}"{style_attr}>{text}</tg-button>'
    return f"<tg-button{style_attr}>{text}</tg-button>"


def rich_table(headers, rows, border: int = 1) -> str:
    """Real <table> rich block. Cells are emitted verbatim (escape values yourself first)."""
    parts = [f'<table border="{int(border)}">']
    if headers:
        parts.append("<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>")
    for row in rows or ():
        parts.append("<tr>" + "".join(f"<td>{'' if c is None else c}</td>" for c in row) + "</tr>")
    parts.append("</table>")
    return "".join(parts)


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
    url_buttons: bool = True,
) -> str:
    """
    Bot API 10.3 rich-message body for the private /start screen:
    <tg-slideshow> + heading + feature list + <details>/<summary>+<table>
    snapshot + real <tg-button> elements. with_buttons=False builds the body
    without buttons (retry path).
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
        f"<p>{custom_emoji('❤️')} <b>Welcome,</b> {user_mention}<br/>"
        f"<i>Send /play with a song name or link to get started.</i></p>"
    )

    features = (
        "<h2>WHAT I CAN DO</h2>"
        "<blockquote>"
        f"{custom_emoji('🚀')} Stream music &amp; video in voice chats<br/>"
        f"{custom_emoji('🔗')} Play from YouTube, Spotify links &amp; more<br/>"
        f"{custom_emoji('📊')} Smart autoplay with mood-based picks<br/>"
        f"{custom_emoji('🏠')} Reliable, MongoDB-backed play history<br/>"
        f"{custom_emoji('📢')} Works in groups, channels &amp; voice chats alike<br/>"
        f"{custom_emoji('🎉')} Playlists, queue control &amp; loop modes built in"
        "</blockquote>"
    )

    why_us = (
        "<h2>WHY THIS BOT</h2>"
        "<p>Built for speed and uptime — no lag, no dropped calls, "
        "and your queue survives restarts. New features ship often, "
        "and support is one tap away if anything ever breaks.</p>"
    )

    footer = (
        "<p><i>Tip: use /help anytime to see the full command list. "
        f"{custom_emoji('🆘')} Stuck? Tap Support below.</i></p>"
    )

    # Real Bot API rich blocks: <details>/<summary> is the actual open/close
    # (collapsed-by-default, tap-to-expand) element, and it can wrap a real
    # <table> just fine — so "table" and "open/close" aren't a tradeoff.
    snapshot_rows = [
        (f"{custom_emoji('✅')} Status", "Online"),
        ("⏱ Uptime", escape(uptime)),
        ("👤 Plan", "Admin" if is_admin else "Free"),
    ]
    snapshot = (
        "<details>"
        "<summary><h2>BOT SNAPSHOT</h2></summary>"
        + rich_table(None, [(f"<b>{k}</b>", v) for k, v in snapshot_rows])
        + "</details>"
    )

    body = slideshow + heading + features + why_us + snapshot
    if not with_buttons:
        return body + footer

    # ---- rich buttons (real <tg-button> tags). Also passed as a normal
    # inline reply_markup below — Telegram renders BOTH: these sit inside
    # the rich body, the reply_markup row sits under the whole message.
    button_lines = []

    if url_buttons:
        add_url = safe_url(f"https://t.me/{app.username}?startgroup=true") if getattr(app, "username", None) else None
        support_url = safe_url(getattr(config, "SUPPORT_CHANNEL", None))
        print(f"[rich_start_html] add_url={add_url!r} support_url={support_url!r}")
        if add_url:
            button_lines.append(rich_button(escape(_["S_B_3"]), url=add_url, style="primary"))
        if support_url:
            button_lines.append(rich_button(escape(_["S_B_5"]), url=support_url, style="primary"))

    button_lines.append(
        rich_button(escape(_["S_B_4"]), callback_data="settings_back_helper", style="success")
    )
    if is_admin:
        button_lines.append(
            rich_button(f"{custom_emoji('⚙️')} Admin Panel", callback_data="admin_panel", style="danger")
        )

    buttons = "<p>" + "<br/>".join(button_lines) + "</p>"
    return body + buttons + footer


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


async def _send_rich_start(
    client, message: Message, _, uptime: str, is_admin: bool, with_buttons: bool, url_buttons: bool = True
):
    rich_html = rich_start_html(
        _,
        user_mention=rich_user_name(message.from_user),
        bot_mention=rich_bot_name(),
        uptime=uptime,
        is_admin=is_admin,
        with_buttons=with_buttons,
        url_buttons=url_buttons,
    )
    # effect_id dropped here: it triggered EFFECT_ID_INVALID on send_rich_message
    # even though the same IDs work fine on the reply_photo fallback below —
    # this rich-message endpoint doesn't seem to accept it the same way.
    await client.send_rich_message(
        chat_id=message.chat.id,
        rich_message=InputRichMessage(html=rich_html),
        reply_parameters=ReplyParameters(message_id=message.id),
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
                await _send_rich_start(client, message, _, uptime, is_admin, with_buttons=True, url_buttons=True)
                sent = True
            except ButtonUrlInvalid as ex:
                # A url-type button (Add to Group / Support) was rejected —
                # retry keeping only the callback-data buttons (Help/Admin).
                print(f"[start_pm] BUTTON_URL_INVALID, retrying without url buttons: {ex}")
                try:
                    await _send_rich_start(client, message, _, uptime, is_admin, with_buttons=True, url_buttons=False)
                    sent = True
                except ButtonUrlInvalid as ex2:
                    print(f"[start_pm] still invalid, retrying with no buttons at all: {ex2}")
                    try:
                        await _send_rich_start(client, message, _, uptime, is_admin, with_buttons=False)
                        sent = True
                    except Exception as ex3:
                        print(f"[start_pm] retry without buttons failed, falling back: {ex3}")
                        traceback.print_exc()
                except Exception as ex2:
                    print(f"[start_pm] retry without url buttons failed, falling back: {ex2}")
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
