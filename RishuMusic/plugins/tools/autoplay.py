# autoplay v1 (NEW) - /autoplay on|off
from pyrogram import filters
from RishuMusic import app
from RishuMusic.misc import db
from RishuMusic.utils import autoplay
from RishuMusic.utils.decorators import AdminRightsCheck   # path adjust karo
from config import BANNED_USERS


@app.on_message(filters.command(["autoplay"]) & filters.group & ~BANNED_USERS)
@AdminRightsCheck
async def autoplay_cmd(cli, message, _, chat_id):
    arg = message.command[1].lower() if len(message.command) > 1 else ""
    if arg not in ("on", "off"):
        state = "ON ✅" if autoplay.is_on(chat_id) else "OFF ❌"
        return await message.reply_text(f"Autoplay: {state}\nUse: /autoplay on | off")
    if arg == "off":
        autoplay.set_on(chat_id, False)
        return await message.reply_text("Autoplay OFF ❌")
    ref = None
    q = db.get(chat_id)
    if q:
        ref = (q[-1].get("vidid"), q[-1].get("title"))
    autoplay.set_on(chat_id, True, ref)
    await message.reply_text("Autoplay ON ✅\nSongs related to current track auto-play.")
