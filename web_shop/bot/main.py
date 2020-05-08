from .webshopbot import WebShopBot
from .config import *
from ..db.models import Customer, Category, Product, Address
from telebot.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ForceReply,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update
)

from copy import copy
from .keyboards import START_KB, TEXTS
from flask import Flask
from flask import request, abort
from mongoengine import DoesNotExist

CALLBACK_PARTS = {
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
    'del': 'del_',
    'cart_delete': 'cart_delete',
    'order_proceed': 'order_proceed',
    'cart_delete_approval': 'cart_delete_approval',
    'cart_delete_cancelation': 'cart_delete_cancelation'
}

bot = WebShopBot(TOKEN)
app = Flask(__name__)

customer = None


def set_webhook():
    import time
    from .check_activity import tl

    tl.start()

    bot.remove_webhook()
    time.sleep(2)
    bot.set_webhook(
        url=f'https://{HOST}/{ENDPOINT}',
        certificate=open(CERTIFICATE, 'r')
    )


def root_categories_buttons():
    categories = Category.get_root()
    buttons = [InlineKeyboardButton(text=category.title, callback_data=f'category_{category.id}') for category in
               categories]
    return buttons


def send_product_preview(product, chat_id, send_prev_button=False, send_next_button=False,
                         send_all_products_button=True, delete_message_id=None):
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

    return_to_category = product.category.parent.id if product.category.parent else CALLBACK_PARTS['root']

    first_row = [
        InlineKeyboardButton(text=TEXTS['details'],
                             callback_data=f'{CALLBACK_PARTS["product"]}{product.id}'),
        InlineKeyboardButton(text=TEXTS['back_to_category'],
                             callback_data=f'{CALLBACK_PARTS["category"]}{return_to_category}'),
        InlineKeyboardButton(text=TEXTS['add_to_cart'],
                             callback_data=f'{CALLBACK_PARTS["to_cart"]}{product.id}')
    ]

    second_row = []

    if send_prev_button:
        second_row.append(InlineKeyboardButton(text=TEXTS['previous'],
                                               callback_data=f'{CALLBACK_PARTS["previous_product"]}'))

    if send_next_button:
        second_row.append(InlineKeyboardButton(text=TEXTS['next'],
                                               callback_data=f'{CALLBACK_PARTS["next_product"]}'))

    third_row = []

    if send_all_products_button:
        third_row.append(InlineKeyboardButton(text=TEXTS['send_all_products'],
                                              callback_data=f'{CALLBACK_PARTS["all_products"]}'))

    kb.row(*first_row)

    if second_row:
        kb.row(*second_row)

    if third_row:
        kb.row(*third_row)

    caption = f'{product.title}\n\n' \
        f'{f"<s>{product.price}</s> <b>" if product.discount_perc else ""}{product.get_price()}₴' \
        f'{"</b> 🔥" if product.discount_perc else ""}'

    if delete_message_id:
        bot.delete_message(chat_id=chat_id, message_id=delete_message_id)

    bot.send_photo(
        chat_id=chat_id,
        photo=product.image.read(),
        caption=caption,
        disable_notification=True,
        reply_markup=kb,
        parse_mode='html'
    )
    product.image.seek(0)


def send_product_full_view(product, chat_id, delete_message_id):
    kb = InlineKeyboardMarkup()
    first_row = [
        InlineKeyboardButton(text=TEXTS['back'],
                             callback_data=f'{CALLBACK_PARTS["next_product"]}{product.id}'),
        InlineKeyboardButton(text=TEXTS['add_to_cart'],
                             callback_data=f'{CALLBACK_PARTS["to_cart"]}{product.id}')
    ]

    kb.row(*first_row)

    discount_txt = TEXTS['discount']

    price_str = f'{f"<s>{product.price}</s> " if product.discount_perc else ""}<b>{product.get_price()}₴</b>' \
        f'{f" 🔥({discount_txt}: {product.discount_perc}%)" if product.discount_perc else ""}'

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

        characs = dict.fromkeys(characs)
        for k in copy(characs):
            if product.characteristics.__getattribute__(k):
                characs[k] = product.characteristics.__getattribute__(k)
            else:
                del characs[k]

        nl = '\n   '
        dimensions = f"{nl}{nl.join([f'{TEXTS[k]}: {v}' for k, v in characs.items()])}"

        caption.insert(2, f'\n{TEXTS["characteristics"]}:{dimensions}')

    if delete_message_id:
        bot.delete_message(chat_id=chat_id, message_id=delete_message_id)

    bot.send_photo(
        chat_id=chat_id,
        photo=product.image.read(),
        caption='\n'.join(caption),
        disable_notification=True,
        reply_markup=kb,
        parse_mode='html'
    )
    product.image.seek(0)


