# ============================================================
# stream.py — v15
# CHANGELOG (v14 -> v15):
#   - FIX callback pills: attribute is data="..." (not callback_data="...") and the
#     two buttons are wrapped in <tg-button-row>, exactly like the richgram README
#     (github.com/Badmunda05/richgram). That wrong attribute was why Telegram
#     answered BUTTON_DATA_INVALID. Url-pill fallback is unchanged.
# CHANGELOG (v13 -> v14):
#   - Rich pills are now CALLBACK buttons (same "DLAUDIO/DLVIDEO <chat_id>" data
#     as the inline row -> in-place download, no DM deep-link needed).
#   - Safety: Telegram rejected type="callback_data" tg-buttons before
#     (BUTTON_DATA_INVALID). So it tries callback pills first; if rejected it
#     remembers (_CB_BAD) and falls back to the url deep-link pills, then to no
#     pills. The rejection error is sent to the Owner DM once.
#   - PILL_MODE = "callback" | "url" to pick the order manually.
# CHANGELOG (v12 -> v13):
#   - "Track Info" is now a big <h1> heading and the table is always visible
#     (no more collapsed dropdown).
#   - Rich pill buttons under the table: "🎵 Audio" / "🎬 Video" (url tg-buttons
#     that deep-link to the bot; handled in dlbuttons.py v3). Premium emojis via
#     render_custom_emojis. Falls back automatically (no pills -> plain table).
#   - Table labels in English with emoji glyphs (🔗 Title, ⏱ Duration, 👤 Requested By).
#   - New vidid param (auto-read from the info link if not passed).
#   - SHOW_KB_DL_ROW flag for the inline-keyboard Audio/Video row.
# CHANGELOG (v11 -> v12):
#   - Play card pe "🎵 Audio / 🎬 Video" download row (_with_dl_row). Rich aur
#     plain fallback dono card me. Handler: plugins/play/dlbuttons.py (new).
#   - Skip/callback cards bhi rich_now_playing se jate hain, to unme bhi aati hai.
# CHANGELOG (v10 -> v11):
#   - FIX RICH_MESSAGE_PHOTO_NO_MEDIA_FOUND: image URL candidates ab chain
#     me try hote hain: direct/temp-upload URL -> normalized YouTube
#     hqdefault.jpg. Photo error aaye to layout variants skip karke seedha
#     next URL. Owner DM error me ab "src=<url>" bhi dikhta hai.
#   - _norm_yt(): ytimg URL (hq720.jpg?sqp=..) -> stable hqdefault.jpg.
# CHANGELOG (v9 -> v10):
#   - rich_now_playing = _rich_photo_card (public alias) so skip / auto-next
#     code (admins skip, callback, core/call.py) can send the same rich card.
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

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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


# v11 NEW: YouTube thumb URL ko stable hqdefault.jpg me normalize karo
# (hq720.jpg?sqp=... query hata dene par aksar 404 -> NO_MEDIA_FOUND).
def _norm_yt(url):
    m = re.search(r"ytimg\.com/vi(?:_webp)?/([\w-]{11})/", str(url or ""))
    if m:
        return f"https://i.ytimg.com/vi/{m.group(1)}/hqdefault.jpg"
    return _rich_src(None, url)


# v13: Audio/Video download buttons are shown in TWO places:
#   1) rich pills inside the card body, under the table (URL deep-links)
#   2) a normal inline-keyboard row under the message (callback, in-place)
# If the rich pills render fine on your client, set this to False to hide row 2.
SHOW_KB_DL_ROW = False


# v13 NEW: rich pill buttons (type="url" is the only tg-button type that works;
# callback_data tg-buttons gave BUTTON_DATA_INVALID). They deep-link to the bot:
#   t.me/<bot>?start=dla_<id>  (audio)   /   t.me/<bot>?start=dlv_<id>  (video)
# and plugins/play/dlbuttons.py answers that /start payload in the user's DM.
def _pill(text: str, url: str, style: str) -> str:
    return (
        f'<tg-button type="url" style="{style}" '
        f'url="{_html_escape(url, quote=True)}">{text}</tg-button>'
    )


