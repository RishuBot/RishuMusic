from pyrogram.types import InlineKeyboardButton
from pyrogram.enums import ButtonStyle
import config
from RishuMusic import app


def start_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"], url=f"https://t.me/{app.username}?startgroup=true&admin=invite_users+delete_messages+manage_video_chats+pin_messages+manage_chat+ban_users+manage_topics+change_info",icon_custom_emoji_id=6066395745139824604,
                style=ButtonStyle.PRIMARY,
            )],
             [
            InlineKeyboardButton(
                text=_["S_B_2"], url=config.SUPPORT_CHAT
            ,icon_custom_emoji_id=5409194306365829029,
                style=ButtonStyle.PRIMARY,)
        ],
    ]
    return buttons


def private_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_3"],
                url=f"https://t.me/{app.username}?startgroup=true&admin=invite_users+delete_messages+manage_video_chats+pin_messages+manage_chat+ban_users+manage_topics+change_info",icon_custom_emoji_id=5409194306365829029,
                style=ButtonStyle.PRIMARY,
            )
        ],
        [
            InlineKeyboardButton(
                text="ᴜᴘᴅᴀᴛᴇ", callback_data="Khushi",icon_custom_emoji_id=6001440193058444284,
                style=ButtonStyle.SUCCESS,
            ),
            InlineKeyboardButton(
                text="ʏᴛ-ᴀᴘɪ", callback_data="api_status",icon_custom_emoji_id=4956259055468282692,
                style=ButtonStyle.DANGER,
            ),
        ],
        [
            InlineKeyboardButton(
                text="ᴧʙσυᴛ", callback_data="riiiiishuuuuuuuuuuu",icon_custom_emoji_id=5409194306365829029,
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                text="ᴘʀɪᴠᴧᴄʏ",
                callback_data="rishuuuuuuu",icon_custom_emoji_id=5251203410396458957,
                style=ButtonStyle.DANGER,
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["S_B_4"], callback_data="settings_back_helper",icon_custom_emoji_id=5422699019279283099,
                style=ButtonStyle.SUCCESS,
            )
        ],
    ]
    return buttons
