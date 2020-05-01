from telebot import TeleBot
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update
)

from typing import  List


class WebShopBot(TeleBot):

    def __init(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def se_reply_keyboard(self, buttons: List[KeyboardButton], chat_id: int=None, text: str=None, message_id: int=None,
                          **kwargs):

        kb = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

        kb.add(*buttons)

        params = dict(chat_id=chat_id, text=text, reply_markup=kb, **kwargs)

        if message_id:
            self.edit_message_text(**params)
        else:
            self.send_message(**params)


    def se_inline_keyboard(self, buttons: List[InlineKeyboardButton], chat_id: int, text: str, message_id: int=None,
                           **kwargs):

        kb = InlineKeyboardMarkup(row_width=2)

        kb.add(*buttons)

        params = dict(chat_id=chat_id, text=text, reply_markup=kb, **kwargs)

        if message_id:
            params['message_id'] = message_id
            self.edit_message_text(**params)
        else:
            self.send_message(**params)
