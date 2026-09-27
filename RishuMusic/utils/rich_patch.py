# -----------------------------------------------
# 🔸 RishuMusic — utils/rich_patch.py
# 🔹 Wires rich_ui.py into EVERY existing text call, project-wide
#
# Import + call apply_rich_patch() ONCE at startup (RishuMusic/__init__.py,
# right after `app` is built). After that, nothing in any plugin file has
# to change:
#
#     await message.reply_text("<h2>Queue</h2><table>...</table>")
#     await msg.edit_text("<blockquote>done</blockquote>")
#     await app.send_message(chat_id, "<h1>Hi</h1>")
#
# all keep working exactly as written — the ONLY difference is that if the
# HTML you pass contains a rich-only tag (h1-h6, table, details/summary,
# mark, sub/sup, tg-button, img), it is transparently sent/edited as a
# native Bot API 10.2+ Rich Message instead of being silently stripped by
# the classic HTML parser. Plain messages with no rich tags (the vast
# majority of your ~existing plugins) go through completely untouched —
# zero behaviour change, zero risk of regression for existing plugins.
#
# Safe to import multiple times — apply_rich_patch() is idempotent.
# -----------------------------------------------
"""utils/rich_patch.py — project-wide Rich Message auto-upgrade.

How it works
------------
``inspect.signature(...).bind_partial`` is used to find the ``text``/``caption``
argument regardless of whether the call site passed it positionally or as a
keyword — so this patch works for whatever mix of call styles your plugins
already use (``send_message(chat_id, text)``, ``send_message(chat_id, text=text)``,
``msg.edit_text(text)``, ``message.reply_text(text, reply_markup=kb)``, etc.)
without requiring any of them to be rewritten.

Patched:
  * ``Client.send_message``
  * ``Client.edit_message_text``
  * ``Message.edit_text``
  * ``Message.reply_text`` (and ``Message.reply``, re-aliased afterwards)
  * ``CallbackQuery.edit_message_text``
  * ``InputMedia.__init__`` (base of Photo/Video/Document/Animation/Audio) — caption safety
  * ``Client.send_photo`` (also covers the ``Message.reply_photo`` shortcut) — caption safety

Each wrapper delegates to :mod:`rich_ui`'s ``rich_send`` / ``rich_edit`` /
``rich_reply`` only when the outgoing text actually contains a rich-only tag;
otherwise it calls straight through to the original method. Because the
plain-text fallback inside ``rich_ui`` always flattens the HTML *before*
calling back into ``send_message``/``edit_message_text``, there is no
recursion even though those are the very methods being patched.

Why captions are handled separately
------------------------------------
Telegram photo/video captions have **no** ``rich_message`` parameter at all —
only full text messages can be Rich Messages. If a caption string contains a
rich-only tag (``<table>``, ``<h3>``, etc.), Telegram's classic HTML entity
parser doesn't recognize it and the whole caption can come back **empty**
instead of just losing the unknown tag. The fix is NOT to make captions
rich (Telegram doesn't support that) — it's to always flatten rich HTML
into caption-safe HTML (via ``rich_caption()``) before it ever reaches
Telegram, so a table degrades to readable bold/newline text instead of
vanishing.

NOTE on start.py
-----------------
``plugins/bot/start.py`` in this bot already calls ``client.send_rich_message``
directly for the /start screen and doesn't need this patch — this module is
for every OTHER plugin (queue, help, admin, etc.) where you'd otherwise have
to add rich-message handling by hand in ~150 places.
"""

from __future__ import annotations

import functools
import inspect
import logging

from pyrogram import Client
from pyrogram.errors import MessageNotModified
from pyrogram.types import Message, CallbackQuery
from pyrogram.types.input_content.input_media import InputMedia

from .rich_ui import _has_rich_only_tags, rich_send, rich_reply, rich_edit, rich_caption

logger = logging.getLogger("pyrogram")

_PATCH_FLAG = "_rishu_rich_patched"


def _text_from(bound: inspect.BoundArguments, name: str):
    value = bound.arguments.get(name)
    return value if isinstance(value, str) else None


def _wrap_send_message(orig):
    sig = inspect.signature(orig)

    @functools.wraps(orig)
    async def send_message(self, *args, **kwargs):
        bound = sig.bind_partial(self, *args, **kwargs)
        text = _text_from(bound, "text")
        if text and _has_rich_only_tags(text):
            chat_id = bound.arguments.get("chat_id")
            try:
                return await rich_send(
                    self,
                    chat_id,
                    text,
                    reply_markup=bound.arguments.get("reply_markup"),
                    reply_parameters=bound.arguments.get("reply_parameters"),
                    message_thread_id=bound.arguments.get("message_thread_id"),
                    disable_notification=bound.arguments.get("disable_notification"),
                    protect_content=bound.arguments.get("protect_content"),
                )
            except Exception as e:
                logger.debug(f"[rich_patch] send_message rich path failed, falling through: {e}")
        return await orig(*bound.args, **bound.kwargs)

    return send_message


