# ============================================================
# RishuMusic/plugins/play/dlbuttons.py — v5
#
# CHANGELOG (v3 -> v5):
#   - NEW: "APTOGGLE <chat_id>" callback = the Autoplay ON/OFF button that replaced
#     YT-API on the play card. Admins only (same rule as Pause/Skip). It flips the
#     repo's own autoplay state (utils/autoplay is_on/set_on), exactly like
#     /autoplay on|off, and refreshes the keyboard right away.
# CHANGELOG (v2 -> v3):
#   - All user-facing text is now plain English (no Hinglish).
#   - NEW: /start deep-link handler for the rich pill buttons under the table:
#         t.me/<bot>?start=dla_<video_id>   -> audio to the user's DM
#         t.me/<bot>?start=dlv_<video_id>   -> video to the user's DM
#     (runs in handler group -1 and stops propagation, so start.py is untouched)
#   - Shared _deliver() used by both the inline-keyboard callbacks and the
#     deep-link, so behaviour is identical.
# CHANGELOG (v1 -> v2):
#   - Download via your API:
#       GET https://vapters.site/stream/<id>?vid=false&quality=192  (mp3 bytes)
#     with YouTube.download() as fallback.
#   - VIDEO_PARAMS is ASSUMED (vid=true&quality=720) - change it if your
#     API uses a different video format.
#
# Callback data (inline keyboard row): "DLAUDIO <chat_id>" / "DLVIDEO <chat_id>"
# The track that is currently playing (db[chat_id][0]) is the one downloaded.
# ============================================================

import asyncio
import os
import re
import time
from html import escape

from pyrogram import filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from RishuMusic import YouTube, app
from RishuMusic.misc import SUDOERS, db
from RishuMusic.utils.database import is_active_chat, is_nonadmin_chat
from RishuMusic.utils.play_buttons import decorate_markup, is_autoplay_on, set_autoplay
from config import BANNED_USERS, adminlist

try:
    from RishuMusic.utils import time_to_seconds
except Exception:  # pragma: no cover
    time_to_seconds = None

# ---- download API ----
API_BASE = "https://vapters.site/stream"
AUDIO_PARAMS = {"vid": "false", "quality": "192"}
VIDEO_PARAMS = {"vid": "true", "quality": "720"}  # ASSUMED - confirm with your API
DL_DIR = "downloads"
MAX_BYTES = 500 * 1024 * 1024
API_TIMEOUT = 180  # seconds

COOLDOWN = 30  # seconds, per user per type
_last = {}  # (user_id, kind) -> last click time
_busy = set()  # (user_id, vidid, kind) currently downloading
_YT_ID = re.compile(r"^[\w-]{11}$")
_BLOCKED = ("UserIsBlocked", "PeerIdInvalid", "InputUserDeactivated")


# ------------------------------------------------------------
# helpers
# ------------------------------------------------------------
def _secs(dur):
    try:
        return int(time_to_seconds(dur)) if time_to_seconds else None
    except Exception:
        return None


def _rm(*paths):
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass


async def _api_download(vidid: str, is_video: bool) -> str:
    """Download from the API into a temp file. Returns the path, raises on failure."""
    import aiohttp

    os.makedirs(DL_DIR, exist_ok=True)
    ext = "mp4" if is_video else "mp3"
    path = os.path.join(DL_DIR, f"dl_{vidid}_{int(time.time())}.{ext}")
    params = VIDEO_PARAMS if is_video else AUDIO_PARAMS
    timeout = aiohttp.ClientTimeout(total=API_TIMEOUT, sock_connect=15)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(
                f"{API_BASE}/{vidid}", params=params, allow_redirects=True
            ) as r:
                ctype = (r.headers.get("Content-Type") or "").lower()
                if r.status != 200:
                    raise RuntimeError(f"API HTTP {r.status}")
                if not (
                    ctype.startswith("audio/")
                    or ctype.startswith("video/")
                    or "octet-stream" in ctype
                ):
                    body = (await r.text())[:150]
                    raise RuntimeError(f"API returned no media ({ctype}): {body}")
                size = 0
                with open(path, "wb") as f:
                    async for chunk in r.content.iter_chunked(1024 * 256):
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise RuntimeError("file too large (over 500MB)")
                        f.write(chunk)
        if size == 0:
            raise RuntimeError("API returned an empty file")
        return path
    except Exception:
        _rm(path)
        raise