def create_customer(user_id, username, first_name=None, last_name=None):
    try:
        customer = Customer.objects.get(user_id=user_id)
    except DoesNotExist:
        customer = Customer.objects.create(user_id=user_id, username=username)
    customer.username = username
    customer.first_name = first_name
    customer.last_name = last_name
    customer.is_archived = False
    customer.save()

    return customer


def get_customer(user_id, username):
    try:
        customer = Customer.objects.get(user_id=user_id)
    except DoesNotExist:
        customer = create_customer(user_id=user_id, username=username)

    return customer


def get_updated_reply_markup(customer):
    buttons = []
    for key, value in START_KB.items():
        if key != 'cart':
            buttons.append(KeyboardButton(value))
        else:
            buttons.append(KeyboardButton(value.format(f'({customer.get_or_create_current_cart().total_items})')))

    kb = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(*buttons)

    return kb


def get_cart_item_text(item):
    text = f'<b>{item.product.title}</b>, ' \
        f'{TEXTS["price"]}: <b>{item.product_price}₴</b>, ' \
        f'{TEXTS["quantity_short"]}: <b>{item.quantity}</b>, ' \
        f'{TEXTS["subsum"]}: <b>{item.item_subsum}₴</b>'
    return text


def get_cart_item_kb(item):
    buttons = []
    buttons.append(InlineKeyboardButton(
        text=TEXTS['product_view'],
        callback_data=f"{CALLBACK_PARTS['product']}{item.product.id}"
    ))
    if item.quantity > 1:
        buttons.append(InlineKeyboardButton(
            text=TEXTS['-1'],
            callback_data=f"{CALLBACK_PARTS['cart_item_modification']}" \
                f"{CALLBACK_PARTS['sub']}" \
                f"{item.product.id}"
        ))
    buttons.append(InlineKeyboardButton(
        text=TEXTS['+1'],
        callback_data=f"{CALLBACK_PARTS['cart_item_modification']}{CALLBACK_PARTS['add']}{item.product.id}"
    ))
    buttons.append(InlineKeyboardButton(
        text=TEXTS['delete_item'],
        callback_data=f"{CALLBACK_PARTS['cart_item_modification']}{CALLBACK_PARTS['del']}{item.product.id}"
    ))

    kb = InlineKeyboardMarkup()
    kb.row(*buttons)

    return kb


def se_total_sum(cart, chat_id, is_edit=False):
    kb = InlineKeyboardMarkup()
    buttons = [
        InlineKeyboardButton(text=TEXTS['cart_delete'], callback_data=CALLBACK_PARTS['cart_delete']),
        InlineKeyboardButton(text=TEXTS['order_proceed'], callback_data=CALLBACK_PARTS['order_proceed'])
    ]
    kb.row(*buttons)

    final_message = f"{TEXTS['total_cost']}: <b>{cart.total_cost}₴</b>"
    if not cart.items:
        final_message = TEXTS['no_cart_items']
        kb = None

    if is_edit:
        bot.edit_message_text(
            text=final_message,
            chat_id=chat_id,
            message_id=cart._active_sum_message_id,
            reply_markup=kb,
            parse_mode='html'
        )

    else:
        sum_message_id = bot.send_message(
            chat_id=chat_id,
            text=final_message,
            reply_markup=kb,
            parse_mode='html',
            disable_notification=True
        ).message_id

        cart._active_sum_message_id = sum_message_id
        cart.save()


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
    customer = create_customer(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    kb = get_updated_reply_markup(customer)

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
    kb = get_updated_reply_markup(customer)
    start_message_text = TEXTS['start_cart_text'].format(cart.distinct_items)
    bot.send_message(chat_id=message.chat.id, text=start_message_text, reply_markup=kb)

    for item in cart.items:
        kb = get_cart_item_kb(item)
        text = get_cart_item_text(item)

        bot.send_message(text=text, reply_markup=kb, chat_id=message.chat.id, parse_mode='html')

    se_total_sum(cart=cart, chat_id=message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PARTS['category']))