def _wrap_client_edit_message_text(orig):
    sig = inspect.signature(orig)

    @functools.wraps(orig)
    async def edit_message_text(self, *args, **kwargs):
        bound = sig.bind_partial(self, *args, **kwargs)
        text = _text_from(bound, "text")
        if text and _has_rich_only_tags(text):
            try:
                return await rich_edit(
                    self,
                    text,
                    chat_id=bound.arguments.get("chat_id"),
                    message_id=bound.arguments.get("message_id"),
                    reply_markup=bound.arguments.get("reply_markup"),
                )
            except Exception as e:
                logger.debug(f"[rich_patch] edit_message_text rich path failed, falling through: {e}")
        try:
            return await orig(*bound.args, **bound.kwargs)
        except MessageNotModified:
            # Editing to identical content — harmless, ignore it instead of
            # crashing the handler (e.g. re-opening a panel that's already
            # showing this exact text/keyboard).
            return None

    return edit_message_text


def _wrap_message_edit_text(orig):
    sig = inspect.signature(orig)

    @functools.wraps(orig)
    async def edit_text(self, *args, **kwargs):
        bound = sig.bind_partial(self, *args, **kwargs)
        text = _text_from(bound, "text")
        if text and _has_rich_only_tags(text):
            try:
                return await rich_edit(self, text, reply_markup=bound.arguments.get("reply_markup"))
            except Exception as e:
                logger.debug(f"[rich_patch] edit_text rich path failed, falling through: {e}")
        try:
            return await orig(*bound.args, **bound.kwargs)
        except MessageNotModified:
            return None

    return edit_text


def _wrap_message_reply_text(orig):
    sig = inspect.signature(orig)

    @functools.wraps(orig)
    async def reply_text(self, *args, **kwargs):
        bound = sig.bind_partial(self, *args, **kwargs)
        text = _text_from(bound, "text")
        if text and _has_rich_only_tags(text):
            try:
                return await rich_reply(
                    self,
                    text,
                    reply_markup=bound.arguments.get("reply_markup"),
                    quote=bound.arguments.get("quote", True),
                )
            except Exception as e:
                logger.debug(f"[rich_patch] reply_text rich path failed, falling through: {e}")
        return await orig(*bound.args, **bound.kwargs)

    return reply_text


def _wrap_cq_edit_message_text(orig):
    sig = inspect.signature(orig)

    @functools.wraps(orig)
    async def edit_message_text(self, *args, **kwargs):
        bound = sig.bind_partial(self, *args, **kwargs)
        text = _text_from(bound, "text")
        if text and _has_rich_only_tags(text):
            try:
                return await rich_edit(self, text, reply_markup=bound.arguments.get("reply_markup"))
            except Exception as e:
                logger.debug(f"[rich_patch] callback edit_message_text rich path failed, falling through: {e}")
        try:
            return await orig(*bound.args, **bound.kwargs)
        except MessageNotModified:
            return None

    return edit_message_text


def _wrap_input_media_init(orig_init):
    @functools.wraps(orig_init)
    def __init__(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        # caption always ends up as a plain attribute after __init__, no matter
        # whether the caller passed it positionally or as a keyword.
        caption = getattr(self, "caption", None)
        if isinstance(caption, str) and _has_rich_only_tags(caption):
            self.caption = rich_caption(caption)
    return __init__


def _wrap_send_photo(orig):
    sig = inspect.signature(orig)

    @functools.wraps(orig)
    async def send_photo(self, *args, **kwargs):
        bound = sig.bind_partial(self, *args, **kwargs)
        caption = _text_from(bound, "caption")
        if caption and _has_rich_only_tags(caption):
            bound.arguments["caption"] = rich_caption(caption)
        return await orig(*bound.args, **bound.kwargs)

    return send_photo


def apply_rich_patch() -> None:
    """Idempotent — call once at startup, after pyrogram is imported."""
    if getattr(Client, _PATCH_FLAG, False):
        return

    Client.send_message = _wrap_send_message(Client.send_message)
    Client.edit_message_text = _wrap_client_edit_message_text(Client.edit_message_text)
    Message.edit_text = _wrap_message_edit_text(Message.edit_text)
    Message.reply_text = _wrap_message_reply_text(Message.reply_text)
    Message.reply = Message.reply_text  # re-alias: was `reply = reply_text` pre-patch too
    CallbackQuery.edit_message_text = _wrap_cq_edit_message_text(CallbackQuery.edit_message_text)

    # Caption safety — captions can NEVER be rich messages (see module docstring).
    InputMedia.__init__ = _wrap_input_media_init(InputMedia.__init__)
    Client.send_photo = _wrap_send_photo(Client.send_photo)  # also fixes Message.reply_photo

    setattr(Client, _PATCH_FLAG, True)
    logger.info("[rich_patch] Rich Message auto-upgrade applied to Client/Message/CallbackQuery.")
