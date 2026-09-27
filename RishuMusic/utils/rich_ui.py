# -----------------------------------------------
# 🔸 RishuMusic — utils/rich_ui.py
# 🔹 Bot API 10.2+ Rich Message helpers (Kurigram >= 2.2.25)
#
# See rich_patch.py in this same folder — that's what wires this into
# every send_message/edit_text/reply_text call across the whole bot
# without touching every plugin file by hand.
# -----------------------------------------------
"""utils/rich_ui.py — Bot API 10.2 Rich Message helpers.

Why this module exists
----------------------
Bot API 10.2 introduces server-side parsed *rich messages*: HTML supporting
``<h1>``-``<h6>``, ``<table>``, ``<details>``/``<summary>``, ``<mark>``,
``<sub>``/``<sup>`` on top of the classic inline tags. That HTML is only
understood when it travels inside ``InputRichMessage(html=...)`` — the
client-side parser used for ordinary ``text=``/``caption=`` arguments silently
drops those tags. So every rich block must go through the helpers below.

Hard rules encoded here (confirmed against a live bot,
github.com/Badmunda05/ShizuMusic, and from the API surface):
  * ``<tg-button>`` MUST carry a `type="url"` or `type="callback_data"`
    attribute alongside the matching `url=`/`callback_data=` attribute.
    Without `type=`, Telegram silently drops the tag and draws nothing —
    no error, just an invisible button. This was the actual bug behind
    "rich buttons never show up" — not the tag itself, not `<p>` wrapping.
  * ``Message.edit_text()`` does **not** accept ``rich_message``. Use
    ``Client.edit_message_text(chat_id=..., message_id=..., rich_message=...)``
    or ``CallbackQuery.edit_message_text(rich_message=...)``.
  * Captions can never be rich (``edit_message_caption`` / ``send_photo`` have
    no ``rich_message`` parameter).
  * ``send_rich_message_draft()`` is a ~30 s ephemeral preview. It **must** be
    followed by a real ``send_rich_message()`` or the output is lost.
  * Ephemeral delivery (``receiver_user_id=``) only works in groups /
    supergroups; in private chats we transparently fall back to a normal send.
  * ``InputRichMessage`` with neither ``html`` nor ``markdown`` raises.
  * ``effect_id=`` on ``send_rich_message`` is unreliable — some valid
    classic message-effect IDs raise ``EFFECT_ID_INVALID`` here even though
    they work fine on ``send_message``/``send_photo``. None of the senders
    below pass it; add it yourself only after testing your exact IDs.

Every sender degrades gracefully: if the server rejects the rich HTML (or the
running Kurigram build predates 10.2) the helper falls back to the plain-text
path so no handler can regress — this is what makes it safe to auto-patch
every text call site instead of editing each plugin by hand.
"""

from __future__ import annotations

import html as _html
import logging
import re

from pyrogram.enums import ParseMode
from pyrogram.types import InputRichMessage, ReplyParameters

logger = logging.getLogger("pyrogram")

__all__ = [
    "RICH_AVAILABLE",
    "rich_esc",
    "sanitize_display_name",
    "rich_heading",
    "rich_note",
    "rich_table",
    "rich_button",
    "rich_details",
    "rich_kv_table",
    "rich_code",
    "rich_img",
    "rich_to_plain",
    "rich_caption",
    "rich_send",
    "rich_reply",
    "rich_edit",
    "rich_answer",
]

# ── capability probe ─────────────────────────────────────────────────────────
try:  # pragma: no cover - depends on installed Kurigram build
    from pyrogram import Client as _Client

    RICH_AVAILABLE = hasattr(_Client, "send_rich_message")
except Exception:  # pragma: no cover
    RICH_AVAILABLE = False


# ── block-level tags that only exist inside InputRichMessage ─────────────────
_RICH_ONLY_TAGS = (
    "h1", "h2", "h3", "h4", "h5", "h6",
    "table", "thead", "tbody", "tr", "th", "td",
    "details", "summary", "mark", "sub", "sup",
    "tg-button", "button", "img",
)
_BLOCK_BREAK_RE = re.compile(
    r"</(?:h[1-6]|tr|details|summary|blockquote|table|pre)>", re.I
)
_CELL_BREAK_RE = re.compile(r"</(?:th|td)>", re.I)
_ANY_TAG_RE = re.compile(r"<[^>]+>")
_RICH_TAGS_RE = re.compile(
    r"</?(?:h[1-6]|table|thead|tbody|tr|th|td|details|summary|mark|sub|sup|tg-button|button|img)\b", re.I
)


