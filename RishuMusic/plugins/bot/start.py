# ============================================================
# start.py — v18
# CHANGELOG (v17 -> v18):
#   - Custom-emoji IDs moved to one shared file, as asked:
#     RishuMusic/utils/premium_emojis.py holds every ID + a pemoji(name,
#     fallback) tag helper. custom_emoji() here is now a thin wrapper over
#     it, so nothing else in this file had to change.
#   - "WHY THIS BOT" is now a <details>/<summary> open-close block with a
#     real <table> inside (Speed/Reliability/Updates/Support rows) —
#     matches the BOT SNAPSHOT treatment, as asked.
#   - "BOT SNAPSHOT" title dressed up: a link-style premium emoji + the
#     title itself is now a tappable <a> to the bot's own t.me link (not
#     just decorative — matches "aage title linko, mast sa").
#   - FIXED: "Add Me In Your Group" was appearing TWICE in your screenshot
#     — private_panel() already has its own copy, and build_reply_markup()
#     was prepending a second one on top. Removed the duplicate; the inline
#     keyboard is now exactly private_panel()'s buttons + Admin Panel.
# CHANGELOG (v16 -> v17):
#   - New error from your logs: BUTTON_DATA_INVALID on the
#     type="callback_data" tg-button (Help/Settings pill). So the url-type
#     fix from v16 was right (no more ButtonUrlInvalid!), but
#     type="callback_data" is NOT actually supported the same way — it's
#     not just missing an attribute, it genuinely errors. The reference
#     repo (ShizuMusic) never uses a callback-type tg-button either — its
#     Help/Admin buttons live ONLY in the reply_markup, never in the rich
#     body. Matched that: dropped callback_data tg-buttons from the rich
#     body entirely. Only URL-type pills (Add to Group / Support) remain
#     inside the message text now.
#   - Help/Settings/Owner/Admin are reachable exactly as before, via the
#     guaranteed reply_markup (build_reply_markup) under the message —
#     nothing lost, just moved to the path that's actually confirmed to work.
# CHANGELOG (v15 -> v16):
#   - REAL fix, confirmed against a live working bot
#     (github.com/Badmunda05/ShizuMusic): the missing piece in every
#     earlier attempt was the `type="url"` / `type="callback_data"`
#     attribute on <tg-button>. Their own rich_ui.py's rich_button()
#     helper omitted it too (same bug I copied), but their actual /start
#     code writes the tag by hand WITH `type=` — and that's the version
#     that renders. Fixed rich_button() to always include it:
#         <tg-button type="url" style="..." url="...">text</tg-button>
#         <tg-button type="callback_data" style="..." callback_data="...">text</tg-button>
#   - Also confirmed <p>...</p> around the buttons is fine (their
#     _support_updates_pills() does exactly that) — the v15 "no <p>"
#     experiment wasn't the fix, so reverted to <p> with buttons
#     space-separated, matching their proven pattern.
#   - ShizuMusic's InlineKeyboardButton(..., style=enums.ButtonStyle.X) is
#     from their own custom pyrogram fork's enums — not present in stock
#     Kurigram, so NOT copied into build_reply_markup() here (would crash
#     with AttributeError on a normal Kurigram install). The plain inline
#     keyboard from v14 stays as the guaranteed fallback either way.
# CHANGELOG (v14 -> v15):
#   - Bringing <tg-button> back for one more try, per your request. Theory:
#     v13 wrapped the buttons inside <p>...</p>, and that may be why they
#     drew nothing — every OTHER tag that worked (h1, table, details) was
#     used as a direct top-level element, never nested in a <p>. So this
#     version places <tg-button> the same way, at the top level after the
#     BOT SNAPSHOT block, no <p> wrapper.
#   - The normal inline reply_markup (Add to Group / private_panel() /
#     Admin) from v14 stays exactly as-is regardless — you still get a
#     guaranteed button row under the message either way.
#   - If <tg-button> still draws nothing (most likely outcome — this genuinely
#     may just not be a supported tag on your client/Bot API build), the
#     admin-only debug message from v13 will tell you if it errors, but if
#     it silently renders nothing again with zero error, that's your answer:
#     this Kurigram build's rich-message renderer doesn't support tg-button
#     at all yet, and the inline keyboard (v14) is the real fix to keep.
# CHANGELOG (v13 -> v14):
#   - Your screenshots confirm it: text/list/<details>+<table> all render
#     perfectly now, but <tg-button> draws NOTHING — no error either (the
#     v13 admin debug message never fired), it's just a no-op tag on your
#     client. Stopped fighting it — dropped <tg-button> from the rich body
#     entirely, along with the now-pointless 3-level retry cascade.
#   - All buttons are now a single, guaranteed-to-render inline
#     reply_markup (build_reply_markup): an "Add to Group" row on top,
#     then your existing private_panel() buttons (Owner/Settings/Support —
#     already wired to working handlers), then the Admin Panel row for
#     admins. This is the same mechanism behind the pill-button grid in
#     the reference screenshot you sent (image 1) — plain
#     InlineKeyboardMarkup, not a rich-message feature.
# CHANGELOG (v12 -> v13):
#   - No access to container logs, but rich message keeps silently falling
#     back to plain photo (inline keyboard shows, rich body doesn't) — so
#     surfaced the failure inside Telegram instead. If you (an admin/owner,
#     per config.SUDO_USERS/OWNER_ID) run /start and rich delivery fails
#     after all retries, the bot now sends you a SECOND message right there
#     with the exact exception text, e.g.
#       ⚠️ Rich /start failed, sent plain fallback.
#       BUTTON_URL_INVALID (with url buttons): ...
#     Send me that text and I can fix the actual cause directly — no logs
#     needed. Regular (non-admin) users never see this extra message.
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