def _dl_pills(vidid, chat=None, mode="url") -> str:
    """mode="callback": in-place download (same handler as the inline row).
    mode="url": deep-link to the bot's DM (always accepted by Telegram)."""
    uname = getattr(app, "username", None)
    if not vidid:
        return ""
    if mode == "callback":
        if not chat:
            return ""
        return (
            "<tg-button-row>"
            + _pill_cb("🎵 Audio", f"DLAUDIO {chat}", "primary")
            + _pill_cb("🎬 Video", f"DLVIDEO {chat}", "success")
            + "</tg-button-row>"
        )
    if not uname:
        return ""
    return (
        "<p>"
        + _pill("🎵 Audio", f"https://t.me/{uname}?start=dla_{vidid}", "primary")
        + " "
        + _pill("🎬 Video", f"https://t.me/{uname}?start=dlv_{vidid}", "success")
        + "</p>"
    )


# v14 NEW: callback-type rich pill. Same callback data as the inline row
# ("DLAUDIO <chat_id>" / "DLVIDEO <chat_id>"), so dlbuttons.py needs no change.
# FIX (v15): the attribute is data="..." (richgram README), NOT callback_data="...".
# The wrong name was the cause of the old BUTTON_DATA_INVALID. Still safe: if Telegram
# rejects it anyway, the card falls back to url pills automatically.
def _pill_cb(text: str, data: str, style: str) -> str:
    return (
        f'<tg-button type="callback_data" style="{style}" '
        f'data="{_html_escape(data, quote=True)}">{text}</tg-button>'
    )


# "callback" = try callback pills first, then url pills. "url" = url pills only.
PILL_MODE = "callback"
_CB_BAD = False  # set True after Telegram rejects callback pills (stops retrying)


def _chat_key(markup):
    """voice-chat id (db key) from the stream_markup's "ADMIN <cmd>|<chat_id>" buttons."""
    try:
        for r in markup.inline_keyboard:
            for b in r:
                d = getattr(b, "callback_data", None)
                if isinstance(d, bytes):
                    d = d.decode("utf-8", "ignore")
                if isinstance(d, str) and d.startswith("ADMIN") and "|" in d:
                    return d.split("|", 1)[1].split("_")[0].strip()
    except Exception:
        pass
    return None


# v12 NEW: play card ke neeche "Audio / Video" download row.
# chat_id (db key) existing stream_markup ke "ADMIN <cmd>|<chat_id>" button se nikalte
# hain, isliye cplay (channel) me bhi sahi key milti hai.
def _with_dl_row(markup):
    if not SHOW_KB_DL_ROW:
        return markup
    try:
        rows = [list(r) for r in markup.inline_keyboard]
        chat = None
        for r in rows:
            for b in r:
                d = getattr(b, "callback_data", None)
                if isinstance(d, bytes):
                    d = d.decode("utf-8", "ignore")
                if isinstance(d, str) and d.startswith("DL"):
                    return markup  # already added
                if chat is None and isinstance(d, str) and d.startswith("ADMIN") and "|" in d:
                    chat = d.split("|", 1)[1].split("_")[0].strip()
        if not chat:
            return markup
        rows.append(
            [
                InlineKeyboardButton("🎵 Audio", callback_data=f"DLAUDIO {chat}"),
                InlineKeyboardButton("🎬 Video", callback_data=f"DLVIDEO {chat}"),
            ]
        )
        return InlineKeyboardMarkup(rows)
    except Exception:
        return markup


