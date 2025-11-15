import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import ChatAdminRequired, UserNotParticipant, ChatWriteForbidden
from RishuMusic import app

# --- Configure required channels ---
REQUIRED_CHANNELS = [
    {"id": "vip_robotz", "display_name": "Vip_Robotz"},
    {"id": -1002021738886, "display_name": "Ur_Rishu_143"},
]

CAPTIONS = [
    "๏ ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴀʟʟ ᴛʜᴇ ʀᴇǫᴜɪʀᴇᴅ ᴄʜᴀɴɴᴇʟs ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ.",
    "๏ ᴊᴏɪɴ ᴛʜᴇsᴇ ᴄʜᴀɴɴᴇʟs ғɪʀsᴛ, ᴛʜᴇɴ ᴘʀᴇss ʀᴇғʀᴇsʜ.",
    "๏ ʏᴏᴜ ᴍᴜsᴛ ʙᴇ ᴀ ᴍᴇᴍʙᴇʀ ᴏғ ᴀʟʟ ᴛʜᴇ ᴄʜᴀɴɴᴇʟs ᴛᴏ ᴜsᴇ ᴛʜɪs ʙᴏᴛ.",
]

async def build_channel_buttons(client: Client, user_id: int):
    not_joined = []
    for chan in REQUIRED_CHANNELS:
        chat_id = chan["id"]
        name = chan["display_name"]

        try:
            await client.get_chat_member(chat_id, user_id)
            continue
        except UserNotParticipant:
            link = None
            try:
                link = await client.export_chat_invite_link(chat_id)
            except:
                if isinstance(chat_id, str) and not str(chat_id).startswith("-"):
                    link = f"https://t.me/{chat_id}"
            if link:
                not_joined.append((name, link))
    return not_joined


@app.on_message(filters.private & filters.incoming, group=-1)
async def must_join_channels(client: Client, msg: Message):
    not_joined = await build_channel_buttons(client, msg.from_user.id)

    if not not_joined:
        return  # all good → continue normally

    caption = random.choice(CAPTIONS)
    buttons = [[InlineKeyboardButton(f"• {name} •", url=link)] for name, link in not_joined]
    buttons.append([InlineKeyboardButton("🔄 ʀᴇғʀᴇsʜ", callback_data="refresh_forcejoin")])

    try:
        await msg.reply_text(
            caption,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        await msg.stop_propagation()
    except ChatWriteForbidden:
        pass


@app.on_callback_query(filters.regex("refresh_forcejoin"))
async def refresh_handler(client: Client, query: CallbackQuery):
    not_joined = await build_channel_buttons(client, query.from_user.id)

    if not not_joined:
        await query.message.edit_text("✅ ʏᴏᴜ ʜᴀᴠᴇ ᴊᴏɪɴᴇᴅ ᴀʟʟ ʀᴇǫᴜɪʀᴇᴅ ᴄʜᴀɴɴᴇʟs! ɴᴏᴡ ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ᴛʜᴇ ʙᴏᴛ.")
    else:
        caption = random.choice(CAPTIONS)
        buttons = [[InlineKeyboardButton(f"• {name} •", url=link)] for name, link in not_joined]
        buttons.append([InlineKeyboardButton("🔄 ʀᴇғʀᴇsʜ", callback_data="refresh_forcejoin")])

        await query.message.edit_text(
            caption,
            reply_markup=InlineKeyboardMarkup(buttons),
        )