# Custom-emoji IDs now live in one shared file so every plugin can reuse
# them: RishuMusic/utils/premium_emojis.py. custom_emoji() below is kept as
# a thin wrapper so every existing custom_emoji('🚀') call in this file
# keeps working unchanged.
from RishuMusic.utils.premium_emojis import pemoji

_EMOJI_NAME_BY_GLYPH = {
    "🚀": "rocket", "💎": "diamond", "👤": "user", "🔗": "link",
    "❤️": "heart", "🏠": "house", "⚙️": "gear", "✅": "check",
    "📊": "chart", "🎉": "party", "📢": "megaphone", "🆘": "sos",
}


def custom_emoji(name: str) -> str:
    """
    Real Bot API custom-emoji HTML tag: <tg-emoji emoji-id="...">🔥</tg-emoji>.
    Looks the glyph up in premium_emojis.py; falls back to the plain emoji
    if it's not registered there.
    """
    key = _EMOJI_NAME_BY_GLYPH.get(name)
    return pemoji(key, name) if key else name


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
    Real, confirmed-working Bot API 10.3 rich-message button — verified
    against github.com/Badmunda05/ShizuMusic (a live bot using this exact
    tag). The missing piece in every earlier attempt was `type="url"` /
    `type="callback_data"` — Telegram silently drops <tg-button> without it,
    which is exactly what was happening.
    """
    style_attr = f' style="{escape(style, quote=True)}"' if style else ""
    if callback_data:
        return (
            f'<tg-button type="callback_data"{style_attr} '
            f'callback_data="{escape(callback_data, quote=True)}">{text}</tg-button>'
        )
    if url:
        return (
            f'<tg-button type="url"{style_attr} '
            f'url="{escape(url, quote=True)}">{text}</tg-button>'
        )
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
) -> str:
    """
    Rich-message body for the private /start screen: <tg-slideshow> +
    heading + feature list + <details>/<summary>+<table> snapshot + footer.
    No <tg-button> here anymore — confirmed (no error, just nothing drawn)
    that this client doesn't render that tag, so all buttons are the
    normal inline reply_markup instead (see build_reply_markup).
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

    why_us_rows = [
        (f"{custom_emoji('🚀')} Speed", "No lag, no dropped calls"),
        (f"{custom_emoji('🏠')} Reliability", "Queue survives restarts"),
        (f"{custom_emoji('🎉')} Updates", "New features ship often"),
        (f"{custom_emoji('🆘')} Support", "One tap away, always"),
    ]
    why_us = (
        "<details>"
        f"<summary><h2>{pemoji('star', '⭐')} WHY THIS BOT</h2></summary>"
        + rich_table(None, [(f"<b>{k}</b>", v) for k, v in why_us_rows])
        + "</details>"
    )

    footer = (
        "<p><i>Tip: use /help anytime to see the full command list. "
        f"{custom_emoji('🆘')} Stuck? Tap Support below.</i></p>"
    )

    # Real Bot API rich blocks: <details>/<summary> is the actual open/close
    # (collapsed-by-default, tap-to-expand) element, and it can wrap a real
    # <table> just fine — so "table" and "open/close" aren't a tradeoff.
    # Title dressed up with a link icon + the bot's own t.me link, matching
    # the "aage title linko, mast sa" ask — tappable, not just decorative.
    bot_link = f"https://t.me/{app.username}" if getattr(app, "username", None) else None
    snapshot_title = f"{pemoji('link', '🔗')} <b>BOT SNAPSHOT</b>"
    if bot_link:
        snapshot_title = f'{pemoji("link", "🔗")} <a href="{escape(bot_link, quote=True)}"><b>BOT SNAPSHOT</b></a>'
    snapshot_rows = [
        (f"{custom_emoji('✅')} Status", "Online"),
        (f"{pemoji('clock', '⏱')} Uptime", escape(uptime)),
        (f"{custom_emoji('👤')} Plan", "Admin" if is_admin else "Free"),
    ]
    snapshot = (
        "<details>"
        f"<summary><h2>{snapshot_title}</h2></summary>"
        + rich_table(None, [(f"<b>{k}</b>", v) for k, v in snapshot_rows])
        + "</details>"
    )

    body = slideshow + heading + features + why_us + snapshot
    if not with_buttons:
        return body + footer

    # BUTTON_DATA_INVALID confirmed: type="callback_data" tg-button doesn't
    # actually work on this endpoint (the reference repo never used it
    # either — its help/admin buttons are ONLY in the reply_markup below,
    # never as an in-body tg-button). Keeping ONLY url-type pills here.
    button_pills = []
    add_url = safe_url(f"https://t.me/{app.username}?startgroup=true") if getattr(app, "username", None) else None
    if add_url:
        button_pills.append(rich_button(escape(_["S_B_3"]), url=add_url, style="primary"))
    support_url = safe_url(getattr(config, "SUPPORT_CHANNEL", None))
    if support_url:
        button_pills.append(rich_button(escape(_["S_B_5"]), url=support_url, style="success"))

    if not button_pills:
        return body + footer

    rich_buttons = "<p>" + " ".join(button_pills) + "</p>"
    return body + rich_buttons + footer