def category_handler(call):
    category_id = call.data[len(CALLBACK_PARTS['category']):]

    if category_id == CALLBACK_PARTS['root']:
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

            callback_data = category.parent.id if category.parent else CALLBACK_PARTS['root']

            buttons = [
                InlineKeyboardButton(
                    text=TEXTS['back'],
                    callback_data=f'{CALLBACK_PARTS["category"]}{callback_data}'
                )
            ]

            buttons.extend(
                [
                    InlineKeyboardButton(
                        text=cat.title,
                        callback_data=f'{CALLBACK_PARTS["category"]}{cat.id}') for cat in categories
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
            if category.products:
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
                    send_all_products_button=bool(customer.current_straight_product_list),
                    delete_message_id=call.message.message_id
                )
            else:
                kb = InlineKeyboardMarkup()

                kb.row(
                    InlineKeyboardButton(
                        text=TEXTS['back'],
                        callback_data=f"{CALLBACK_PARTS['category']}{category.parent.id}"
                    )
                )

                bot.edit_message_text(text=TEXTS['no_products'], reply_markup=kb, chat_id=call.message.chat.id,
                                      message_id=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PARTS["cart_item_modification"]))
def cart_modification_from_cart(call):
    customer = get_customer(call.from_user.id, call.from_user.username)
    cart = customer.get_or_create_current_cart()

    decision_call = call.data[len(CALLBACK_PARTS["cart_item_modification"]):]

    if decision_call.startswith(CALLBACK_PARTS['add']):
        product = Product.objects.get(id=decision_call[len(CALLBACK_PARTS["add"]):])

        item = cart.add_item(product=product)

        reply_markup = get_cart_item_kb(item)
        text = get_cart_item_text(item)

        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=text, reply_markup=reply_markup, parse_mode='html')

        se_total_sum(cart=cart, chat_id=call.message.chat.id, is_edit=True)
    elif decision_call.startswith(CALLBACK_PARTS['sub']):
        product = Product.objects.get(id=decision_call[len(CALLBACK_PARTS["sub"]):])

        item = cart.sub_item(product=product)

        if item:
            reply_markup = get_cart_item_kb(item)
            text = get_cart_item_text(item)

            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=text, reply_markup=reply_markup, parse_mode='html')

            se_total_sum(cart=cart, chat_id=call.message.chat.id, is_edit=True)
        else:
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            se_total_sum(cart=cart, chat_id=call.message.chat.id, is_edit=True)
    elif decision_call.startswith(CALLBACK_PARTS['del']):
        product = Product.objects.get(id=decision_call[len(CALLBACK_PARTS["del"]):])

        cart.del_item(product=product)

        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        se_total_sum(cart=cart, chat_id=call.message.chat.id, is_edit=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PARTS["next_product"]))
def next_product(call):
    customer = get_customer(call.from_user.id, call.from_user.username)
    if call.data != CALLBACK_PARTS["next_product"]:
        product = Product.objects.get(id=call.data[len(CALLBACK_PARTS["next_product"]):])
    else:
        product = customer.current_straight_product_list.pop()
        customer.current_backward_product_list.append(product)

    customer.save()

    send_product_preview(
        product=product,
        chat_id=call.message.chat.id,
        send_prev_button=len(customer.current_backward_product_list) > 1,
        send_next_button=bool(customer.current_straight_product_list),
        delete_message_id=call.message.message_id
    )


@bot.callback_query_handler(func=lambda call: call.data == CALLBACK_PARTS["previous_product"])
def prev_product(call):
    customer = get_customer(call.from_user.id, call.from_user.username)
    customer.current_straight_product_list.append(customer.current_backward_product_list.pop())
    product = customer.current_backward_product_list[-1]
    customer.save()

    send_product_preview(
        product=product,
        chat_id=call.message.chat.id,
        send_prev_button=len(customer.current_backward_product_list) > 1,
        send_next_button=bool(customer.current_straight_product_list),
        delete_message_id=call.message.message_id
    )


@bot.callback_query_handler(func=lambda call: call.data == CALLBACK_PARTS["all_products"])
def all_product(call):
    customer = get_customer(call.from_user.id, call.from_user.username)
    delete_message_id = call.message.message_id
    for product in (*customer.current_backward_product_list[::-1], *customer.current_straight_product_list[::-1]):
        send_product_preview(
            product=product,
            chat_id=call.message.chat.id,
            send_all_products_button=False,
            delete_message_id=delete_message_id
        )
        delete_message_id = None


