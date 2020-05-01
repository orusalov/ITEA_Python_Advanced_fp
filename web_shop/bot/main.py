from .webshopbot import WebShopBot
from .config import *
from ..db.models import Customer, Category, Product
from telebot.types import (
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update
)

from .keyboards import START_KB, TEXTS
from flask import Flask
from flask import request, abort

CALLBACK_PREFIXES = {
    'category': 'category_',
    'product': 'product_',
    'root': 'root',
    'to_cart': 'to_cart_',
    'next_product': 'next_product',
    'previous_product': 'previous_product',
    'all_products': 'send_all_products'
}

bot = WebShopBot(TOKEN)
app = Flask(__name__)


def set_webhook():
    import time

    bot.remove_webhook()
    time.sleep(2)
    bot.set_webhook(
        url=f'https://{HOST}/{ENDPOINT}',
        certificate=open(CERTIFICETE, 'r')
    )

def root_categories_buttons():
    categories = Category.get_root()
    buttons = [InlineKeyboardButton(text=category.title, callback_data=f'category_{category.id}') for category in
               categories]
    return buttons

def send_product_preview(product, chat_id, send_prev_button=False, send_next_button=False,
                         send_all_products_button=True):
    kb = InlineKeyboardMarkup(row_width=2)
    # buttons = [
    #     InlineKeyboardButton(text=TEXTS['details'],
    #                          callback_data=f'{CALLBACK_PREFIXES["product"]}{product.id}'),
    #     InlineKeyboardButton(text=TEXTS['add_to_cart'],
    #                          callback_data=f'{CALLBACK_PREFIXES["to_cart"]}{product.id}')
    # ]
    #
    # if send_prev_button:
    #     buttons.append(InlineKeyboardButton(text=TEXTS['previous'],
    #                                         callback_data=f'{CALLBACK_PREFIXES["previous_product"]}'))
    #
    # if send_next_button:
    #     buttons.append(InlineKeyboardButton(text=TEXTS['next'],
    #                                         callback_data=f'{CALLBACK_PREFIXES["next_product"]}'))
    #
    # if send_all_products_button:
    #     buttons.append(InlineKeyboardButton(text=TEXTS['send_all_products'],
    #                                         callback_data=f'{CALLBACK_PREFIXES["all_products"]}'))

    # kb.add(*buttons)

    first_row = [
            InlineKeyboardButton(text=TEXTS['details'],
                                 callback_data=f'{CALLBACK_PREFIXES["product"]}{product.id}').to_dic(),
            InlineKeyboardButton(text=TEXTS['back_to_category'],
                                 callback_data=f'{CALLBACK_PREFIXES["category"]}{product.category.parent.id}').to_dic(),
            InlineKeyboardButton(text=TEXTS['add_to_cart'],
                                 callback_data=f'{CALLBACK_PREFIXES["to_cart"]}{product.id}').to_dic()
        ]

    second_row = []

    if send_prev_button:
        second_row.append(InlineKeyboardButton(text=TEXTS['previous'],
                                            callback_data=f'{CALLBACK_PREFIXES["previous_product"]}').to_dic())

    if send_next_button:
        second_row.append(InlineKeyboardButton(text=TEXTS['next'],
                                            callback_data=f'{CALLBACK_PREFIXES["next_product"]}').to_dic())

    third_row = []

    if send_all_products_button:
        third_row.append(InlineKeyboardButton(text=TEXTS['send_all_products'],
                                            callback_data=f'{CALLBACK_PREFIXES["all_products"]}').to_dic())

    kb.keyboard.append(first_row)

    if second_row:
        kb.keyboard.append(second_row)

    if third_row:
        kb.keyboard.append(third_row)

    bot.send_photo(
        chat_id=chat_id,
        photo=product.image.read(),
        caption=f'{TEXTS["price"]} - {product.price}, {product.description}',
        disable_notification=True,
        reply_markup=kb
    )
    product.image.seek(0)

@app.route('/', methods=['POST'])
def process_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(status=403)


