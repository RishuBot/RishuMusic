# ============================================================
# RishuMusic/utils/play_buttons.py — v3
#
# CHANGELOG (v2 -> v3)  [checked against the real repo]:
#   - Autoplay ON/OFF now uses the repo's OWN autoplay state
#     (RishuMusic.utils.autoplay.is_on / set_on, default OFF) - the button can
#     no longer disagree with /autoplay on|off. Turning it ON passes the same
#     "ref" (last queued track) that /autoplay on uses, so prefetch starts.
#   - Removed my separate state + autoplay_next_if_on(): enqueue_next already
#     checks is_on(), so skip.py / core/call.py need NO change.
#   - YT-API button is found by its callback ("oapi") as well as by text, because
#     the real label is small-caps ("ʏᴛ-ᴀᴘɪ").
# CHANGELOG (v1 -> v2):
#   - EVERY button gets a colour; paint_markup() for the other menus.
#
# What this file does for the play card's inline keyboard:
#   1) removes the "YT-API" button and puts "Autoplay: ON / OFF" in its place
#      (callback "APTOGGLE <chat_id>", handled in plugins/play/dlbuttons.py)
#   2) colours every button (primary = blue, success = green, danger = red).
#      Buttons that already have a style are left alone.
# ============================================================

import copy

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

try:  # Kurigram >= 2.2.26 (the repo already uses it in utils/inline/start.py)
    from pyrogram.enums import ButtonStyle as _BS
except Exception:  # pragma: no cover
    _BS = None

STYLE_BAD = False  # set True by stream.py / play.py if Telegram rejects a style


# ------------------------------------------------------------
# autoplay on / off  (thin wrappers over the repo's utils/autoplay)
# ------------------------------------------------------------
def is_autoplay_on(chat_id) -> bool:
    try:
        from RishuMusic.utils.autoplay import is_on

        return bool(is_on(int(chat_id)))
    except Exception:
        return False


def set_autoplay(chat_id, on: bool) -> None:
    """Same thing /autoplay on|off does (plugins/tools/autoplay.py)."""
    from RishuMusic.misc import db
    from RishuMusic.utils.autoplay import set_on

    chat_id = int(chat_id)
    ref = None
    if on:
        q = db.get(chat_id)
        if q:
            ref = (q[-1].get("vidid"), q[-1].get("title"))
    set_on(chat_id, bool(on), ref)


# ------------------------------------------------------------
# colours
# ------------------------------------------------------------
_ADMIN_COLORS = {
    "Resume": "success",
    "Pause": "primary",
    "Replay": "primary",
    "Skip": "success",
    "Stop": "danger",
    "End": "danger",
}


def _style_value(name: str):
    if _BS is not None:
        v = getattr(_BS, name.upper(), None)
        if v is not None:
            return v
    return name


def _already_styled(b) -> bool:
    cur = getattr(b, "style", None)
    if cur is None:
        return False
    s = str(getattr(cur, "name", cur)).lower().split(".")[-1]
    return s not in ("", "none", "default")


def _paint(b, name):
    """Return a coloured copy of button b (or b itself if colours aren't possible)."""
    if STYLE_BAD or not name or not hasattr(b, "style") or _already_styled(b):
        return b
    try:
        b2 = copy.copy(b)
        b2.style = _style_value(name)
        return b2
    except Exception:
        return b


def _data(b):
    d = getattr(b, "callback_data", None)
    if isinstance(d, bytes):
        d = d.decode("utf-8", "ignore")
    return d if isinstance(d, str) else None


def _kind(b):
    """Colour for a button. Specific buttons first, then EVERYTHING else gets blue."""
    d = _data(b)
    if d:
        if d.startswith("ADMIN") and "|" in d:
            parts = d.split("|", 1)[0].split()
            c = _ADMIN_COLORS.get(parts[-1]) if parts else None
            if c:
                return c
        elif d.startswith("DLAUDIO"):
            return "primary"
        elif d.startswith("DLVIDEO"):
            return "success"
        elif d.startswith(("close", "forceclose")):
            return "danger"
        elif d.startswith("MusicStream"):  # "MusicStream vidid|user|mode|c|f"
            try:
                return "success" if d.split(None, 1)[1].split("|")[2] == "v" else "primary"
            except Exception:
                pass
        elif d.startswith("ShreePlaylists"):  # "ShreePlaylists id|user|type|mode|c|f"
            try:
                return "success" if d.split(None, 1)[1].split("|")[3] == "v" else "primary"
            except Exception:
                pass
    # timer bar, slider arrows, links, anything unknown -> blue
    if d or getattr(b, "url", None):
        return "primary"
    return None


# ------------------------------------------------------------
# build / decorate
# ------------------------------------------------------------
def chat_key(markup):
    """Voice-chat id (the db key) found in the card's own callback data."""
    try:
        for r in markup.inline_keyboard:
            for b in r:
                d = _data(b)
                if not d:
                    continue
                if d.startswith("ADMIN") and "|" in d:
                    return d.split("|", 1)[1].split("_")[0].strip()
                if d.startswith(("DLAUDIO", "DLVIDEO", "APTOGGLE")):
                    return d.split(None, 1)[1].strip()
    except Exception:
        pass
    return None


def _ap_button(chat, colors: bool):
    on = is_autoplay_on(chat)
    b = InlineKeyboardButton(
        "Autoplay: ON" if on else "Autoplay: OFF",
        callback_data=f"APTOGGLE {chat}",
    )
    return _paint(b, "success" if on else "danger") if colors else b


def _is_ytapi(b) -> bool:
    if _data(b) == "oapi":  # the real YT-API button (utils/inline/play.py)
        return True
    t = (getattr(b, "text", "") or "").lower().replace(" ", "")
    return t in ("yt-api", "ytapi", "ʏᴛ-ᴀᴘɪ", "ʏᴛᴀᴘɪ")


async def decorate_markup(markup, chat_id=None, colors: bool = True):
    """YT-API -> Autoplay toggle, then colours. Never raises (returns markup on error)."""
    try:
        rows = [list(r) for r in markup.inline_keyboard]
        chat = chat_id if chat_id is not None else chat_key(markup)
        have_ap = False
        for r in rows:
            for i, b in enumerate(r):
                d = _data(b) or ""
                if d.startswith("APTOGGLE") or _is_ytapi(b):
                    if chat is not None:
                        r[i] = _ap_button(chat, colors)
                        have_ap = True
                    else:
                        r[i] = None  # no chat id -> just drop the YT-API button
            r[:] = [b for b in r if b is not None]
        rows = [r for r in rows if r]
        if not have_ap and chat is not None:
            rows.append([_ap_button(chat, colors)])
        if colors:
            rows = [[_paint(b, _kind(b)) for b in r] for r in rows]
        return InlineKeyboardMarkup(rows)
    except Exception:
        return markup


def paint_markup(markup, colors: bool = True):
    """Colour a keyboard only (no YT-API swap, no autoplay button).
    For the other cards: pre-play card, slider, queue messages. Never raises."""
    if not colors or STYLE_BAD:
        return markup
    try:
        rows = [[_paint(b, _kind(b)) for b in r] for r in markup.inline_keyboard]
        return InlineKeyboardMarkup(rows)
    except Exception:
        return markup
