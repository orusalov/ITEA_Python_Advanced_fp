from telebot import TeleBot
from .config import TOKEN
from ..db.models import Customer, Category
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update
)

from .keyboards import START_KB
from flask import Flask
from flask import request, abort

bot = TeleBot(TOKEN)
app = Flask(__name__)


@app.route('/', methods=['POST'])
def process_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(status=403)

def set_webhook():
    import time

    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(
        url='https://35.246.165.155/tg',
        certificate=open('web_shop/bot/webhook_cert.pem', 'r')
    )



# @bot.message_handler(commands=['start'])
# def start(message):
#     kb = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
#
#     buttons = [KeyboardButton(value) for value in START_KB.values()]
#
#     kb.add(*buttons)
#
#     bot.send_message(
#         message.chat.id,
#         'Greetings!',
#         reply_markup=kb
#     )
#
#
# @bot.message_handler(func=lambda message: message.text == START_KB['categories'])
# def categories_handler(message):
#     kb = InlineKeyboardMarkup(row_width=2)
#     categories = Category.get_root()
#     buttons = [InlineKeyboardButton(text=category.title, callback_data=f'category_{category.id}') for category in
#                categories]
#     kb.add(*buttons)
#
#     bot.send_message(
#         message.chat.id,
#         "Выберите категорию",
#         reply_markup=kb
#     )
#
#
# @bot.callback_query_handler(func=lambda call: call.data.startswith('category'))
# def category_handler(call):
#     category_id = '_'.join(call.data.split('_')[1:])
#     category = Category.objects.get(id=category_id)
#     kb = InlineKeyboardMarkup(row_width=2)
#
#     if category.subcategories:
#         categories = category.subcategories
#         buttons = [InlineKeyboardButton(text=category.title, callback_data=f'category_{category.id}') for category in
#                    categories]
#
#         kb.add(*buttons)
#
#         bot.edit_message_text(
#             text=category.title,
#             chat_id=call.message.chat.id,
#             message_id=call.message.message_id,
#             reply_markup=kb
#         )
#     elif category.is_leaf:
#
#         for product in category.products:
#             button = InlineKeyboardButton(text='Добавить в корзину', callback_data=f'product_{product.id}')
#
#             kb.keyboard = [[button.to_dic()]]
#
#             bot.send_photo(
#                 chat_id=call.message.chat.id,
#                 photo=product.image.read(),
#                 caption=product.description,
#                 disable_notification=True,
#                 reply_markup=kb
#             )
#
#
# @bot.callback_query_handler(func=lambda call: call.data.startswith('product'))
# def add_to_cart(call):
#     pass
#
#
# @bot.message_handler(func=lambda message: message.text == START_KB['news'])
# def news_handler(message):
#     pass
#
#
# @bot.message_handler(func=lambda message: message.text == START_KB['discount_products'])
# def discount_products_handler(message):
#     pass


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        'Привет! Пришли мне фоточку того, что хочешь освятить'
    )


@bot.message_handler(content_types=['text','photo'])
def categories_handler(message):

    if message.text:
        bot.send_message(
            message.chat.id,
            "Ненене, вышлите фото"
        )
    else:
        with open('photo_2020-04-17_20-53-28.jpg', 'rb') as file:
            bot.send_photo(
                chat_id=message.chat.id,
                photo=file,
                disable_notification=True
            )