@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PARTS["product"]))
def detailed_product_view(call):
    product_id = call.data[len(CALLBACK_PARTS["product"]):]
    product = Product.objects.get(id=product_id)
    send_product_full_view(product=product, chat_id=call.message.chat.id, delete_message_id=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PARTS["to_cart"]))
def to_cart(call):
    customer = get_customer(call.from_user.id, call.from_user.username)
    product_id = call.data[len(CALLBACK_PARTS["to_cart"]):]
    product = Product.objects.get(id=product_id)
    customer.get_or_create_current_cart().add_item(product=product)

    kb = get_updated_reply_markup(customer)
    bot.send_message(text=TEXTS['added_to_cart'], chat_id=call.message.chat.id, reply_markup=kb)


@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PARTS['cart_delete']))
def cart_delete(call):
    if call.data == CALLBACK_PARTS['cart_delete']:
        kb = InlineKeyboardMarkup()
        buttons = [
            InlineKeyboardButton(text=TEXTS['yes'], callback_data=CALLBACK_PARTS['cart_delete_approval']),
            InlineKeyboardButton(text=TEXTS['cancel'], callback_data=CALLBACK_PARTS['cart_delete_cancelation'])
        ]
        kb.row(*buttons)

        bot.send_message(text=TEXTS['cart_delete_approval'], chat_id=call.message.chat.id, reply_markup=kb)
    elif call.data == CALLBACK_PARTS['cart_delete_approval']:

        customer = get_customer(call.from_user.id, call.from_user.username)
        customer.get_or_create_current_cart().del_all_items()

        kb = get_updated_reply_markup(customer)
        bot.send_message(text=TEXTS['cart_deleted'], chat_id=call.message.chat.id, reply_markup=kb)

    elif call.data == CALLBACK_PARTS['cart_delete_cancelation']:
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('address_delete'))
def address_delete(call):
    customer = get_customer(call.from_user.id, call.from_user.username)
    if call.data.startswith('address_delete_index'):
        address_txt = call.message.text

        callback_addition = f"{customer.address_list.index(address_txt)}_{call.message.message_id}"

        kb = InlineKeyboardMarkup()
        buttons = [
            InlineKeyboardButton(text=TEXTS['yes'], callback_data=f'address_delete_approval_{callback_addition}'),
            InlineKeyboardButton(text=TEXTS['cancel'], callback_data='address_delete_cancelation')
        ]
        kb.row(*buttons)

        bot.send_message(text=TEXTS['address_delete_approval'], chat_id=call.message.chat.id, reply_markup=kb)
    elif call.data.startswith('address_delete_approval_'):

        callback_addition = call.data[len('address_delete_approval_'):]
        address_index = int(callback_addition.split('_')[0])
        address_message_id = int(callback_addition.split('_')[1])

        del customer.address_list[address_index]
        customer.save()

        bot.delete_message(chat_id=call.message.chat.id, message_id=address_message_id)
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)

    elif call.data == 'address_delete_cancelation':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PARTS['order_proceed']))
def order_proceed(call):
    customer = get_customer(user_id=call.from_user.id, username=call.from_user.username)
    if call.data == CALLBACK_PARTS['order_proceed']:
        final_message = f"{TEXTS['choose_address']}"
        if not customer.address_list:
            final_message = TEXTS['no_addresses']
        for address in customer.address_list:
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton(
                    text=TEXTS['choose_this_address'],
                    callback_data=f'order_proceed_address_chosen'
                ),
                InlineKeyboardButton(
                    text=TEXTS['delete_item'],
                    callback_data=f'address_delete_index'
                )
            )
            bot.send_message(text=str(address), reply_markup=markup, chat_id=call.message.chat.id, parse_mode='html')

        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton(text=TEXTS['address_add'], callback_data='address_add'))

        bot.send_message(text=final_message, chat_id=call.message.chat.id, reply_markup=kb)
    elif call.data.startswith('order_proceed_address_chosen'):
        address_index = customer.address_list.index(call.message.text)
        cart = customer.get_or_create_current_cart()
        cart.address = customer.address_list[address_index]
        cart.save()

        cart_items_txt = '\n'.join([get_cart_item_text(ci) for ci in cart.items])
        total = f"{TEXTS['total_cost']}: <b>{cart.total_cost}₴</b>"

        text = '\n'.join(
            [
                cart_items_txt,
                '',
                total,
                '',
                TEXTS['shipping_address'],
                str(cart.address)
            ]
        )

        kb = InlineKeyboardMarkup()
        buttons = [
            InlineKeyboardButton(text=TEXTS['back'], callback_data='order_proceed'),
            InlineKeyboardButton(text=TEXTS['order_confirmation'], callback_data=f'order_proceed_final_confirmation')
        ]
        kb.row(*buttons)

        bot.send_message(text=text, chat_id=call.message.chat.id, reply_markup=kb, parse_mode='html')
    elif call.data.startswith('order_proceed_final_confirmation'):
        cart = customer.get_or_create_current_cart()

        cart.archive()

        kb = get_updated_reply_markup(customer)

        bot.send_message(reply_markup=kb,
                         chat_id=call.message.chat.id,
                         text=TEXTS['order_ended'],
                         parse_mode='html'
                         )


