# ============================================================
# skip.py — v3   (v1 = your original file)
# CHANGELOG (v1 -> v2):
#   - Skip ke baad "Now Streaming" card ab rich card (thumbnail + dropdown
#     table) hai, /play jaisa. Pehle message.reply_photo se plain caption
#     aa raha tha, isliye "normal" dikhta tha.
#   - Naya _card() helper -> stream.py ka rich_now_playing() call karta hai
#     (rich fail ho to wo khud plain photo caption pe fallback karta hai).
#   - Saare reply_photo(stream_1 / stream_2) calls _card() se replace
#     (marked "# v2" neeche). Baaki logic same.
# ============================================================

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, Message

import config
from RishuMusic import YouTube, app
from RishuMusic.core.call import shree
from RishuMusic.misc import db
from RishuMusic.utils.autoplay import enqueue_next as autoplay_next  # autoplay v3
from RishuMusic.utils.database import get_loop
from RishuMusic.utils.decorators import AdminRightsCheck
from RishuMusic.utils.inline import close_markup, stream_markup
from RishuMusic.utils.stream.stream import rich_now_playing  # v2 NEW
from RishuMusic.utils.thumbnails import get_thumb
from config import BANNED_USERS,autoclean


# v2 NEW
def _yt_thumb(videoid):
    return f"https://i.ytimg.com/vi/{videoid}/hqdefault.jpg"


# v2 NEW
async def _card(chat_id, img, button, _, title, dur, user, link,
                plain_cap=None, rich_img_url=None, streamtype=None):
    cap = plain_cap or _["stream_1"].format(link, title[:23], dur, user)
    return await rich_now_playing(
        chat_id,
        img,
        InlineKeyboardMarkup(button),
        cap,
        title=title[:23],
        duration_min=dur,
        user_name=user,
        link=link,
        rich_img_url=rich_img_url,
        # v: Mode row (Video when a video is streaming in the VC, else Audio)
        extra_rows=[("🎧 Mode", "Video" if str(streamtype) == "video" else "Audio")],
    )


