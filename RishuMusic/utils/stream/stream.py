# ============================================================
# stream.py — v5
# CHANGELOG (v4 -> v5):
#   - Error ab OWNER_ID ke DM me aata hai (fail ho to LOGGER_ID fallback).
# CHANGELOG (v3 -> v4):
#   - Rich fail hone par exact error ab LOGGER_ID chat me aata hai
#     (once per unique error). Container logs ki zarurat nahi.
# CHANGELOG (v2 -> v3):
#   - 3 attempts: dropdown+emoji-render -> dropdown (no render) -> plain table.
# CHANGELOG (v1 -> v2):
#   - "Now Streaming" table ab <details>/<summary> dropdown ke andar.
# en.yml: no change needed.
# ============================================================

import os
import traceback
from html import escape as _html_escape
from random import randint
from typing import Union

from pyrogram.types import InlineKeyboardMarkup

import config
from RishuMusic import Carbon, YouTube, app
from RishuMusic.core.call import shree
from RishuMusic.misc import db
from RishuMusic.utils.database import add_active_video_chat, is_active_chat
from RishuMusic.utils.exceptions import AssistantErr
from RishuMusic.utils.inline import aq_markup, close_markup, stream_markup
# v5 (broken)
# from RishuMusic.utils.pastebin import shreeBin

# v6
from RishuMusic.utils.pastebin import ShreeBin as shreeBin
from RishuMusic.utils.premium_emojis import render_custom_emojis
from RishuMusic.utils.rich_ui import (
    RICH_AVAILABLE,
    _input_rich,
    rich_esc,
    rich_img,
    rich_kv_table,
)
from RishuMusic.utils.stream.queue import put_queue, put_queue_index
from RishuMusic.utils.thumbnails import get_thumb


# v4 NEW: rich fail hone par exact error LOGGER_ID chat me aayega (no logs needed)
_reported = set()


async def _report_rich_error(where: str, name: str, ex) -> None:
    text = f"{type(ex).__name__}: {ex}" if isinstance(ex, BaseException) else str(ex)
    key = (where, name, text[:80])
    if key in _reported:  # same error baar-baar spam na ho
        return
    _reported.add(key)
    msg = f"⚠️ <b>{where}</b> [{name}] failed\n<code>{_html_escape(text[:900])}</code>"
    # v5: pehle Owner ke DM me, owner ne bot start nahi kiya ho to LOGGER_ID me
    try:
        await app.send_message(config.OWNER_ID, msg)
    except Exception:
        try:
            await app.send_message(config.LOGGER_ID, msg)
        except Exception:
            pass


# v4 (v3 se same, emoji default empty)
def _rich_details(title: str, table: str, emoji: str = "") -> str:
    lead = f"{emoji} " if emoji else ""
    return f"<details><summary>{lead}<b>{title}</b></summary>{table}</details>"


async def _rich_photo_card(
    chat_id, img, markup, plain_cap, *, title=None, duration_min=None,
    user_name=None, link=None, extra_rows=None,
):
    """Send the 'Now Streaming' card as a real Bot API 10.2+ Rich Message:
    thumbnail + a genuine HTML ``<table>`` inside a <details> dropdown (v2).

    ``plain_cap`` (the existing stream_1/stream_2-formatted string) is kept
    as the fallback caption if rich delivery isn't available on this
    client/account or fails for any reason — the card always sends either
    way, this only changes how it renders when it works.

    Pass either (title, duration_min, user_name[, link]) to get a real
    table, or leave them unset to fall back to plain_cap even in the rich
    path (used for cards that have no song info, e.g. the index/m3u8 card).
    """
    if not RICH_AVAILABLE:
        await _report_rich_error("stream._rich_photo_card", "import", "RICH_AVAILABLE is False (rich_ui import/support issue)")
    elif img and title is not None:
        rows = []
        title_cell = rich_esc(title)
        if link:
            title_cell = f'<a href="{rich_esc(link)}">{title_cell}</a>'
        rows.append(("ᴛɪᴛʟᴇ", title_cell))
        if duration_min is not None:
            rows.append(("ᴅᴜʀᴀᴛɪᴏɴ", f"{rich_esc(duration_min)} ᴍɪɴᴜᴛᴇs"))
        if user_name is not None:
            rows.append(("ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ", rich_esc(user_name)))
        if extra_rows:
            rows.extend(extra_rows)
        table = rich_kv_table(rows)
        head = rich_img(img) + "\n<b>❖ Mᴜsɪᴄ Oɴ Sᴛʀᴇᴀᴍɪɴɢ ⏤●</b>\n"
        attempts = (
            ("details+emoji-render",
             render_custom_emojis(head + _rich_details("ᴛʀᴀᴄᴋ ɪɴғᴏ", table))),
            ("details-no-render",
             head + _rich_details("ᴛʀᴀᴄᴋ ɪɴғᴏ", table)),
            ("plain-table",
             render_custom_emojis(head + table)),
        )
        for name, body in attempts:
            try:
                return await app.send_rich_message(
                    chat_id=chat_id,
                    rich_message=_input_rich(body),
                    reply_markup=markup,
                )
            except Exception as ex:
                traceback.print_exc()
                await _report_rich_error("stream._rich_photo_card", name, ex)
    return await app.send_photo(
        chat_id,
        photo=img,
        caption=render_custom_emojis(plain_cap),
        reply_markup=markup,
    )


