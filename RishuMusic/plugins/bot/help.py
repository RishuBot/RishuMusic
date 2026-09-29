# v3 — rich UI help panel
# - Main help panel (/help in PM + "Back" from any category) is a rich
#   message: image, heading, welcome line, support note, and collapsible
#   QUICK START / POPULAR COMMANDS / GOOD TO KNOW tables.
# - Category pages (helpers.HELP_N) are rich tables (see strings/helpers.py).
# - If the current message is a photo/video message, it is deleted and a
#   fresh rich message is sent (edit_message_text can't turn media into text).
# - helper_cb no longer needs one elif per category; a missing HELP_N shows
#   an alert instead of crashing.
# REQUIRES: utils/rich_ui.py (+ rich_patch.py for the group /help reply).

import html as _html
import random
from typing import Union

from pyrogram import filters, types
from pyrogram.errors import MessageNotModified
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, Message

import config
from RishuMusic import app
from RishuMusic.misc import SUDOERS
from RishuMusic.utils import help_pannel
from RishuMusic.utils.database import get_lang
from RishuMusic.utils.decorators.language import LanguageStart, languageCB
from RishuMusic.utils.inline.help import help_back_markup, private_help_panel
from RishuMusic.utils.rich_ui import (
    rich_details,
    rich_edit,
    rich_heading,
    rich_img,
    rich_note,
    rich_reply,
    rich_send,
    rich_table,
    sanitize_display_name,
)
from config import BANNED_USERS, SUPPORT_CHAT
from strings import get_string, helpers


def _support_url():
    u = (SUPPORT_CHAT or "").strip()
    if u.startswith("@"):
        return "https://t.me/" + u[1:]
    if u.startswith(("t.me/", "telegram.me/")):
        return "https://" + u
    if u.startswith(("http://", "https://")):
        return u
    return None


def help_panel_html(name: str) -> str:
    """Rich body for the main help panel. `name` must already be HTML-safe."""
    support = _support_url()
    if support:
        support_line = (
            "💬 Ask your doubts at "
            f'<a href="{_html.escape(support, quote=True)}">Support Chat</a>'
        )
    else:
        support_line = "💬 Ask your doubts in our support chat"

    quick_start = rich_table(
        ["Step", "What to do"],
        [
            ("1️⃣", "Add me to your group and promote me as admin"),
            ("2️⃣", "Start a voice chat in the group"),
            ("3️⃣", "Send <code>/play song name</code> or paste a link"),
            ("4️⃣", "Control playback with the player buttons"),
        ],
    )

    popular = rich_table(
        ["Command", "What it does"],
        [
            ("<code>/play</code> [name/link]", "Stream audio in the voice chat"),
            ("<code>/vplay</code> [name/link]", "Stream video in the voice chat"),
            ("<code>/pause</code> · <code>/resume</code>", "Pause or resume the stream"),
            ("<code>/skip</code>", "Skip to the next track"),
            ("<code>/queue</code>", "Show the upcoming tracks"),
            ("<code>/loop</code>", "Repeat the current stream"),
            ("<code>/end</code>", "Stop and clear the queue"),
            ("<code>/settings</code>", "Open the group settings"),
        ],
    )

    good_to_know = (
        "<p>📌 Give me these admin rights: delete messages, manage video chats, invite users.</p>"
        "<p>📌 Add <b>c</b> before a command (like <code>/cplay</code>) to stream in a linked channel.</p>"
        "<p>📌 My assistant account joins the voice chat by itself — please don't remove it.</p>"
        "<p>📌 Auth users can use admin commands too — see <code>/auth</code>.</p>"
    )

    return (
        rich_img(random.choice(config.START_IMG_URL))
        + rich_heading("📖 HELP CENTER", level=1)
        + f"<p>👋 Hey <b>{name}</b>, pick a category from the buttons below to see its commands.</p>"
        + rich_note(support_line)
        + rich_details("⚡️ QUICK START", quick_start, open=True)
        + rich_details("🎧 POPULAR COMMANDS", popular)
        + rich_details("📌 GOOD TO KNOW", good_to_know)
        + "<p><i>Tap a category below for its full command list.</i></p>"
    )


def _is_media_message(msg) -> bool:
    return bool(
        msg
        and (
            getattr(msg, "photo", None)
            or getattr(msg, "video", None)
            or getattr(msg, "animation", None)
            or getattr(msg, "document", None)
        )
    )


async def _show(cq: CallbackQuery, html: str, keyboard):
    """Show `html` (rich) in place of the message the button was pressed on."""
    msg = cq.message
    if _is_media_message(msg):
        # A photo/video message can't be edited into a text/rich message.
        try:
            await msg.delete()
        except Exception:
            pass
        return await rich_send(app, msg.chat.id, html, reply_markup=keyboard)
    try:
        return await rich_edit(cq, html, reply_markup=keyboard)
    except MessageNotModified:
        return None


@app.on_message(filters.command(["help"]) & filters.private & ~BANNED_USERS)
@app.on_callback_query(filters.regex("settings_back_helper") & ~BANNED_USERS)
async def helper_private(
    client, update: Union[types.Message, types.CallbackQuery]
):
    is_callback = isinstance(update, types.CallbackQuery)
    is_sudo = update.from_user.id in SUDOERS
    name = sanitize_display_name(update.from_user.first_name)
    if is_callback:
        try:
            await update.answer()
        except Exception:
            pass
        chat_id = update.message.chat.id
        language = await get_lang(chat_id)
        _ = get_string(language)
        keyboard = help_pannel(_, is_sudo, True)
        await _show(update, help_panel_html(name), keyboard)
    else:
        try:
            await update.delete()
        except Exception:
            pass
        language = await get_lang(update.chat.id)
        _ = get_string(language)
        keyboard = help_pannel(_, is_sudo)
        await rich_send(
            client, update.chat.id, help_panel_html(name), reply_markup=keyboard
        )


@app.on_message(filters.command(["help"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def help_com_group(client, message: Message, _):
    keyboard = private_help_panel(_)
    html = (
        rich_heading("📖 HELP", level=2)
        + rich_note(_["help_2"])
        + "<p><i>Tap the button below to open the full help menu in private.</i></p>"
    )
    await rich_reply(
        message, html, reply_markup=InlineKeyboardMarkup(keyboard)
    )


@app.on_callback_query(filters.regex("help_callback") & ~BANNED_USERS)
@languageCB
async def helper_cb(client, CallbackQuery: CallbackQuery, _):
    try:
        await CallbackQuery.answer()
    except Exception:
        pass
    parts = CallbackQuery.data.strip().split(None, 1)
    cb = parts[1] if len(parts) > 1 else ""
    keyboard = help_back_markup(_)
    text = None
    if cb.startswith("hb") and cb[2:].isdigit():
        text = getattr(helpers, f"HELP_{cb[2:]}", None)
    if not text:
        try:
            return await CallbackQuery.answer(
                "This section isn't available yet.", show_alert=True
            )
        except Exception:
            return
    await _show(CallbackQuery, text, keyboard)