@bot.message_handler(commands=['start'])
def start(message):
    buttons = [KeyboardButton(value) for value in START_KB.values()]
    print(message.chat.id)
    bot.se_reply_keyboard(buttons=buttons, chat_id=message.chat.id, text=TEXTS['greeting_message'])


@bot.message_handler(func=lambda message: message.text == START_KB['categories'])
def categories_handler(message):
    bot.se_inline_keyboard(
        chat_id=message.chat.id,
        text=TEXTS['categories_message'],
        buttons=root_categories_buttons()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PREFIXES['category']))
def category_handler(call):
    category_id = call.data[len(CALLBACK_PREFIXES['category']):]

    if category_id == CALLBACK_PREFIXES['root']:
        bot.se_inline_keyboard(
            chat_id=call.message.chat.id,
            text=TEXTS['categories_message'],
            buttons=root_categories_buttons(),
            message_id=call.message.message_id
        )
    else:
        category = Category.objects.get(id=category_id)

        if category.subcategories:
            categories = category.subcategories
            buttons = [InlineKeyboardButton(text=cat.title, callback_data=f'{CALLBACK_PREFIXES["category"]}{cat.id}') for cat in categories]

            callback_data = category.parent.id if category.parent else CALLBACK_PREFIXES['root']

            buttons.append(InlineKeyboardButton(text=TEXTS['back'], callback_data=f'{CALLBACK_PREFIXES["category"]}{callback_data}'))

            message_id = call.message.message_id if call.message.text else None

            bot.se_inline_keyboard(
                chat_id=call.message.chat.id,
                text=category.title,
                buttons=buttons,
                message_id=message_id
            )

        elif category.is_leaf:
            global current_straight_product_list
            current_straight_product_list = []
            global current_backward_product_list
            current_backward_product_list = []

            current_straight_product_list.extend(category.products)
            product = current_straight_product_list.pop()
            current_backward_product_list.append(product)

            send_product_preview(
                product=product,
                chat_id=call.message.chat.id,
                send_next_button=bool(current_straight_product_list),
                send_all_products_button=bool(current_straight_product_list)
            )


@bot.callback_query_handler(func=lambda call: call.data == CALLBACK_PREFIXES["next_product"])
def next_product(call):
    product = current_straight_product_list.pop()
    current_backward_product_list.append(product)

    send_product_preview(
        product=product,
        chat_id=call.message.chat.id,
        send_prev_button=len(current_backward_product_list) > 1,
        send_next_button=bool(current_straight_product_list)
    )

@bot.callback_query_handler(func=lambda call: call.data == CALLBACK_PREFIXES["previous_product"])
def prev_product(call):
    current_straight_product_list.append(current_backward_product_list.pop())
    product = current_backward_product_list[-1]

    send_product_preview(
        product=product,
        chat_id=call.message.chat.id,
        send_prev_button=len(current_backward_product_list) > 1,
        send_next_button=bool(current_straight_product_list)
    )

@bot.callback_query_handler(func=lambda call: call.data == CALLBACK_PREFIXES["all_products"])
def all_product(call):
    for product in (*current_backward_product_list[::-1], *current_straight_product_list[::-1]):

        send_product_preview(
            product=product,
            chat_id=call.message.chat.id,
            send_all_products_button=False
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PREFIXES["product"]))
def details_cart(call):
    pass


@bot.message_handler(func=lambda message: message.text == START_KB['news'])
def news_handler(message):
    pass


@bot.message_handler(func=lambda message: message.text == START_KB['discount_products'])
def discount_products_handler(message):
    global current_straight_product_list
    current_straight_product_list = []
    global current_backward_product_list
    current_backward_product_list = []

    current_straight_product_list.extend(Product.get_discount_products())
    product = current_straight_product_list.pop()
    current_backward_product_list.append(product)

    send_product_preview(
        product=product,
        chat_id=message.chat.id,
        send_next_button=bool(current_straight_product_list),
        send_all_products_button=bool(current_straight_product_list)
    )