async def _fetch_thumb(vidid: str):
    """Best-effort thumbnail for send_audio / send_video. None on failure."""
    try:
        import aiohttp

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as sess:
            async with sess.get(f"https://i.ytimg.com/vi/{vidid}/hqdefault.jpg") as r:
                if r.status != 200:
                    return None
                data = await r.read()
        os.makedirs(DL_DIR, exist_ok=True)
        path = os.path.join(DL_DIR, f"th_{vidid}_{int(time.time())}.jpg")
        with open(path, "wb") as f:
            f.write(data)
        return path
    except Exception:
        return None


async def _deliver(user, status: Message, vidid, is_video, title, dur, in_group):
    """Download the track and send it to `user`'s DM. Edits `status` with the
    outcome. Returns True if the file was sent."""
    label = "video" if is_video else "audio"
    mention = user.mention
    uid = user.id
    file_path = None
    thumb = None
    is_temp = False
    try:
        # 1) your API, 2) fallback: YouTube.download()
        try:
            file_path = await _api_download(vidid, is_video)
            is_temp = True
        except Exception as api_ex:
            try:
                file_path, _direct = await YouTube.download(
                    vidid, status, videoid=True, video=True if is_video else None
                )
            except Exception as ex:
                await status.edit_text(
                    "❌ Download failed.\n"
                    f"API: <code>{escape(str(api_ex)[:150])}</code>\n"
                    f"Fallback: <code>{escape(str(ex)[:150])}</code>"
                )
                return False
        if not file_path:
            await status.edit_text("❌ Download failed: no file was returned.")
            return False

        cap = (
            f"❖ <b>Title :</b> <a href=\"https://youtu.be/{vidid}\">{escape(title)}</a>\n"
            f"⏱ <b>Duration :</b> {escape(str(dur))}\n"
            f"👤 <b>Requested by :</b> {mention}"
        )
        seconds = _secs(dur) or 0
        thumb = await _fetch_thumb(vidid)

        err = None
        try:
            if is_video:
                await app.send_video(
                    uid,
                    video=file_path,
                    caption=cap,
                    duration=seconds,
                    thumb=thumb,
                    supports_streaming=True,
                )
            else:
                try:
                    await app.send_audio(
                        uid,
                        audio=file_path,
                        caption=cap,
                        title=title,
                        duration=seconds,
                        thumb=thumb,
                    )
                except Exception as ex_a:
                    if type(ex_a).__name__ in _BLOCKED:
                        raise
                    # formats send_audio refuses (webm/m4a) go as a document
                    await app.send_document(uid, document=file_path, caption=cap)
        except Exception as ex:
            err = ex

        if err is None:
            if in_group:
                await status.edit_text(
                    f"✅ <b>{mention}</b> — your {label} was sent to your DM.",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("📩 Open DM", url=f"https://t.me/{app.username}")]]
                    ),
                )
                await asyncio.sleep(10)
                try:
                    await status.delete()
                except Exception:
                    pass
            else:
                await status.edit_text(f"✅ Done! Your {label} is above. Enjoy 🎶")
            return True

        name = type(err).__name__
        if name in _BLOCKED:
            await status.edit_text(
                f"❌ <b>{mention}</b> — please start / unblock me in DM first, then tap again 👇",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("👉 Start / Unblock", url=f"https://t.me/{app.username}?start=info_{vidid}")]]
                ),
            )
        else:
            await status.edit_text(
                f"❌ Could not send the file: <code>{escape(name)}: {escape(str(err)[:150])}</code>"
            )
        return False
    finally:
        _rm(thumb, file_path if is_temp else None)