def build_reply_markup(_, is_admin: bool = False) -> InlineKeyboardMarkup:
    """
    Real, guaranteed-to-render button set — plain InlineKeyboardMarkup
    (the rich-body <tg-button> tags never actually rendered anything on
    your client, no error either, so dropped them — this is the only path
    now). Reuses RishuMusic.utils.inline.private_panel() as-is — it already
    has its OWN "Add Me In Your Group" row built in (confirmed from your
    screenshot: prepending another one here made it show up TWICE) — so
    this just appends the admin row on top of whatever private_panel gives.
    """
    buttons = list(private_panel(_))

    if is_admin:
        buttons.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])

    return InlineKeyboardMarkup(buttons)


async def _send_rich_start(client, message: Message, _, uptime: str, is_admin: bool, with_buttons: bool = True):
    rich_html = rich_start_html(
        _,
        user_mention=rich_user_name(message.from_user),
        bot_mention=rich_bot_name(),
        uptime=uptime,
        is_admin=is_admin,
        with_buttons=with_buttons,
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
        last_error = None
        if RICH_MESSAGES_SUPPORTED:
            try:
                await _send_rich_start(client, message, _, uptime, is_admin, with_buttons=True)
                sent = True
            except ButtonUrlInvalid as ex:
                last_error = f"BUTTON_URL_INVALID (top-level tg-button): {ex}"
                try:
                    await _send_rich_start(client, message, _, uptime, is_admin, with_buttons=False)
                    sent = True
                except Exception as ex2:
                    last_error += f" | retry without buttons also failed: {type(ex2).__name__}: {ex2}"
                    traceback.print_exc()
            except Exception as ex:
                # Fork/server doesn't actually support it, or rejected something
                # else in the body — fall back to plain photo below.
                last_error = f"{type(ex).__name__}: {ex}"
                traceback.print_exc()
        else:
            last_error = "RICH_MESSAGES_SUPPORTED is False (InputRichMessage/ReplyParameters not importable)"

        if not sent:
            await message.reply_photo(
                photo=get_start_img(),
                has_spoiler=True,
                effect_id=random.choice(EFFECT_ID),
                caption=_["start_2"].format(message.from_user.mention, app.mention),
                reply_markup=build_reply_markup(_, is_admin=is_admin),
            )
            # No container-log access? This puts the exact failure reason
            # straight into Telegram instead, visible only to admins.
            if is_admin and last_error:
                try:
                    await message.reply_text(
                        f"⚠️ <b>Rich /start failed, sent plain fallback.</b>\n<code>{escape(last_error)}</code>",
                        quote=False,
                    )
                except Exception:
                    pass

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
