from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

InlineButton = InlineKeyboardButton


class InlineKeyboard(InlineKeyboardMarkup):
    def __init__(self, row_width: int = 3):
        self.row_width = row_width
        self.inline_keyboard = []
        super().__init__(self.inline_keyboard)

    def add(self, *buttons):
        w = self.row_width
        for i in range(0, len(buttons), w):
            self.inline_keyboard.append(list(buttons[i:i + w]))

    def row(self, *buttons):
        self.inline_keyboard.append(list(buttons))