async def stream(
    _,
    mystic,
    user_id,
    result,
    chat_id,
    user_name,
    original_chat_id,
    video: Union[bool, str] = None,
    streamtype: Union[bool, str] = None,
    spotify: Union[bool, str] = None,
    forceplay: Union[bool, str] = None,
):
    if not result:
        return
    if forceplay:
        await shree.force_stop_stream(chat_id)
    if streamtype == "playlist":
        msg = f"{_['play_19']}\n\n"
        count = 0
        for search in result:
            if int(count) == config.PLAYLIST_FETCH_LIMIT:
                continue
            try:
                (
                    title,
                    duration_min,
                    duration_sec,
                    thumbnail,
                    vidid,
                ) = await YouTube.details(search, False if spotify else True)
            except:
                continue
            if str(duration_min) == "None":
                continue
            if duration_sec > config.DURATION_LIMIT:
                continue
            if await is_active_chat(chat_id):
                await put_queue(
                    chat_id,
                    original_chat_id,
                    f"vid_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                )
                position = len(db.get(chat_id)) - 1
                count += 1
                msg += f"{count}. {title[:70]}\n"
                msg += f"{_['play_20']} {position}\n\n"
            else:
                if not forceplay:
                    db[chat_id] = []
                status = True if video else None
                try:
                    file_path, direct = await YouTube.download(
                        vidid, mystic, video=status, videoid=True
                    )
                except:
                    raise AssistantErr(_["play_14"])
                await shree.join_call(
                    chat_id,
                    original_chat_id,
                    file_path,
                    video=status,
                    image=thumbnail,
                )
                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path if direct else f"vid_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                    forceplay=forceplay,
                )
                img = await get_thumb(vidid, user_id)
                button = stream_markup(_, chat_id)
                link = f"https://t.me/{app.username}?start=info_{vidid}"
                run = await _rich_photo_card(
                    original_chat_id,
                    img,
                    InlineKeyboardMarkup(button),
                    _["stream_1"].format(link, title[:23], duration_min, user_name),
                    title=title[:23],
                    duration_min=duration_min,
                    user_name=user_name,
                    link=link,
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"
        if count == 0:
            return
        else:
            link = await shreeBin(msg)
            lines = msg.count("\n")
            if lines >= 17:
                car = os.linesep.join(msg.split(os.linesep)[:17])
            else:
                car = msg
            carbon = await Carbon.generate(car, randint(100, 10000000))
            upl = close_markup(_)
            return await app.send_photo(
                original_chat_id,
                photo=carbon,
                caption=_["play_21"].format(position, link),
                reply_markup=upl,
            )
    elif streamtype == "youtube":
        link = result["link"]
        vidid = result["vidid"]
        title = (result["title"]).title()
        duration_min = result["duration_min"]
        thumbnail = result["thumb"]
        status = True if video else None
        try:
            file_path, direct = await YouTube.download(
                vidid, mystic, videoid=True, video=status
            )
        except:
            raise AssistantErr(_["play_14"])
        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                file_path if direct else f"vid_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await app.send_message(
                chat_id=original_chat_id,
                text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                reply_markup=InlineKeyboardMarkup(button),
            )
        else:
            if not forceplay:
                db[chat_id] = []
            await shree.join_call(
                chat_id,
                original_chat_id,
                file_path,
                video=status,
                image=thumbnail,
            )
            await put_queue(
                chat_id,
                original_chat_id,
                file_path if direct else f"vid_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
                forceplay=forceplay,
            )
            img = await get_thumb(vidid, user_id)
            button = stream_markup(_, chat_id)
            link = f"https://t.me/{app.username}?start=info_{vidid}"
            run = await _rich_photo_card(
                original_chat_id,
                img,
                InlineKeyboardMarkup(button),
                _["stream_1"].format(link, title[:23], duration_min, user_name),
                title=title[:23],
                duration_min=duration_min,
                user_name=user_name,
                link=link,
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "stream"
    elif streamtype == "soundcloud":
        file_path = result["filepath"]
        title = result["title"]
        duration_min = result["duration_min"]
        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "audio",
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await app.send_message(
                chat_id=original_chat_id,
                text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                reply_markup=InlineKeyboardMarkup(button),
            )
        else:
            if not forceplay:
                db[chat_id] = []
            await shree.join_call(chat_id, original_chat_id, file_path, video=None)
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "audio",
                forceplay=forceplay,
            )
            button = stream_markup(_, chat_id)
            run = await _rich_photo_card(
                original_chat_id,
                config.SOUNCLOUD_IMG_URL,
                InlineKeyboardMarkup(button),
                _["stream_1"].format(
                    config.SUPPORT_CHAT, title[:23], duration_min, user_name
                ),
                title=title[:23],
                duration_min=duration_min,
                user_name=user_name,
                link=config.SUPPORT_CHAT,
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
    elif streamtype == "telegram":
        file_path = result["path"]
        link = result["link"]
        title = (result["title"]).title()
        duration_min = result["dur"]
        status = True if video else None
        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "video" if video else "audio",
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await app.send_message(
                chat_id=original_chat_id,
                text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                reply_markup=InlineKeyboardMarkup(button),
            )
        else:
            if not forceplay:
                db[chat_id] = []
            await shree.join_call(chat_id, original_chat_id, file_path, video=status)
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "video" if video else "audio",
                forceplay=forceplay,
            )
            if video:
                await add_active_video_chat(chat_id)
            button = stream_markup(_, chat_id)
            run = await _rich_photo_card(
                original_chat_id,
                config.TELEGRAM_VIDEO_URL if video else config.TELEGRAM_AUDIO_URL,
                InlineKeyboardMarkup(button),
                _["stream_1"].format(link, title[:23], duration_min, user_name),
                title=title[:23],
                duration_min=duration_min,
                user_name=user_name,
                link=link,
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
    elif streamtype == "live":
        link = result["link"]
        vidid = result["vidid"]
        title = (result["title"]).title()
        thumbnail = result["thumb"]
        duration_min = "Live Track"
        status = True if video else None
        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                f"live_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await app.send_message(
                chat_id=original_chat_id,
                text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                reply_markup=InlineKeyboardMarkup(button),
            )
        else:
            if not forceplay:
                db[chat_id] = []
            n, file_path = await YouTube.video(link)
            if n == 0:
                raise AssistantErr(_["str_3"])
            await shree.join_call(
                chat_id,
                original_chat_id,
                file_path,
                video=status,
                image=thumbnail if thumbnail else None,
            )
            await put_queue(
                chat_id,
                original_chat_id,
                f"live_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
                forceplay=forceplay,
            )
            img = await get_thumb(vidid, user_id)
            button = stream_markup(_, chat_id)
            live_link = f"https://t.me/{app.username}?start=info_{vidid}"
            run = await _rich_photo_card(
                original_chat_id,
                img,
                InlineKeyboardMarkup(button),
                _["stream_1"].format(live_link, title[:23], duration_min, user_name),
                title=title[:23],
                duration_min=duration_min,
                user_name=user_name,
                link=live_link,
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
    elif streamtype == "index":
        link = result
        title = "ɪɴᴅᴇx ᴏʀ ᴍ3ᴜ8 ʟɪɴᴋ"
        duration_min = "00:00"
        if await is_active_chat(chat_id):
            await put_queue_index(
                chat_id,
                original_chat_id,
                "index_url",
                title,
                duration_min,
                user_name,
                link,
                "video" if video else "audio",
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await mystic.edit_text(
                text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                reply_markup=InlineKeyboardMarkup(button),
            )
        else:
            if not forceplay:
                db[chat_id] = []
            await shree.join_call(
                chat_id,
                original_chat_id,
                link,
                video=True if video else None,
            )
            await put_queue_index(
                chat_id,
                original_chat_id,
                "index_url",
                title,
                duration_min,
                user_name,
                link,
                "video" if video else "audio",
                forceplay=forceplay,
            )
            button = stream_markup(_, chat_id)
            run = await _rich_photo_card(
                original_chat_id,
                config.STREAM_IMG_URL,
                InlineKeyboardMarkup(button),
                _["stream_2"].format(user_name),
                title=title,
                user_name=user_name,
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
            await mystic.delete()