# ------------------------------------------------------------
# 1) inline-keyboard buttons (in the group)
# ------------------------------------------------------------
@app.on_callback_query(filters.regex(r"^DL(AUDIO|VIDEO) ") & ~BANNED_USERS)
async def dl_current(client, cq: CallbackQuery):
    kind, chat = cq.data.strip().split(None, 1)
    is_video = kind == "DLVIDEO"
    label = "video" if is_video else "audio"

    try:
        chat_id = int(chat)
    except ValueError:
        return await cq.answer("Invalid button.", show_alert=True)

    playing = db.get(chat_id)
    if not playing:
        return await cq.answer("Nothing is playing right now.", show_alert=True)

    cur = playing[0]
    vidid = str(cur.get("vidid") or "")
    queued = str(cur.get("file") or "")
    if "live_" in queued or not _YT_ID.match(vidid):
        return await cq.answer(
            "This track can't be downloaded (live stream / Telegram file / link).",
            show_alert=True,
        )

    uid = cq.from_user.id
    now = time.time()
    if now - _last.get((uid, kind), 0) < COOLDOWN:
        return await cq.answer(
            f"You already requested a {label}. Please wait {COOLDOWN}s and check your DM.",
            show_alert=True,
        )
    key = (uid, vidid, kind)
    if key in _busy:
        return await cq.answer("Already downloading...", show_alert=False)
    _last[(uid, kind)] = now
    _busy.add(key)

    sent = False
    try:
        title = str(cur.get("title") or "Unknown").title()
        await cq.answer(f"⏳ Downloading {label}, check your DM...")
        status = await cq.message.reply_text(
            f"⏳ <b>{cq.from_user.mention}</b> — downloading {label}, please wait..."
        )
        sent = await _deliver(cq.from_user, status, vidid, is_video, title, cur.get("dur"), True)
    finally:
        _busy.discard(key)
        if not sent:  # failed -> no cooldown, the user can retry right away
            _last.pop((uid, kind), None)


# ------------------------------------------------------------
# 2) /start deep-link from the rich pill buttons (in the user's DM)
#    t.me/<bot>?start=dla_<id> (audio)  /  dlv_<id> (video)
# ------------------------------------------------------------
_DEEP = re.compile(r"^/start(?:@\w+)?\s+dl([av])_([\w-]{11})\s*$")


@app.on_message(filters.private & filters.regex(_DEEP) & ~BANNED_USERS, group=-1)
async def dl_deeplink(client, message: Message):
    try:
        m = _DEEP.match(message.text.strip())
        if m and message.from_user:
            await _handle_deeplink(message, m.group(1) == "v", m.group(2))
    finally:
        # always stop here so start.py doesn't also answer this /start
        message.stop_propagation()


async def _handle_deeplink(message: Message, is_video: bool, vidid: str):
    user = message.from_user
    uid = user.id
    kind = "DLVIDEO" if is_video else "DLAUDIO"
    label = "video" if is_video else "audio"

    now = time.time()
    if now - _last.get((uid, kind), 0) < COOLDOWN:
        return await message.reply_text(
            f"⏳ Please wait {COOLDOWN}s before requesting another {label}."
        )
    key = (uid, vidid, kind)
    if key in _busy:
        return await message.reply_text("⏳ Already downloading, please wait...")
    _last[(uid, kind)] = now
    _busy.add(key)

    sent = False
    try:
        try:
            title, dur, _s, _t, _v = await YouTube.details(vidid, True)
        except Exception:
            title, dur = "Unknown", None
        if str(dur) == "None":
            return await message.reply_text("❌ Live streams can't be downloaded.")
        status = await message.reply_text(f"⏳ Downloading {label}, please wait...")
        sent = await _deliver(user, status, vidid, is_video, str(title).title(), dur, False)
    finally:
        _busy.discard(key)
        if not sent:
            _last.pop((uid, kind), None)


# ------------------------------------------------------------
# 3) Autoplay ON / OFF toggle (replaces the old YT-API button)
# ------------------------------------------------------------
@app.on_callback_query(filters.regex(r"^APTOGGLE ") & ~BANNED_USERS)
async def ap_toggle(client, cq: CallbackQuery):
    try:
        chat_id = int(cq.data.strip().split(None, 1)[1])
    except (IndexError, ValueError):
        return await cq.answer("Invalid button.", show_alert=True)

    if not await is_active_chat(chat_id):
        return await cq.answer("Nothing is playing right now.", show_alert=True)

    # same permission rule as the other player buttons (callback.py)
    if not await is_nonadmin_chat(cq.message.chat.id):
        if cq.from_user.id not in SUDOERS:
            admins = adminlist.get(cq.message.chat.id)
            if not admins or cq.from_user.id not in admins:
                return await cq.answer("Only admins can change autoplay.", show_alert=True)

    new_state = not is_autoplay_on(chat_id)
    set_autoplay(chat_id, new_state)
    await cq.answer(
        "Autoplay is now ON ✅ — related songs will play after the queue ends."
        if new_state
        else "Autoplay is now OFF ⛔ — playback stops when the queue ends.",
        show_alert=True,
    )
    try:  # refresh the keyboard right away (the 7s timer would do it anyway)
        await cq.edit_message_reply_markup(
            reply_markup=await decorate_markup(cq.message.reply_markup, chat_id)
        )
    except Exception:
        pass