@app.on_message(
    filters.command(["skip", "cskip", "next", "cnext"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def skip(cli, message: Message, _, chat_id):
    if not len(message.command) < 2:
        loop = await get_loop(chat_id)
        if loop != 0:
            return await message.reply_text(_["admin_8"])
        state = message.text.split(None, 1)[1].strip()
        if state.isnumeric():
            state = int(state)
            check = db.get(chat_id)
            if check:
                count = len(check)
                if count > 2:
                    count = int(count - 1)
                    if 1 <= state <= count:
                        for x in range(state):
                            popped = None
                            try:
                                popped = check.pop(0)
                            except:
                                return await message.reply_text(_["admin_12"])
                            if popped:
                                rem = popped["file"]
                                autoclean.remove(rem)
                            if not check:
                                try:
                                    await message.reply_text(
                                        text=_["admin_6"].format(
                                            message.from_user.mention,
                                            message.chat.title,
                                        ),
                                        reply_markup=close_markup(_),
                                    )
                                    await shree.stop_stream(chat_id)
                                except:
                                    return
                                break
                    else:
                        return await message.reply_text(_["admin_11"].format(count))
                else:
                    return await message.reply_text(_["admin_10"])
            else:
                return await message.reply_text(_["queue_2"])
        else:
            return await message.reply_text(_["admin_9"])
    else:
        check = db.get(chat_id)
        popped = None
        try:
            popped = check.pop(0)
            if popped:
                rem = popped["file"]
                autoclean.remove(rem)
            if not check:  # autoplay v3
                await autoplay_next(chat_id, message.chat.id)
            if not check:
                await message.reply_text(
                    text=_["admin_6"].format(
                        message.from_user.mention, message.chat.title
                    ),
                    reply_markup=close_markup(_),
                )
                try:
                    return await shree.stop_stream(chat_id)
                except:
                    return
        except:
            try:
                await message.reply_text(
                    text=_["admin_6"].format(
                        message.from_user.mention, message.chat.title
                    ),
                    reply_markup=close_markup(_),
                )
                return await shree.stop_stream(chat_id)
            except:
                return
    queued = check[0]["file"]
    title = (check[0]["title"]).title()
    user = check[0]["by"]
    user_id = check[0]["user_id"]
    streamtype = check[0]["streamtype"]
    videoid = check[0]["vidid"]
    status = True if str(streamtype) == "video" else None
    db[chat_id][0]["played"] = 0
    exis = (check[0]).get("old_dur")
    if exis:
        db[chat_id][0]["dur"] = exis
        db[chat_id][0]["seconds"] = check[0]["old_second"]
        db[chat_id][0]["speed_path"] = None
        db[chat_id][0]["speed"] = 1.0
    if "live_" in queued:
        n, link = await YouTube.video(videoid, True)
        if n == 0:
            return await message.reply_text(_["admin_7"].format(title))
        try:
            image = await YouTube.thumbnail(videoid, True)
        except:
            image = None
        try:
            await shree.skip_stream(chat_id, link, video=status, image=image)
        except:
            return await message.reply_text(_["call_6"])
        button = stream_markup(_, chat_id)
        img = await get_thumb(videoid,user_id)
        # v2: reply_photo -> _card (rich)
        run = await _card(
            message.chat.id, img, button, _, title, check[0]["dur"], user,
            f"https://t.me/{app.username}?start=info_{videoid}",
            rich_img_url=_yt_thumb(videoid),
            streamtype=streamtype,
        )
        db[chat_id][0]["mystic"] = run
        db[chat_id][0]["markup"] = "tg"
    elif "vid_" in queued:
        mystic = await message.reply_text(_["call_7"], disable_web_page_preview=True)
        try:
            file_path, direct = await YouTube.download(
                videoid,
                mystic,
                videoid=True,
                video=status,
            )
        except:
            return await mystic.edit_text(_["call_6"])
        try:
            image = await YouTube.thumbnail(videoid, True)
        except:
            image = None
        try:
            await shree.skip_stream(chat_id, file_path, video=status, image=image)
        except:
            return await mystic.edit_text(_["call_6"])
        button = stream_markup(_, chat_id)
        img = await get_thumb(videoid,user_id)
        # v2: reply_photo -> _card (rich)
        run = await _card(
            message.chat.id, img, button, _, title, check[0]["dur"], user,
            f"https://t.me/{app.username}?start=info_{videoid}",
            rich_img_url=_yt_thumb(videoid),
            streamtype=streamtype,
        )
        db[chat_id][0]["mystic"] = run
        db[chat_id][0]["markup"] = "stream"
        await mystic.delete()
    elif "index_" in queued:
        try:
            await shree.skip_stream(chat_id, videoid, video=status)
        except:
            return await message.reply_text(_["call_6"])
        button = stream_markup(_, chat_id)
        # v2: reply_photo -> _card (rich)
        run = await _card(
            message.chat.id, config.STREAM_IMG_URL, button, _,
            "ɪɴᴅᴇx ᴏʀ ᴍ3ᴜ8 ʟɪɴᴋ", None, user, None,
            plain_cap=_["stream_2"].format(user),
            streamtype=streamtype,
        )
        db[chat_id][0]["mystic"] = run
        db[chat_id][0]["markup"] = "tg"
    else:
        if videoid == "telegram":
            image = None
        elif videoid == "soundcloud":
            image = None
        else:
            try:
                image = await YouTube.thumbnail(videoid, True)
            except:
                image = None
        try:
            await shree.skip_stream(chat_id, queued, video=status, image=image)
        except:
            return await message.reply_text(_["call_6"])
        if videoid == "telegram":
            button = stream_markup(_, chat_id)
            # v2: reply_photo -> _card (rich)
            run = await _card(
                message.chat.id,
                config.TELEGRAM_AUDIO_URL
                if str(streamtype) == "audio"
                else config.TELEGRAM_VIDEO_URL,
                button, _, title, check[0]["dur"], user, config.SUPPORT_CHAT,
                streamtype=streamtype,
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
        elif videoid == "soundcloud":
            button = stream_markup(_, chat_id)
            # v2: reply_photo -> _card (rich)
            run = await _card(
                message.chat.id,
                config.SOUNCLOUD_IMG_URL
                if str(streamtype) == "audio"
                else config.TELEGRAM_VIDEO_URL,
                button, _, title, check[0]["dur"], user, config.SUPPORT_CHAT,
                streamtype=streamtype,
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
        else:
            button = stream_markup(_, chat_id)
            img = await get_thumb(videoid,user_id)
            # v2: reply_photo -> _card (rich)
            run = await _card(
                message.chat.id, img, button, _, title, check[0]["dur"], user,
                f"https://t.me/{app.username}?start=info_{videoid}",
                rich_img_url=_yt_thumb(videoid),
                streamtype=streamtype,
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "stream"