def _has_rich_only_tags(html_text: str) -> bool:
    """Check if html_text contains Bot API 10.2+ rich tags that specifically require InputRichMessage."""
    if not html_text:
        return False
    return bool(_RICH_TAGS_RE.search(str(html_text)))


# ── builders ────────────────────────────────────────────────────────────────

def rich_esc(value) -> str:
    """HTML-escape untrusted text (titles, usernames, exception strings).

    Always run user/remote-supplied strings through this before interpolating
    them into rich HTML, otherwise a stray ``<`` breaks the whole block.
    """
    if value is None:
        return ""
    return _html.escape(str(value), quote=False)


def sanitize_display_name(name) -> str:
    """
    Best-effort cleanup of a Telegram first_name/last_name for display inside
    rich HTML: strips characters that have broken HTML parsing in practice
    (e.g. a name containing a bare '</3'), then escapes the rest.
    """
    if not name:
        return "User"
    text = str(name)
    text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)  # drop anything tag-shaped
    text = text.strip() or "User"
    return rich_esc(text)


def rich_heading(text: str, level: int = 1) -> str:
    """``<h1>``-``<h6>`` page/section title. Text is passed through verbatim so
    callers may embed ``<b>``/``<tg-emoji>`` inside it."""
    level = max(1, min(6, int(level)))
    return f"<h{level}>{text}</h{level}>"


def rich_note(text: str, expandable: bool = False) -> str:
    """``<blockquote>`` note / tip / caveat."""
    attr = " expandable" if expandable else ""
    return f"<blockquote{attr}>{text}</blockquote>"


def rich_code(value) -> str:
    """``<code>`` wrapped, escaped — for commands, IDs and other literals."""
    return f"<code>{rich_esc(value)}</code>"


def rich_img(url: str, *, width: int = None, height: int = None) -> str:
    """Embed an image directly inside a rich message's body via a plain
    ``<img>`` tag pointing at an already-public HTTP(S) URL.

    Telegram's rich-message renderer fetches the URL itself server-side — no
    local upload or a ``media=``/``InputRichMessageMedia`` field is needed for
    this case. This only works with a stable public URL; it can NOT embed a
    local file path or a bare Telegram ``file_id`` — use :func:`rich_send`'s
    plain-fallback / a normal ``send_photo`` call for those instead.
    """
    if not url:
        return ""
    attrs = f' src="{rich_esc(url)}"'
    if width:
        attrs += f' width="{int(width)}"'
    if height:
        attrs += f' height="{int(height)}"'
    return f"<img{attrs}/>"


def rich_button(text: str, url: str = None, callback_data: str = None, style: str = None) -> str:
    """Native Rich Message inline button (``<tg-button>``) for Bot API 10.3+.

    CONFIRMED syntax for URL buttons (verified against a live bot,
    github.com/Badmunda05/ShizuMusic) — ``type="url"`` is REQUIRED, an
    earlier version of this helper omitted it and Telegram silently dropped
    the whole tag (no error, just nothing drawn):

        <tg-button type="url" style="primary" url="...">text</tg-button>

    ⚠️ ``callback_data=`` is UNCONFIRMED and, as tested, actually fails:
    ``type="callback_data"`` raises BUTTON_DATA_INVALID on send. The
    reference bot above never uses a callback-type tg-button either — its
    Help/Admin/etc. buttons are only ever in the normal ``reply_markup``
    (a plain ``InlineKeyboardButton(callback_data=...)``), never embedded in
    the rich body. Passing ``callback_data`` here is kept for forward
    compatibility (in case a future Bot API version supports it) but you
    should NOT rely on it today — put callback buttons in reply_markup
    instead, exactly like the reference bot does.

    Embeddable inside tables (``<td>``), paragraphs, lists, and blockquotes.
    """
    style_attr = f' style="{rich_esc(style)}"' if style else ""
    if callback_data:
        return (
            f'<tg-button type="callback_data"{style_attr} '
            f'callback_data="{rich_esc(callback_data)}">{text}</tg-button>'
        )
    if url:
        return (
            f'<tg-button type="url"{style_attr} '
            f'url="{rich_esc(url)}">{text}</tg-button>'
        )
    return f'<tg-button{style_attr}>{text}</tg-button>'


def rich_table(headers, rows, border: int = 1) -> str:
    """Native Rich Block table.

    ``headers`` may be ``None``/empty for a header-less grid. Cells are
    emitted verbatim (so bold/code/emoji tags work) — escape untrusted values
    yourself with :func:`rich_esc`. ``None`` cells render as an empty string.
    """
    parts = [f'<table border="{int(border)}">']
    if headers:
        cells = "".join(f"<th>{'' if h is None else h}</th>" for h in headers)
        parts.append(f"<tr>{cells}</tr>")
    for row in rows or ():
        cells = "".join(f"<td>{'' if c is None else c}</td>" for c in row)
        parts.append(f"<tr>{cells}</tr>")
    parts.append("</table>")
    return "".join(parts)


