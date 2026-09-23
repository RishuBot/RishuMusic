from typing import Union

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ButtonStyle

from RishuMusic import app


def help_pannel(_, is_sudo, START: Union[bool, int] = None):
    first = [
        InlineKeyboardButton(
            text=_["CLOSE_BUTTON"],
            callback_data=f"close",
            icon_custom_emoji_id=4956337889593000947,  # ❌
            style=ButtonStyle.DANGER,
        )
    ]
    second = [
        InlineKeyboardButton(
            text=_["BACK_BUTTON"],
            callback_data=f"settingsback_helper",
            icon_custom_emoji_id=5280766107504899554,  # 🔙
            style=ButtonStyle.PRIMARY,
        ),
    ]
    mark = second if START else first

    upl = [
        [
            InlineKeyboardButton(
                text=_["H_B_10"],
                callback_data="help_callback hb10",
                icon_custom_emoji_id=6134194260628479379,  # 🎉
                style=ButtonStyle.PRIMARY,
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["H_B_1"],
                callback_data="help_callback hb1",
                icon_custom_emoji_id=5039649904264217620,  # 🔍
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                text=_["H_B_2"],
                callback_data="help_callback hb2",
                icon_custom_emoji_id=6113971389935391397,  # 👨‍💻
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                text=_["H_B_3"],
                callback_data="help_callback hb3",
                icon_custom_emoji_id=4956259055468282692,  # 📡
                style=ButtonStyle.PRIMARY,
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["H_B_4"],
                callback_data="help_callback hb4",
                icon_custom_emoji_id=5372926953978341366,  # 👥
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                text=_["H_B_5"],
                callback_data="help_callback hb5",
                icon_custom_emoji_id=4958621433509970793,  # 📊
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                text=_["H_B_6"],
                callback_data="help_callback hb6",
                icon_custom_emoji_id=6123166309325740830,  # 🔥
                style=ButtonStyle.PRIMARY,
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["H_B_7"],
                callback_data="help_callback hb7",
                icon_custom_emoji_id=6172517356162520126,  # ✅
                style=ButtonStyle.SUCCESS,
            ),
            InlineKeyboardButton(
                text=_["H_B_8"],
                callback_data="help_callback hb8",
                icon_custom_emoji_id=5308624268255460504,  # ⚙️
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                text=_["H_B_9"],
                callback_data="help_callback hb9",
                icon_custom_emoji_id=5298609030321691620,  # 📣
                style=ButtonStyle.PRIMARY,
            ),
        ],
    ]

    upl.append(mark)

    return InlineKeyboardMarkup(upl)


def help_back_markup(_):
    upl = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=_["BACK_BUTTON"],
                    callback_data=f"settings_back_helper",
                    icon_custom_emoji_id=5280766107504899554,  # 🔙
                    style=ButtonStyle.PRIMARY,
                ),
            ]
        ]
    )
    return upl


def private_help_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_4"],
                url=f"https://t.me/{app.username}?start=help",
                icon_custom_emoji_id=5767297774584339394,  # 🔗
                style=ButtonStyle.PRIMARY,
            ),
        ],
    ]
    return buttons