async def _rich_photo_card(
    chat_id, img, markup, plain_cap, *, title=None, duration_min=None,
    user_name=None, link=None, extra_rows=None, rich_img_url=None, vidid=None,
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
    global _CB_BAD
    markup = _with_dl_row(markup)  # v12
    if not vidid:  # v13: YouTube cards always carry ...?start=info_<id> as link
        _m = re.search(r"start=info_([\w-]{11})", str(link or ""))
        vidid = _m.group(1) if _m else None
    # v11: ek se zyada image URL candidates (label, url); jo Telegram accept kare
    srcs = []
    if RICH_AVAILABLE and title is not None:
        direct = _rich_src(img, None)
        if direct:
            srcs.append(("direct", direct))
        else:
            up = await _temp_public_url(img)
            if up:
                srcs.append(("upload", up))
        yt = _norm_yt(rich_img_url)
        if yt and yt not in [u for _l, u in srcs]:
            srcs.append(("yt", yt))
    if not RICH_AVAILABLE:
        await _report_rich_error("stream._rich_photo_card", "import", "RICH_AVAILABLE is False (rich_ui import/support issue)")
    elif title is not None and not srcs:
        await _report_rich_error("stream._rich_photo_card", "no-url", f"no public image URL for: {img}")
    elif title is not None:
        rows = []
        title_cell = rich_esc(title)
        if link:
            title_cell = f'<a href="{rich_esc(link)}">{title_cell}</a>'
        rows.append(("🔗 Title", title_cell))
        if duration_min is not None:
            rows.append(("⏱ Duration", f"{rich_esc(duration_min)} min"))
        if user_name is not None:
            rows.append(("👤 Requested By", f"<b>{rich_esc(_plain_name(user_name))}</b>"))
        if extra_rows:
            rows.extend(extra_rows)
        table = rich_kv_table(rows)
        for label, src in srcs:
            head = rich_img(src) + "\n<b>❖ Mᴜsɪᴄ Oɴ Sᴛʀᴇᴀᴍɪɴɢ ⏤●</b>\n"
            # v13: big "Track Info" heading, table always visible, pills under it
            core = head + "<h1>🎵 Track Info</h1>" + table
            chat_key = _chat_key(markup)
            cb_pills = (
                _dl_pills(vidid, chat_key, "callback")
                if PILL_MODE == "callback" and not _CB_BAD
                else ""
            )
            url_pills = _dl_pills(vidid, chat_key, "url")
            attempts = []
            if cb_pills:
                attempts.append(("cb-pills+emoji-render", render_custom_emojis(core + cb_pills)))
                attempts.append(("cb-pills-no-render", core + cb_pills))
            if url_pills:
                attempts.append(("url-pills+emoji-render", render_custom_emojis(core + url_pills)))
                attempts.append(("url-pills-no-render", core + url_pills))
            attempts.append(("heading+emoji-render", render_custom_emojis(core)))
            attempts.append(("plain-table", render_custom_emojis(head + table)))
            for name, body in attempts:
                if _CB_BAD and name.startswith("cb-"):
                    continue
                try:
                    return await app.send_rich_message(
                        chat_id=chat_id,
                        rich_message=_input_rich(body),
                        reply_markup=markup,
                    )
                except Exception as ex:
                    traceback.print_exc()
                    # v14: Telegram rejected callback pills -> stop trying them
                    if name.startswith("cb-") and "BUTTON" in str(ex).upper():
                        _CB_BAD = True
                    # v11: error me image URL bhi (label se dedupe, URL text me)
                    await _report_rich_error(
                        "stream._rich_photo_card",
                        f"{name}|{label}",
                        f"{type(ex).__name__}: {ex} | src={src}",
                    )
                    if "RICH_MESSAGE_PHOTO" in str(ex):
                        break  # image ka issue hai, layout ka nahi -> next URL
    return await app.send_photo(
        chat_id,
        photo=img,
        caption=render_custom_emojis(plain_cap),
        reply_markup=markup,
    )


# v10 NEW: public name, skip/auto-next files isse import karke use karein
rich_now_playing = _rich_photo_card

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