def rich_kv_table(pairs, headers=None, border: int = 1) -> str:
    """Two-column key/value table from an iterable of ``(key, value)`` pairs.

    Keys are bolded, values are emitted verbatim. Entries whose value is
    ``None`` are skipped so callers can build optional rows inline.
    """
    rows = [
        (f"<b>{k}</b>", v)
        for k, v in (pairs or ())
        if v is not None
    ]
    return rich_table(headers, rows, border=border)


def rich_details(summary: str, body: str, open: bool = False) -> str:
    """Collapsible section — keeps long help/FAQ/debug output out of the way."""
    attr = " open" if open else ""
    return f"<details{attr}><summary>{summary}</summary>{body}</details>"


def rich_to_plain(html_text: str) -> str:
    """Best-effort rich HTML -> readable plain text (e.g. for logs)."""
    if not html_text:
        return ""
    text = str(html_text)
    text = _CELL_BREAK_RE.sub("\x1f", text)
    text = _BLOCK_BREAK_RE.sub("\n", text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = _ANY_TAG_RE.sub("", text)
    text = _html.unescape(text)
    text = re.sub(r"\x1f+(?=\s*(?:\n|$))", "", text)
    text = text.replace("\x1f", " \u2022 ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def rich_caption(html_text: str) -> str:
    """Downgrade rich HTML for a **caption**.

    Photo/video captions have no ``rich_message`` parameter, so block tags
    would be silently stripped by Telegram's client-side parser. This keeps
    the tags captions *do* support (``b/i/u/s/code/pre/blockquote/emoji/a``)
    and flattens the rest.
    """
    return _plain_fallback(html_text)


_VERBATIM_BLOCK_RE = re.compile(
    r'(<(?:table|pre)\b[\s\S]*?</(?:table|pre)>)', re.I
)
_BR_CONVERT_RE = re.compile(
    r'(?<!<br/>)(?<!<br>)(?<!</p>)(?<!</h2>)(?<!</h1>)(?<!</h3>)(?<!</h4>)(?<!</h5>)(?<!</h6>)(?<!</blockquote>)(?<!</summary>)(?<!</details>)(?<!</table>)(?<!</pre>)(?<!</li>)(?<!</ul>)(?<!</ol>)(?<!<hr/>)(?<!<hr>)\n',
    re.I,
)


def _normalize_html(html_text: str) -> str:
    """Normalize HTML for Telegram's Rich Message API.

    Fixes unquoted attributes like ``href=tg://user?id=123`` (which some
    ``User.mention()`` helpers generate) into a quoted form Telegram's parser
    accepts, and preserves line breaks so text inside a Rich Message doesn't
    collapse into a single line (Rich Messages don't auto-linebreak on ``\\n``
    the way plain HTML sends do).
    """
    if not html_text:
        return ""
    text = str(html_text).replace("\r\n", "\n")
    text = re.sub(r'href=([^\s">]+)', r'href="\1"', text)

    parts = _VERBATIM_BLOCK_RE.split(text)
    for i in range(0, len(parts), 2):
        if not parts[i]:
            continue
        if i > 0 and parts[i].startswith("\n"):
            leading_nl = ""
            content = parts[i]
            while content.startswith("\n"):
                leading_nl += "\n"
                content = content[1:]
            parts[i] = leading_nl + _BR_CONVERT_RE.sub("<br/>\n", content)
        else:
            parts[i] = _BR_CONVERT_RE.sub("<br/>\n", parts[i])
    return "".join(parts)


def _plain_fallback(html_text: str) -> str:
    """Plain text for a failed rich send, keeping the inline tags Telegram's
    normal HTML parser *does* understand (b/i/u/s/code/pre/blockquote/emoji)."""
    if not html_text:
        return ""
    text = _normalize_html(html_text)
    text = re.sub(r"<h[1-6]>(.*?)</h[1-6]>", r"\n<b>\1</b>\n", text, flags=re.I | re.S)
    text = re.sub(r"<summary>(.*?)</summary>", r"<b>\1</b>\n", text, flags=re.I | re.S)
    text = re.sub(r"<mark>(.*?)</mark>", r"<b>\1</b>", text, flags=re.I | re.S)
    text = re.sub(r'<tg-button[^>]*\burl="([^"]*)"[^>]*>(.*?)</tg-button>', r'<a href="\1">\2</a>', text, flags=re.I | re.S)
    text = re.sub(r'<tg-button[^>]*\bcallback_data="[^"]*"[^>]*>(.*?)</tg-button>', r'<b>\1</b>', text, flags=re.I | re.S)
    text = re.sub(r'<tg-button[^>]*>(.*?)</tg-button>', r'<b>\1</b>', text, flags=re.I | re.S)
    text = re.sub(r"<button[^>]*>(.*?)</button>", r"<b>\1</b>", text, flags=re.I | re.S)
    text = _CELL_BREAK_RE.sub("  ", text)
    text = re.sub(r"</tr>", "\n", text, flags=re.I)
    text = re.sub(r"</table>", "\n", text, flags=re.I)
    text = re.sub(
        r"</?(?:%s)(?:\s[^>]*)?>" % "|".join(_RICH_ONLY_TAGS),
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"<br\s*/?>\n?", "\n", text, flags=re.I)
    text = re.sub(r"[ \t]{2,}", "  ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_IMG_RE = re.compile(r'<img\s+src="([^"]*)"[^>]*/?>', re.I)


def _extract_img(html_text: str):
    """Pull a rich_img()-embedded ``<img src="...">`` out of html_text.

    Returns ``(url_or_None, remaining_html)``. Used by the plain-message
    fallback path so a photo embedded via :func:`rich_img` still shows up as
    a real Telegram photo (via ``send_photo``) instead of silently vanishing
    when rich messages aren't available/fail — captions can't carry the tag
    itself, but the photo can still go out as an actual photo message.
    """
    if not html_text:
        return None, html_text
    m = _IMG_RE.search(html_text)
    if not m:
        return None, html_text
    url = _html.unescape(m.group(1))
    remaining = html_text[:m.start()] + html_text[m.end():]
    return url, remaining


def _input_rich(html_text: str) -> InputRichMessage:
    return InputRichMessage(html=_normalize_html(html_text))


def _is_group(chat_type) -> bool:
    value = getattr(chat_type, "value", chat_type)
    return value in ("group", "supergroup")


# ── senders ─────────────────────────────────────────────────────────────────
# These are used directly by rich_patch.py, and can also be called by hand
# from any plugin that wants ephemeral / explicit-chat_id control.

async def rich_send(
    client,
    chat_id,
    html_text: str,
    *,
    reply_markup=None,
    receiver_user_id=None,
    callback_query_id=None,
    reply_to_message_id=None,
    reply_parameters=None,
    message_thread_id=None,
    disable_notification=None,
    protect_content=None,
):
    """Send a rich message, falling back to plain ``send_message`` on any failure.

    ``receiver_user_id`` makes the message *ephemeral* (visible only to that
    user, groups/supergroups only).
    """
    if not html_text:
        return None

    if reply_parameters is None and reply_to_message_id:
        reply_parameters = ReplyParameters(message_id=reply_to_message_id)

    if RICH_AVAILABLE and (receiver_user_id or _has_rich_only_tags(html_text)):
        try:
            return await client.send_rich_message(
                chat_id=chat_id,
                rich_message=_input_rich(html_text),
                reply_markup=reply_markup,
                receiver_user_id=receiver_user_id,
                callback_query_id=callback_query_id,
                reply_parameters=reply_parameters,
                message_thread_id=message_thread_id,
                disable_notification=disable_notification,
                protect_content=protect_content,
            )
        except Exception as e:
            logger.debug(f"[rich_send] rich delivery failed, falling back: {e}")

    try:
        img_url, rest = _extract_img(html_text)
        if img_url:
            try:
                return await client.send_photo(
                    chat_id=chat_id,
                    photo=img_url,
                    caption=_plain_fallback(rest),
                    reply_markup=reply_markup,
                    reply_parameters=reply_parameters,
                    message_thread_id=message_thread_id,
                    disable_notification=disable_notification,
                    protect_content=protect_content,
                )
            except Exception as e:
                logger.debug(f"[rich_send] photo fallback failed, trying text-only: {e}")
        return await client.send_message(
            chat_id=chat_id,
            text=_plain_fallback(html_text),
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            reply_parameters=reply_parameters,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except Exception as e:
        logger.debug(f"[rich_send] plain send failed: {e}")
        return None


async def rich_reply(
    message,
    html_text: str,
    *,
    reply_markup=None,
    ephemeral: bool = False,
    quote: bool = True,
    client=None,
):
    """Reply to an incoming ``Message`` with rich formatting.

    ``ephemeral=True`` makes the reply visible only to the sender (groups /
    supergroups only, ignored in PM).
    """
    if not html_text:
        return None

    chat = getattr(message, "chat", None)
    if not chat:
        return None
    app = client or getattr(message, "_client", None)
    from_user = getattr(message, "from_user", None)
    receiver_user_id = from_user.id if (ephemeral and from_user and _is_group(chat.type)) else None

    reply_parameters = None
    if quote and not receiver_user_id and getattr(message, "id", 0):
        reply_parameters = ReplyParameters(message_id=message.id)

    return await rich_send(
        app,
        chat.id,
        html_text,
        reply_markup=reply_markup,
        receiver_user_id=receiver_user_id,
        reply_parameters=reply_parameters,
        message_thread_id=getattr(message, "message_thread_id", None),
    )


async def _rich_edit_via_client(app, chat_id, message_id, html_text, reply_markup):
    """Edit a message into rich HTML using Kurigram's NATIVE ``rich_message=``
    parameter on ``Client.edit_message_text`` (added alongside ``send_rich_message``
    in kurigram >= 2.2.25).

    IMPORTANT: when ``rich_message`` is supplied, ``text``/``entities`` must be
    left unset — the raw ``EditMessage`` RPC rejects/ignores a message that
    carries both plain content and a rich_message in the same call. Kurigram's
    own ``edit_message_text`` already enforces this correctly, so we call it
    directly instead of re-invoking the raw API ourselves.
    """
    if chat_id is None or not message_id:
        logger.debug("[rich_edit] missing chat_id/message_id")
        return None

    if RICH_AVAILABLE and _has_rich_only_tags(html_text):
        try:
            return await app.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                rich_message=_input_rich(html_text),
                reply_markup=reply_markup,
            )
        except Exception as e:
            logger.debug(f"[rich_edit] native rich edit failed, falling back: {e}")

    try:
        return await app.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=_plain_fallback(html_text),
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.debug(f"[rich_edit] plain edit failed: {e}")
        return None


async def rich_edit(
    target,
    html_text: str,
    *,
    reply_markup=None,
    chat_id=None,
    message_id=None,
    client=None,
):
    """Edit an existing message into rich HTML.

    ``target`` may be a :class:`CallbackQuery`, a :class:`Message`, or a
    :class:`Client` together with explicit ``chat_id``/``message_id``.
    """
    if not html_text:
        return None

    # CallbackQuery
    if hasattr(target, "data") and hasattr(target, "message"):
        app = client or getattr(target, "_client", None)
        msg = getattr(target, "message", None)
        if msg and hasattr(msg, "chat") and hasattr(msg, "id"):
            chat_id = msg.chat.id
            message_id = msg.id
        if app is not None and chat_id and message_id:
            return await _rich_edit_via_client(app, chat_id, message_id, html_text, reply_markup)
        try:
            return await target.edit_message_text(
                _plain_fallback(html_text), parse_mode=ParseMode.HTML, reply_markup=reply_markup
            )
        except Exception as e:
            logger.debug(f"[rich_edit] cq plain edit failed: {e}")
            return None

    # Message instance.
    if hasattr(target, "chat") and hasattr(target, "id"):
        app = client or getattr(target, "_client", None)
        chat_id = target.chat.id
        message_id = target.id
        if app is not None:
            return await _rich_edit_via_client(app, chat_id, message_id, html_text, reply_markup)
        try:
            return await target.edit_text(
                _plain_fallback(html_text), parse_mode=ParseMode.HTML, reply_markup=reply_markup
            )
        except Exception as e:
            logger.debug(f"[rich_edit] message plain edit failed: {e}")
            return None

    # Bare Client + ids.
    return await _rich_edit_via_client(target, chat_id, message_id, html_text, reply_markup)


async def rich_answer(
    callback_query,
    html_text: str,
    *,
    reply_markup=None,
    client=None,
):
    """Ephemeral rich response to a button press.

    Only the pressing user sees it (groups/supergroups); in private chats it
    falls back to a normal message.
    """
    if not html_text:
        return None

    app = client or getattr(callback_query, "_client", None)
    message = getattr(callback_query, "message", None)
    chat = getattr(message, "chat", None)
    user = getattr(callback_query, "from_user", None)
    if app is None or chat is None:
        return None

    receiver_user_id = user.id if (user and _is_group(getattr(chat, "type", None))) else None
    return await rich_send(
        app,
        chat.id,
        html_text,
        reply_markup=reply_markup,
        receiver_user_id=receiver_user_id,
        callback_query_id=getattr(callback_query, "id", None) if receiver_user_id else None,
        message_thread_id=getattr(message, "message_thread_id", None),
    )
