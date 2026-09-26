# -----------------------------------------------
# 🔸 RishuMusic — utils/premium_emojis.py
# 🔹 JSON-backed custom/premium emoji registry + auto-render patches.
#
# Data file: RishuMusic/utils/data/custom_emoji_ids.json
# (this path is relative to THIS file's own folder — utils/data/, not a
# top-level RishuMusic/data/ folder)
# -----------------------------------------------
"""utils/premium_emojis.py — custom emoji registry backed by
utils/data/custom_emoji_ids.json.

Constants below (SUCCESS, ERROR, ROCKET, ...) are plain Unicode strings —
safe to use anywhere, including InlineKeyboardButton labels.

For real Telegram custom-emoji rendering in message TEXT (not buttons —
Telegram does not support custom-emoji tags in button labels), call
render() explicitly, or apply the patches at the bottom so every
send_message/edit_message_text call renders registered emoji automatically
without touching every plugin file:

    await bot.send_message(user_id, render('✅') + " Done!", parse_mode="html")

Tag used: <tg-emoji emoji-id="..."> — the standard, CONFIRMED-working Bot
API HTML custom-emoji tag (verified in this project's rich-message system,
utils/rich_ui.py). An earlier draft of this module used <emoji id="...">
instead; that tag is unconfirmed on this bot and was switched out so both
this module and rich_ui.py render custom emoji the exact same, tested way.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

_DATA_PATH = Path(__file__).resolve().parent / 'data' / 'custom_emoji_ids.json'


@lru_cache(maxsize=1)
def _load_registry() -> Dict[str, List[int]]:
    registry: Dict[str, List[int]] = {}
    if not _DATA_PATH.exists():
        return registry
    try:
        payload = json.loads(_DATA_PATH.read_text(encoding='utf-8'))
    except Exception:
        return registry
    for pack in payload:
        for item in pack.get('items', []):
            emoji = item.get('emoji')
            document_id = item.get('document_id')
            if not emoji or document_id is None:
                continue
            registry.setdefault(emoji, []).append(int(document_id))
    return registry


def document_ids_for(emoji: str) -> List[int]:
    return list(_load_registry().get(emoji, []))


def pick_document_id(emoji: str, index: int = 0) -> Optional[int]:
    ids = document_ids_for(emoji)
    if not ids:
        return None
    return ids[index % len(ids)]


def render(emoji: str, fallback: Optional[str] = None, index: int = 0) -> str:
    """Render a Telegram custom-emoji tag for use in HTML message TEXT only.

    WARNING: Do NOT use the output in InlineKeyboardButton labels —
    Telegram does not support custom-emoji tags in buttons. For a button
    icon, see icon_custom_emoji_id (the patch at the bottom of this file
    handles that automatically from a leading emoji in the button text).

    Args:
        emoji: The visible emoji and lookup key.
        fallback: Plain-text shown if no document ID is found. Defaults to
            ``emoji`` itself, so a missing/unregistered emoji degrades to
            the normal Unicode emoji instead of breaking the message.
        index: Which document ID to use when multiple exist for one emoji.
    """
    document_id = pick_document_id(emoji, index=index)
    visible = fallback if fallback is not None else emoji
    if document_id is None:
        return visible
    return f'<tg-emoji emoji-id="{document_id}">{visible}</tg-emoji>'


# Backward-compatible alias for code written against the earlier
# name-based premium_emojis.py (pemoji('rocket', '🚀')) — 'name' here is
# just treated as the fallback/lookup emoji itself, since this registry is
# keyed by the actual emoji glyph, not a friendly name.
def pemoji(name: str, fallback: str = "") -> str:
    glyph = fallback or name
    return render(glyph, glyph) if glyph else ""


# ─────────────────────────────────────────────────────────────────────────────
# All constants below are PLAIN UNICODE — safe for buttons AND text
# ─────────────────────────────────────────────────────────────────────────────

# STATUS & RESULTS
SUCCESS      = '✅'
ERROR        = '❌'
WARNING      = '⚠️'
INFO         = 'ℹ️'
LOADING      = '⏳'
DONE         = '☑️'
CANCELLED    = '🚫'
PENDING      = '🔄'
FAILED       = '💢'
BLOCKED      = '⛔'
VERIFIED     = '✔️'
UNVERIFIED   = '✖️'
ONLINE       = '🟢'
OFFLINE      = '🔴'
IDLE         = '🟡'
BANNED       = '🚫'
MUTED        = '🔇'
UNMUTED      = '🔊'
BUSY         = '⛔'
PREMIUM      = '💎'
BADGE        = '🏅'
MEDAL        = '🥇'
TROPHY       = '🏆'
NEW_TAG      = '🆕'
HOT          = '♨️'
TRENDING     = '📈'
DROPPED      = '📉'

# OTP / AUTH
OTP          = '🔑'
CODE         = '🔢'
LOCK         = '🔒'
UNLOCK       = '🔓'
KEY          = '🗝️'
PHONE        = '📱'
SMS          = '💬'
SHIELD       = '🛡️'
SESSION      = '🖥️'
LOGIN        = '🚪'
LOGOUT       = '🚶'
PASSWORD     = '🔐'
TOKEN        = '🎫'
TIMER        = '⏱️'
TIMEOUT      = '⌛'
EXPIRED      = '🕰️'

# PAYMENTS & CREDITS
CREDIT       = '💳'
MONEY        = '💰'
WALLET       = '👛'
COIN         = '🪙'
DIAMOND      = '💎'
GIFT         = '🎁'
RECEIPT      = '🧾'
INVOICE      = '📃'
PAID         = '✅'
REFUND       = '↩️'
BANK         = '🏦'
RUPEE        = '₹'
DOLLAR       = '💵'
USDT         = '🪙'
CRYPTO       = '₿'
PRICE_TAG    = '🏷️'
TRENDING_UP  = '📈'
TRENDING_DN  = '📉'
PLAN         = '📋'
BALANCE      = '⚖️'
TOPUP        = '➕'
DEDUCT       = '➖'

# ADMIN & MANAGEMENT
ADMIN        = '👮'
OWNER        = '👑'
BOT          = '🤖'
GEAR         = '⚙️'
SETTINGS     = '🛠️'
DATABASE     = '🗄️'
BROADCAST    = '📢'
BAN          = '🔨'
UNBAN        = '🔓'
MUTE         = '🔇'
UNMUTE       = '🔊'
WARN         = '⚠️'
STATS        = '📊'
LOGS         = '📜'
BACKUP       = '💾'
RESTART      = '🔁'
DEPLOY       = '🚀'
DEBUG        = '🐛'
TERMINAL     = '⌨️'
CONFIG       = '📝'

# USERS & SOCIAL
USER         = '👤'
USERS        = '👥'
NEW_USER     = '🆕'
VIP          = '🌟'
GUEST        = '🧑'
ANONYMOUS    = '👻'
SPY          = '🕵️'
SUPPORT      = '🎧'
HANDSHAKE    = '🤝'
WAVE         = '👋'
CLAP         = '👏'
THUMBS_UP    = '👍'
THUMBS_DOWN  = '👎'
HEART        = '❤️'
BROKEN_HEART = '💔'
PRAY         = '🙏'
COOL         = '😎'
ANGRY        = '😡'
SLEEP        = '💤'

# NOTIFICATIONS & MESSAGES
BELL         = '🔔'
NO_BELL      = '🔕'
PIN          = '📌'
INBOX        = '📥'
OUTBOX       = '📤'
MAIL         = '📧'
NOTE         = '📝'
ALERT        = '🚨'
ANNOUNCE     = '📣'
FORWARD      = '↪️'
REPLY        = '↩️'
MENTION      = '🔖'
LINK         = '🔗'
CHANNEL      = '📡'
GROUP        = '👥'
ID_BADGE     = '🆔'

# ACTIONS & UI
SEARCH       = '🔍'
ADD          = '➕'
REMOVE       = '➖'
EDIT         = '✏️'
DELETE       = '🗑️'
SAVE         = '💾'
COPY         = '📋'
SEND         = '📤'
DOWNLOAD     = '⬇️'
UPLOAD       = '⬆️'
REFRESH      = '🔄'
BACK         = '◀️'
NEXT         = '▶️'
CLOSE        = '✖️'
CONFIRM      = '✅'
MENU         = '📂'
LIST         = '📃'
FILTER       = '🔽'
SORT         = '🔼'
HOME         = '🏠'
HELP         = '❓'
FAQ          = '💡'
TUTORIAL     = '📖'

# COUNTRIES & GEOGRAPHY
GLOBE        = '🌐'
MAP          = '🗺️'
FLAG         = '🏳️'
LOCATION     = '📍'
INDIA        = '🇮🇳'
USA          = '🇺🇸'
UK           = '🇬🇧'
RUSSIA       = '🇷🇺'
PAKISTAN     = '🇵🇰'
BANGLADESH   = '🇧🇩'
NEPAL        = '🇳🇵'

# TIME & PROGRESS
CLOCK        = '🕐'
ALARM        = '⏰'
HOURGLASS    = '⌛'
CALENDAR     = '📅'
TODAY        = '📆'
FAST         = '💨'
SLOW         = '🐢'
DEADLINE     = '⏰'
INFINITE     = '♾️'

# MISC / FUN
FIRE         = '🔥'
SPARK        = '✨'
ROCKET       = '🚀'
ZAP          = '⚡'
STAR         = '⭐'
CROWN        = '👑'
ROBOT        = '🤖'
IDEA         = '💡'
MAGIC        = '🪄'
CRYSTAL      = '🔮'
BOMB         = '💣'
SKULL        = '💀'
NINJA        = '🥷'
ALIEN        = '👽'
RECYCLE      = '♻️'


# ─────────────────────────────────────────────────────────────────────────────
# HTML Rendering & Pyrogram Monkey-Patching for Custom Emojis
# ─────────────────────────────────────────────────────────────────────────────

# Combined regex pattern for matching common unicode emojis
EMOJI_REGEX_STR = (
    r'(?:'
    r'[\u2300-\u23ff]'             # Technical Symbols (e.g. ⏰, ⌛)
    r'|[\u2500-\u27bf]'           # Dingbats & Geometric (e.g. ⚠️, ❌, ✅, ⚡)
    r'|[\u2b00-\u2bff]'           # Arrows & Misc (e.g. ⭐, ⭕)
    r'|[\U0001f000-\U0001f9ff]'   # Emojis & Pictographs (e.g. 🚀, 🌍)
    r'|[\U0001fa00-\U0001faff]'   # Symbols Extended
    r'|[\u2000-\u3300]'           # CJK & Symbols (optional, keycaps/arrows)
    r'|\d\ufe0f?\u20e3'           # Keycaps (e.g. 1️⃣)
    r')'
)

EMOJI_REGEX = re.compile(EMOJI_REGEX_STR)


def render_custom_emojis(text: str) -> str:
    """Replace registered emojis with <tg-emoji> tags; unregistered emoji
    are left as plain Unicode (never stripped, unlike the earlier draft of
    this module — a missing ID should never make an emoji vanish).

    Tokenizes the text to avoid touching emoji that are:
    1. Inside HTML tags (e.g. <a href="...">)
    2. Inside existing <tg-emoji>...</tg-emoji> tags
    3. Inside inline code (`...`) or code blocks (```...```)
    """
    if not isinstance(text, str) or not text:
        return text

    registry = _load_registry()
    if not registry:
        return text

    # Tokenize the text using a regex that matches tags and code blocks
    pattern = re.compile(r'(<tg-emoji\b[^>]*>[\s\S]*?</tg-emoji>|```[\s\S]*?```|`[^`\n]+`|<[^>]+>)')
    parts = pattern.split(text)

    sorted_emojis = sorted(registry.keys(), key=len, reverse=True)
    escaped_emojis = [re.escape(e) for e in sorted_emojis]

    emoji_pattern = ('|'.join(escaped_emojis) + '|' + EMOJI_REGEX_STR) if escaped_emojis else EMOJI_REGEX_STR
    emoji_re = re.compile(f'({emoji_pattern})')

    def replace_match(match):
        em_char = match.group(1)
        doc_id = pick_document_id(em_char)
        if doc_id is not None:
            return f'<tg-emoji emoji-id="{doc_id}">{em_char}</tg-emoji>'
        # Unregistered emoji — keep it as a normal Unicode emoji, never strip it.
        return em_char

    for i in range(0, len(parts), 2):  # Only process non-matched parts (even indices)
        parts[i] = emoji_re.sub(replace_match, parts[i])

    return "".join(parts)


_EMOJI_PATCH_FLAG = "_rishu_emoji_patched"


def apply_emoji_patch() -> None:
    """Idempotent — call once at startup, AFTER apply_rich_patch() (see
    utils/rich_patch.py). Order matters: this wraps whatever
    Client.send_message/edit_message_text already is, so applying it
    second means emoji-rendering runs on the text first, then the
    already-installed rich-message check runs on the result — the correct
    order, since <tg-emoji> is not a rich-only tag and never trips that
    check either way.

    Also patches InlineKeyboardButton.__init__ so a button label with a
    LEADING registered emoji (e.g. "🚀 Deploy") gets that emoji rendered as
    a real button icon via icon_custom_emoji_id, with the emoji stripped
    from the visible text. This assumes your Kurigram build's
    InlineKeyboardButton accepts icon_custom_emoji_id — if it doesn't, this
    patch will raise on the very first button created anywhere in the bot,
    so test a single /start or /help call right after deploying this.
    """
    from pyrogram import Client
    from pyrogram.enums import ParseMode
    from pyrogram.types import InlineKeyboardButton

    if getattr(Client, _EMOJI_PATCH_FLAG, False):
        return

    orig_send_message = Client.send_message

    async def new_send_message(self, chat_id, text, parse_mode=None, *args, **kwargs):
        effective_mode = parse_mode if parse_mode is not None else (self.parse_mode or ParseMode.DEFAULT)
        if effective_mode != ParseMode.DISABLED and isinstance(text, str):
            text = render_custom_emojis(text)
            if parse_mode == ParseMode.MARKDOWN:
                parse_mode = ParseMode.DEFAULT
        return await orig_send_message(self, chat_id, text, parse_mode=parse_mode, *args, **kwargs)

    Client.send_message = new_send_message

    orig_edit_message_text = Client.edit_message_text

    async def new_edit_message_text(self, chat_id, message_id, text, parse_mode=None, *args, **kwargs):
        effective_mode = parse_mode if parse_mode is not None else (self.parse_mode or ParseMode.DEFAULT)
        if effective_mode != ParseMode.DISABLED and isinstance(text, str):
            text = render_custom_emojis(text)
            if parse_mode == ParseMode.MARKDOWN:
                parse_mode = ParseMode.DEFAULT
        return await orig_edit_message_text(self, chat_id, message_id, text, parse_mode=parse_mode, *args, **kwargs)

    Client.edit_message_text = new_edit_message_text

    # Monkey-patch InlineKeyboardButton constructor to extract a leading
    # registered emoji as a button icon. ⚠️ RISKY — see docstring above.
    orig_button_init = InlineKeyboardButton.__init__

    def extract_button_emoji(text: str):
        if not isinstance(text, str) or not text:
            return text, None
        registry = _load_registry()
        if not registry:
            return text, None

        stripped_start = text.lstrip()
        sorted_emojis = sorted(registry.keys(), key=len, reverse=True)

        for em_char in sorted_emojis:
            if stripped_start.startswith(em_char):
                remainder = stripped_start[len(em_char):].strip()
                if remainder.startswith(('-', '|', ':', '→')):
                    remainder = remainder[1:].strip()
                if remainder:
                    doc_id = pick_document_id(em_char)
                    if doc_id is not None:
                        return remainder, str(doc_id)
                break

        return text, None

    def new_button_init(self, text: str, *args, **kwargs):
        if "icon_custom_emoji_id" not in kwargs and len(args) < 12:
            clean_text, doc_id = extract_button_emoji(text)
            if doc_id:
                text = clean_text
                kwargs["icon_custom_emoji_id"] = doc_id
        orig_button_init(self, text, *args, **kwargs)

    InlineKeyboardButton.__init__ = new_button_init

    setattr(Client, _EMOJI_PATCH_FLAG, True)
