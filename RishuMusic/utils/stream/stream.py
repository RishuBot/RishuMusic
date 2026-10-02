# ============================================================
# stream.py — v9
# CHANGELOG (v8 -> v9):
#   - v8 (clickable mention attempt) REMOVED, back to bold plain name.
#   - Upload fix: litterbox gave HTTP 500. Now tries litterbox -> catbox
#     (permanent) -> uguu, with User-Agent + proper content-type, 8s timeout
#     per host. One combined error to Owner DM only if ALL hosts fail.
# CHANGELOG (v7 -> v8) [reverted in v9]:
#   - Clickable mention: pehle attempt "mention-link" (<a href="tg://user?id=..">)
#     bold naam ke saath; Telegram reject kare to purane attempts (plain bold
#     naam) chalte hain. Reject error Owner DM me aayega.
# CHANGELOG (v6 -> v7):
#   - Requested-by mention fix: _plain_name() strips the raw <a href=tg://..>
#     tag, shows bold plain name (no more literal HTML in the table).
#   - _temp_public_url(): local get_thumb() image is uploaded to litterbox
#     (temp host, TEMP_TIME=72h) so the rich card shows YOUR generated thumb.
#     Order: http img -> temp upload -> YouTube thumb URL. Needs aiohttp.
# CHANGELOG (v5 -> v6):
#   - FIX RICH_MESSAGE_PHOTO_URL_INVALID: get_thumb() returns a LOCAL file,
#     rich <img> needs a public URL. New _rich_src() + rich_img_url param;
#     youtube/live/playlist cards pass the YouTube thumbnail URL.
#     (Rich card me custom generated thumb nahi, YouTube thumb dikhega;
#     fallback photo card me purana generated thumb hi rehta hai.)
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
import re
import traceback
from html import escape as _html_escape
from html import unescape as _html_unescape
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


# v9: multi-host temp upload. Order: litterbox (temp, TEMP_TIME) -> catbox
# (permanent, reliable) -> uguu (temp ~3h). Pehla jo chal jaye wahi use hota hai.
# TEMP_TIME: "1h" / "12h" / "24h" / "72h"
TEMP_TIME = "72h"
_upload_cache = {}
_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) RishuMusic/1.0"}


async def _upload_to(sess, host, blob, fname, ctype):
    """Returns (url_or_None, note)."""
    import aiohttp

    form = aiohttp.FormData()
    if host == "litterbox":
        form.add_field("reqtype", "fileupload")
        form.add_field("time", TEMP_TIME)
        form.add_field("fileToUpload", blob, filename=fname, content_type=ctype)
        target = "https://litterbox.catbox.moe/resources/internals/api.php"
    elif host == "catbox":
        form.add_field("reqtype", "fileupload")
        form.add_field("fileToUpload", blob, filename=fname, content_type=ctype)
        target = "https://catbox.moe/user/api.php"
    else:  # uguu
        form.add_field("files[]", blob, filename=fname, content_type=ctype)
        target = "https://uguu.se/upload?output=text"
    async with sess.post(target, data=form) as r:
        txt = (await r.text()).strip()
        if r.status == 200 and txt.startswith("https://"):
            return txt.split()[0], "ok"
        return None, f"HTTP {r.status}: {txt[:80]!r}"


async def _temp_public_url(path):
    """Local thumb file -> public https URL. None if every host fails."""
    path = str(path or "")
    if not path or path.startswith(("http://", "https://")) or not os.path.isfile(path):
        return None
    if path in _upload_cache:
        return _upload_cache[path]
    notes = []
    try:
        import aiohttp

        with open(path, "rb") as f:
            blob = f.read()
        fname = os.path.basename(path)
        ctype = "image/png" if fname.lower().endswith(".png") else "image/jpeg"
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(timeout=timeout, headers=_UA) as sess:
            for host in ("litterbox", "catbox", "uguu"):
                try:
                    url, note = await _upload_to(sess, host, blob, fname, ctype)
                except Exception as ex:
                    url, note = None, f"{type(ex).__name__}: {ex}"
                if url:
                    if len(_upload_cache) > 200:
                        _upload_cache.clear()
                    _upload_cache[path] = url
                    return url
                notes.append(f"{host}: {note}")
    except Exception as ex:
        notes.append(f"setup: {type(ex).__name__}: {ex}")
    await _report_rich_error("stream._temp_public_url", "all-hosts-failed", " | ".join(notes))
    return None


# v7 NEW: user_name aksar pyrogram .mention hota hai (<a href="tg://...">Naam</a>),
# rich body me wo literal text dikhta tha. Tags hata ke plain naam.
def _plain_name(user_name) -> str:
    name = _html_unescape(re.sub(r"<[^>]+>", "", str(user_name or ""))).strip()
    return name or "User"


# v6 NEW: rich <img> ko public http(s) URL chahiye (local cache path =
# RICH_MESSAGE_PHOTO_URL_INVALID). img URL ho to wahi, warna rich_img_url.
def _rich_src(img, rich_img_url=None):
    for cand in (img, rich_img_url):
        c = str(cand or "")
        if c.startswith(("http://", "https://")):
            return c.split("?")[0]
    return None


async def _rich_photo_card(
    chat_id, img, markup, plain_cap, *, title=None, duration_min=None,
    user_name=None, link=None, extra_rows=None, rich_img_url=None,
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
    rich_src = None
    if RICH_AVAILABLE and title is not None:
        # v7: http URL -> local thumb temp-upload -> YouTube thumb URL
        rich_src = (
            _rich_src(img, None)
            or await _temp_public_url(img)
            or _rich_src(None, rich_img_url)
        )
    if not RICH_AVAILABLE:
        await _report_rich_error("stream._rich_photo_card", "import", "RICH_AVAILABLE is False (rich_ui import/support issue)")
    elif title is not None and not rich_src:
        await _report_rich_error("stream._rich_photo_card", "no-url", f"no public image URL for: {img}")
    elif title is not None:
        rows = []
        title_cell = rich_esc(title)
        if link:
            title_cell = f'<a href="{rich_esc(link)}">{title_cell}</a>'
        rows.append(("ᴛɪᴛʟᴇ", title_cell))
        if duration_min is not None:
            rows.append(("ᴅᴜʀᴀᴛɪᴏɴ", f"{rich_esc(duration_min)} ᴍɪɴᴜᴛᴇs"))
        if user_name is not None:
            rows.append(("ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ", f"<b>{rich_esc(_plain_name(user_name))}</b>"))
        if extra_rows:
            rows.extend(extra_rows)
        table = rich_kv_table(rows)
        head = rich_img(rich_src) + "\n<b>❖ Mᴜsɪᴄ Oɴ Sᴛʀᴇᴀᴍɪɴɢ ⏤●</b>\n"
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
                    rich_img_url=thumbnail,
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
                rich_img_url=thumbnail,
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
                rich_img_url=thumbnail,
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