@bot.callback_query_handler(func=lambda call: call.data == 'address_add')
def address_add_start_form(call):
    bot.send_message(text=TEXTS['address_disclaimer'], chat_id=call.message.chat.id)
    bot.send_message(text=TEXTS['address_add_name'], chat_id=call.message.chat.id, reply_markup=ForceReply())


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


def form_input(message):
    if message.reply_to_message:
        return message.reply_to_message.message_id + 1 == message.message_id
    else:
        return False


@bot.message_handler(func=form_input)
def address_form_handler(message):
    customer = get_customer(user_id=message.from_user.id, username=message.from_user.username)

    if message.reply_to_message.text == TEXTS['address_add_name']:
        customer.current_address_creation_form = Address(
            first_name=message.text.title(),
            last_name='dummy',
            city='dummy',
            phone_number='0000000000',
            nova_poshta_branch=1
        )
        customer.save()
        bot.send_message(text=TEXTS['address_add_surname'], chat_id=message.chat.id, reply_markup=ForceReply())
    elif message.reply_to_message.text == TEXTS['address_add_surname']:
        customer.current_address_creation_form.last_name = message.text.title()
        customer.save()
        bot.send_message(text=TEXTS['address_add_phone'], chat_id=message.chat.id, reply_markup=ForceReply())
    elif message.reply_to_message.text == TEXTS['address_add_phone']:
        customer.current_address_creation_form.phone_number = message.text
        customer.save()
        bot.send_message(text=TEXTS['address_add_city'], chat_id=message.chat.id, reply_markup=ForceReply())
    elif message.reply_to_message.text == TEXTS['address_add_city']:
        customer.current_address_creation_form.city = message.text
        customer.save()
        bot.send_message(text=TEXTS['address_add_NP_number'], chat_id=message.chat.id, reply_markup=ForceReply())
    elif message.reply_to_message.text == TEXTS['address_add_NP_number']:
        customer.current_address_creation_form.nova_poshta_branch = int(message.text)
        customer.add_address()
        del customer.current_address_creation_form
        customer.save()
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton(text=TEXTS['order_proceed'], callback_data='order_proceed')
        )
        bot.send_message(text=TEXTS['address_add_success'], chat_id=message.chat.id, reply_markup=kb)
    else:
        bot.send_message(text=TEXTS['not_correct'], chat_id=message.chat.id)

        kb = get_updated_reply_markup(customer)

        bot.send_message(reply_markup=kb,
                         chat_id=message.chat.id,
                         text=f"{message.chat.first_name}, {TEXTS['greeting_message']}",
                         parse_mode='html'
                         )


@bot.message_handler(func=lambda message: message.text == START_KB['news'])
def news_handler(message):
    pass


@bot.message_handler(
    content_types=[
        'audio',
        'photo',
        'voice',
        'video',
        'document',
        'text',
        'location',
        'contact',
        'sticker'
    ]
)
def default_handler(message):
    customer = get_customer(message.from_user.id, username=message.from_user.username)
    kb = get_updated_reply_markup(customer)

    bot.send_message(reply_markup=kb,
                     chat_id=message.chat.id,
                     text=f"{message.chat.first_name}, {TEXTS['greeting_message']}",
                     parse_mode='html'
                     )
