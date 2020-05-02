from .webshopbot import WebShopBot
from .config import *
from ..db.models import Customer, Category, Product
from telebot.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update
)

from .keyboards import START_KB, TEXTS
from flask import Flask
from flask import request, abort
from mongoengine import DoesNotExist

CALLBACK_PREFIXES = {
    'category': 'category_',
    'product': 'product_',
    'root': 'root',
    'to_cart': 'to_cart_',
    'next_product': 'next_product',
    'previous_product': 'previous_product',
    'all_products': 'send_all_products',
    'cart_item_modification': 'cart_item_modification_',
    'sub': 'sub_',
    'add': 'add_',
    'del': 'del_'
}

bot = WebShopBot(TOKEN)
app = Flask(__name__)

customer = None


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

    return_to_category = product.category.parent.id if product.category.parent else CALLBACK_PREFIXES['root']

    first_row = [
        InlineKeyboardButton(text=TEXTS['details'],
                             callback_data=f'{CALLBACK_PREFIXES["product"]}{product.id}'),
        InlineKeyboardButton(text=TEXTS['back_to_category'],
                             callback_data=f'{CALLBACK_PREFIXES["category"]}{return_to_category}'),
        InlineKeyboardButton(text=TEXTS['add_to_cart'],
                             callback_data=f'{CALLBACK_PREFIXES["to_cart"]}{product.id}')
    ]

    second_row = []

    if send_prev_button:
        second_row.append(InlineKeyboardButton(text=TEXTS['previous'],
                                               callback_data=f'{CALLBACK_PREFIXES["previous_product"]}'))

    if send_next_button:
        second_row.append(InlineKeyboardButton(text=TEXTS['next'],
                                               callback_data=f'{CALLBACK_PREFIXES["next_product"]}'))

    third_row = []

    if send_all_products_button:
        third_row.append(InlineKeyboardButton(text=TEXTS['send_all_products'],
                                              callback_data=f'{CALLBACK_PREFIXES["all_products"]}'))

    kb.row(*first_row)

    if second_row:
        kb.row(*second_row)

    if third_row:
        kb.row(*third_row)

    caption = f'{product.title}\n\n' \
        f'{f"<s>{product.price}</s> <b>" if product.discount_perc else ""}{product.get_price()}₴' \
        f'{"</b> 🔥" if product.discount_perc else ""}'

    bot.send_photo(
        chat_id=chat_id,
        photo=product.image.read(),
        caption=caption,
        disable_notification=True,
        reply_markup=kb,
        parse_mode='html'
    )
    product.image.seek(0)


def send_product_full_view(product, chat_id):
    kb = InlineKeyboardMarkup()
    first_row = [
        InlineKeyboardButton(text=TEXTS['back'],
                             callback_data=f'{CALLBACK_PREFIXES["next_product"]}{product.id}'),
        InlineKeyboardButton(text=TEXTS['add_to_cart'],
                             callback_data=f'{CALLBACK_PREFIXES["to_cart"]}{product.id}')
    ]

    kb.row(*first_row)

    discount_txt = TEXTS['discount']

    price_str = f'{f"<s>{product.price}</s> <b>" if product.discount_perc else ""}{product.get_price()}₴' \
        f'{f"</b> 🔥({discount_txt}: {product.discount_perc}%)" if product.discount_perc else ""}'

    caption = [
        f'<b>{product.title}</b>',
        product.description,
        '',
        price_str
    ]

    if product.characteristics:
        characs = {'height', 'width', 'depth', 'weight'}
        patrs = product.characteristics._fields

        characs = set(patrs.keys()) & characs

        nl = '\n   '
        dimensions = f"{nl}{nl.join([f'{TEXTS[k]}: {patrs[k]}' for k in characs])}"

        caption.insert(2, f'{TEXTS["characteristics"]}:\n{dimensions}')

    bot.send_photo(
        chat_id=chat_id,
        photo=product.image.read(),
        caption='\n'.join(caption),
        disable_notification=True,
        reply_markup=kb,
        parse_mode='html'
    )
    product.image.seek(0)


def get_customer(user_id, username):
    try:
        customer = Customer.objects.get(user_id=user_id)
    except DoesNotExist:
        customer = Customer.objects.create(user_id=user_id, username=username)

    return customer


def get_updated_reply_markup(user_id, username):
    customer = get_customer(user_id, username)

    buttons = []
    for key, value in START_KB.items():
        if key != 'cart':
            buttons.append(KeyboardButton(value))
        else:
            buttons.append(KeyboardButton(value.format(f'({customer.get_or_create_current_cart().total_items})')))

    kb = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(*buttons)

    return kb


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
    kb = get_updated_reply_markup(message.from_user.id, username=message.from_user.username)

    bot.send_message(reply_markup=kb,
                     chat_id=message.chat.id,
                     text=f"{message.chat.first_name}, {TEXTS['greeting_message']}",
                     parse_mode='html'
                     )


@bot.message_handler(func=lambda message: message.text == START_KB['categories'])
def categories_handler(message):
    bot.se_inline_keyboard(
        chat_id=message.chat.id,
        text=TEXTS['categories_message'],
        buttons=root_categories_buttons(),
        parse_mode='html'
    )


@bot.message_handler(regexp="^" + START_KB['cart'].format('\(\d+\)') + "$")
def cart_handler(message):
    customer = get_customer(message.from_user.id, message.from_user.username)

    cart = customer.get_or_create_current_cart()

    final_message = f"{TEXTS['total_cost']}: <b>{cart.total_cost}₴</b>"
    if not cart.items:
        final_message = TEXTS['no_cart_items']

    for item in cart.items:
        text = f'<b>{item.product.title}</b>, ' \
            f'{TEXTS["price"]}: <b>{item.product_price}₴</b>, ' \
            f'{TEXTS["quantity_short"]}: <b>{item.quantity}</b>, ' \
            f'{TEXTS["subsum"]}: <b>{item.item_subsum}₴</b>'
        buttons = []
        buttons.append(InlineKeyboardButton(
            text=TEXTS['product_view'],
            callback_data=f"{CALLBACK_PREFIXES['next_product']}{item.product.id}"
        ))
        if item.quantity > 1:
            buttons.append(InlineKeyboardButton(
                text=TEXTS['-1'],
                callback_data=f"{CALLBACK_PREFIXES['cart_item_modification']}" \
                f"{CALLBACK_PREFIXES['sub']}" \
                f"{item.product.id}"
            ))
        buttons.append(InlineKeyboardButton(
            text=TEXTS['+1'],
            callback_data=f"{CALLBACK_PREFIXES['cart_item_modification']}{CALLBACK_PREFIXES['add']}{item.product.id}"
        ))
        buttons.append(InlineKeyboardButton(
            text=TEXTS['delete_item'],
            callback_data=f"{CALLBACK_PREFIXES['cart_item_modification']}{CALLBACK_PREFIXES['del']}{item.product.id}"
        ))

        kb = InlineKeyboardMarkup()
        kb.row(*buttons)

        bot.send_message(text=text, reply_markup=kb, chat_id=message.chat.id, parse_mode='html')

    kb = get_updated_reply_markup(message.from_user.id, message.from_user.username)

    bot.send_message(
        chat_id=message.chat.id,
        text=final_message,
        reply_markup=kb,
        parse_mode='html',
        disable_notification=True
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

            callback_data = category.parent.id if category.parent else CALLBACK_PREFIXES['root']

            buttons = [
                InlineKeyboardButton(
                    text=TEXTS['back'],
                    callback_data=f'{CALLBACK_PREFIXES["category"]}{callback_data}'
                )
            ]

            buttons.extend(
                [
                    InlineKeyboardButton(
                        text=cat.title,
                        callback_data=f'{CALLBACK_PREFIXES["category"]}{cat.id}') for cat in categories
                ]
            )

            message_id = call.message.message_id if call.message.text else None

            bot.se_inline_keyboard(
                chat_id=call.message.chat.id,
                text=category.title,
                buttons=buttons,
                message_id=message_id
            )

        elif category.is_leaf:
            customer = get_customer(call.from_user.id, call.from_user.username)

            customer.current_straight_product_list = []
            customer.current_backward_product_list = []

            customer.current_straight_product_list.extend(category.products)
            product = customer.current_straight_product_list.pop()
            customer.current_backward_product_list.append(product)

            customer.save()

            send_product_preview(
                product=product,
                chat_id=call.message.chat.id,
                send_next_button=bool(customer.current_straight_product_list),
                send_all_products_button=bool(customer.current_straight_product_list)
            )


@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PREFIXES["next_product"]))
def next_product(call):
    customer = get_customer(call.from_user.id, call.from_user.username)
    if call.data != CALLBACK_PREFIXES["next_product"]:
        product = Product.objects.get(id=call.data[len(CALLBACK_PREFIXES["next_product"]):])
    else:
        product = customer.current_straight_product_list.pop()
        customer.current_backward_product_list.append(product)

    customer.save()

    send_product_preview(
        product=product,
        chat_id=call.message.chat.id,
        send_prev_button=len(customer.current_backward_product_list) > 1,
        send_next_button=bool(customer.current_straight_product_list)
    )


@bot.callback_query_handler(func=lambda call: call.data == CALLBACK_PREFIXES["previous_product"])
def prev_product(call):
    customer = get_customer(call.from_user.id, call.from_user.username)
    customer.current_straight_product_list.append(customer.current_backward_product_list.pop())
    product = customer.current_backward_product_list[-1]
    customer.save()

    send_product_preview(
        product=product,
        chat_id=call.message.chat.id,
        send_prev_button=len(customer.current_backward_product_list) > 1,
        send_next_button=bool(customer.current_straight_product_list)
    )


@bot.callback_query_handler(func=lambda call: call.data == CALLBACK_PREFIXES["all_products"])
def all_product(call):
    customer = get_customer(call.from_user.id, call.from_user.username)
    for product in (*customer.current_backward_product_list[::-1], *customer.current_straight_product_list[::-1]):
        send_product_preview(
            product=product,
            chat_id=call.message.chat.id,
            send_all_products_button=False
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PREFIXES["product"]))
def detailed_product_view(call):
    product_id = call.data[len(CALLBACK_PREFIXES["product"]):]
    product = Product.objects.get(id=product_id)
    send_product_full_view(product=product, chat_id=call.message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PREFIXES["to_cart"]))
def detailed_product_view(call):
    customer = get_customer(call.from_user.id, call.from_user.username)
    product_id = call.data[len(CALLBACK_PREFIXES["to_cart"]):]
    product = Product.objects.get(id=product_id)
    customer.get_or_create_current_cart().add_item(product=product)

    kb = get_updated_reply_markup(call.from_user.id, username=call.from_user.username)
    bot.send_message(text=TEXTS['added_to_cart'], chat_id=call.message.chat.id, reply_markup=kb)


@bot.message_handler(func=lambda message: message.text == START_KB['news'])
def news_handler(message):
    pass


@bot.message_handler(func=lambda message: message.text == START_KB['discount_products'])
def discount_products_handler(message):
    customer = get_customer(message.from_user.id, message.from_user.username)
    customer.current_straight_product_list = []
    customer.current_backward_product_list = []

    customer.current_straight_product_list.extend(Product.get_discount_products())
    product = customer.current_straight_product_list.pop()
    customer.current_backward_product_list.append(product)
    customer.save()

    send_product_preview(
        product=product,
        chat_id=message.chat.id,
        send_next_button=bool(customer.current_straight_product_list),
        send_all_products_button=bool(customer.current_straight_product_list)
    )
