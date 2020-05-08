from .webshopbot import WebShopBot
from .config import *
from telebot.types import (
    ForceReply,
    InlineKeyboardButton,
    Update
)

from .keyboards import START_KB, TEXTS
from flask import Flask
from flask import request, abort

bot = WebShopBot(TOKEN)
app = Flask(__name__)

customer = None


def set_webhook():
    import time

    bot.remove_webhook()
    time.sleep(2)
    bot.set_webhook(
        url=f'https://{HOST}/{ENDPOINT}',  #
        certificate=open(CERTIFICATE, 'r')
    )


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
    customer = bot.create_customer(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    kb = bot.get_general_keyboard(customer)

    bot.send_message(reply_markup=kb,
                     chat_id=message.chat.id,
                     text=f"{message.chat.first_name}, {TEXTS['greeting_message']}",
                     parse_mode='html'
                     )


@bot.message_handler(func=lambda message: message.text == START_KB['categories'])
def categories_handler(message):
    bot.se_categories(
        chat_id=message.chat.id,
        text=TEXTS['categories_message'],
        buttons=bot.root_categories_buttons(),
        parse_mode='html'
    )


@bot.message_handler(regexp="^" + START_KB['cart'].format('\(\d+\)') + "$")
def cart_handler(message):
    customer = bot.get_customer(user_id=message.from_user.id)
    cart = customer.get_or_create_current_cart()
    kb = bot.get_general_keyboard(customer)
    start_message_text = TEXTS['start_cart_text'].format(cart.distinct_items)
    bot.send_message(chat_id=message.chat.id, text=start_message_text, reply_markup=kb)

    for item in cart.items:
        kb = bot.get_cart_item_kb(item)
        text = bot.get_cart_item_text(item)

        bot.send_message(text=text, reply_markup=kb, chat_id=message.chat.id, parse_mode='html')

    bot.se_total_sum(cart=cart, chat_id=message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('category'))
def category_handler(call):
    category_id = call.data[len('category'):]

    if category_id == 'root':
        bot.se_categories(
            chat_id=call.message.chat.id,
            text=TEXTS['categories_message'],
            buttons=bot.root_categories_buttons(),
            message_id=call.message.message_id
        )
    else:
        category = bot.get_category(id=category_id)

        if category.subcategories:
            categories = category.subcategories
            callback_data = category.parent.id if category.parent else 'root'
            back_button = InlineKeyboardButton(text=TEXTS['back'],callback_data=f'category{callback_data}')
            buttons = [InlineKeyboardButton(text=cat.title, callback_data=f'category{cat.id}') for cat in categories]
            message_id = call.message.message_id if call.message.text else None
            # previous message should be changed or deleted
            delete_message_id = call.message.message_id if not message_id else None

            bot.se_categories(
                chat_id=call.message.chat.id,
                text=category.title,
                buttons=buttons,
                back_button=back_button,
                message_id=message_id,
                delete_message_id=delete_message_id
            )

        elif category.is_leaf:
            if category.products:
                customer = bot.get_customer(user_id=call.from_user.id)

                customer.current_straight_product_list = []
                customer.current_backward_product_list = []

                customer.current_straight_product_list.extend(category.products)
                product = customer.current_straight_product_list.pop()
                customer.current_backward_product_list.append(product)

                customer.save()

                bot.send_product_preview(
                    product=product,
                    chat_id=call.message.chat.id,
                    send_next_button=bool(customer.current_straight_product_list),
                    send_all_products_button=bool(customer.current_straight_product_list),
                    delete_message_id=call.message.message_id
                )
            else:
                kb = bot.create_inline_keyboard([InlineKeyboardButton(
                    text=TEXTS['back'],
                    callback_data=f"category{category.parent.id}"
                )
                ]
                )

                bot.edit_message_text(text=TEXTS['no_products'], reply_markup=kb, chat_id=call.message.chat.id,
                                      message_id=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("cart_item_modification"))
def cart_modification_from_cart(call):
    customer = bot.get_customer(user_id=call.from_user.id)
    cart = customer.get_or_create_current_cart()

    decision_call = call.data[len("cart_item_modification"):]

    if decision_call.startswith('add'):
        product = bot.get_product(id=decision_call[len("add"):])

        item = cart.add_item(product=product)

        reply_markup = bot.get_cart_item_kb(item)
        text = bot.get_cart_item_text(item)

        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=text, reply_markup=reply_markup, parse_mode='html')

        bot.se_total_sum(cart=cart, chat_id=call.message.chat.id, is_edit=True)
    elif decision_call.startswith('sub'):
        product = bot.get_product(id=decision_call[len("sub"):])

        item = cart.sub_item(product=product)

        if item:
            reply_markup = bot.get_cart_item_kb(item)
            text = bot.get_cart_item_text(item)

            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=text, reply_markup=reply_markup, parse_mode='html')

            bot.se_total_sum(cart=cart, chat_id=call.message.chat.id, is_edit=True)
        else:
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.se_total_sum(cart=cart, chat_id=call.message.chat.id, is_edit=True)
    elif decision_call.startswith('del'):
        product = bot.get_product(id=decision_call[len("del"):])

        cart.del_item(product=product)

        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.se_total_sum(cart=cart, chat_id=call.message.chat.id, is_edit=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith("next_product"))
def next_product(call):
    customer = bot.get_customer(user_id=call.from_user.id)
    if call.data != "next_product":
        product = bot.get_product(id=call.data[len("next_product"):])
    else:
        product = customer.current_straight_product_list.pop()
        customer.current_backward_product_list.append(product)

    customer.save()

    bot.send_product_preview(
        product=product,
        chat_id=call.message.chat.id,
        send_prev_button=len(customer.current_backward_product_list) > 1,
        send_next_button=bool(customer.current_straight_product_list),
        delete_message_id=call.message.message_id
    )


@bot.callback_query_handler(func=lambda call: call.data == "previous_product")
def prev_product(call):
    customer = bot.get_customer(user_id=call.from_user.id)
    customer.current_straight_product_list.append(customer.current_backward_product_list.pop())
    product = customer.current_backward_product_list[-1]
    customer.save()

    bot.send_product_preview(
        product=product,
        chat_id=call.message.chat.id,
        send_prev_button=len(customer.current_backward_product_list) > 1,
        send_next_button=bool(customer.current_straight_product_list),
        delete_message_id=call.message.message_id
    )


@bot.callback_query_handler(func=lambda call: call.data == "all_products")
def all_product(call):
    customer = bot.get_customer(user_id=call.from_user.id)
    delete_message_id = call.message.message_id
    for product in (*customer.current_backward_product_list[::-1], *customer.current_straight_product_list[::-1]):
        bot.send_product_preview(
            product=product,
            chat_id=call.message.chat.id,
            send_all_products_button=False,
            delete_message_id=delete_message_id
        )
        delete_message_id = None


@bot.callback_query_handler(func=lambda call: call.data.startswith("product"))
def detailed_product_view(call):
    product_id = call.data[len("product"):]
    product = bot.get_product(id=product_id)
    bot.send_product_full_view(product=product, chat_id=call.message.chat.id, delete_message_id=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("to_cart"))
def to_cart(call):
    customer = bot.get_customer(user_id=call.from_user.id)
    product_id = call.data[len("to_cart"):]
    product = bot.get_product(id=product_id)
    customer.get_or_create_current_cart().add_item(product=product)

    kb = bot.get_general_keyboard(customer)
    bot.send_message(text=TEXTS['added_to_cart'], chat_id=call.message.chat.id, reply_markup=kb)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cart_delete'))
def cart_delete(call):
    if call.data == 'cart_delete':
        buttons = [
            InlineKeyboardButton(text=TEXTS['yes'], callback_data='cart_delete_approval'),
            InlineKeyboardButton(text=TEXTS['cancel'], callback_data='cart_delete_cancelation')
        ]
        kb = bot.create_inline_keyboard(buttons)

        bot.send_message(text=TEXTS['cart_delete_approval'], chat_id=call.message.chat.id, reply_markup=kb)
    elif call.data == 'cart_delete_approval':

        customer = bot.get_customer(user_id=call.from_user.id)
        customer.get_or_create_current_cart().del_all_items()

        kb = bot.get_general_keyboard(customer)
        bot.send_message(text=TEXTS['cart_deleted'], chat_id=call.message.chat.id, reply_markup=kb)

    elif call.data == 'cart_delete_cancelation':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('address_delete'))
def address_delete(call):
    customer = bot.get_customer(user_id=call.from_user.id)
    if call.data.startswith('address_delete_index'):
        address_txt = call.message.text

        callback_addition = f"{customer.address_list.index(address_txt)}_{call.message.message_id}"

        buttons = [
            InlineKeyboardButton(text=TEXTS['yes'], callback_data=f'address_delete_approval_{callback_addition}'),
            InlineKeyboardButton(text=TEXTS['cancel'], callback_data='address_delete_cancelation')
        ]
        kb = bot.create_inline_keyboard(buttons)

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


@bot.callback_query_handler(func=lambda call: call.data.startswith('order_proceed'))
def order_proceed(call):
    customer = bot.get_customer(user_id=call.from_user.id)
    if call.data == 'order_proceed':
        final_message = f"{TEXTS['choose_address']}"
        if not customer.address_list:
            final_message = TEXTS['no_addresses']
        for address in customer.address_list:
            record = [
                InlineKeyboardButton(
                    text=TEXTS['choose_this_address'],
                    callback_data=f'order_proceed_address_chosen'
                ),
                InlineKeyboardButton(
                    text=TEXTS['delete_item'],
                    callback_data=f'address_delete_index'
                )
            ]
            markup = bot.create_inline_keyboard(record)
            bot.send_message(text=str(address), reply_markup=markup, chat_id=call.message.chat.id, parse_mode='html')

        row = [InlineKeyboardButton(text=TEXTS['address_add'], callback_data='address_add')]
        kb = bot.create_inline_keyboard(row)

        bot.send_message(text=final_message, chat_id=call.message.chat.id, reply_markup=kb)
    elif call.data.startswith('order_proceed_address_chosen'):
        address_index = customer.address_list.index(call.message.text)
        cart = customer.get_or_create_current_cart()
        cart.address = customer.address_list[address_index]
        cart.save()

        cart_items_txt = '\n'.join([bot.get_cart_item_text(ci) for ci in cart.items])
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

        buttons = [
            InlineKeyboardButton(text=TEXTS['back'], callback_data='order_proceed'),
            InlineKeyboardButton(text=TEXTS['order_confirmation'], callback_data=f'order_proceed_final_confirmation')
        ]
        kb = bot.create_inline_keyboard(buttons)

        bot.send_message(text=text, chat_id=call.message.chat.id, reply_markup=kb, parse_mode='html')
    elif call.data.startswith('order_proceed_final_confirmation'):
        cart = customer.get_or_create_current_cart()

        cart.archive()

        kb = bot.get_general_keyboard(customer)

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
    customer = bot.get_customer(user_id=message.from_user.id)
    customer.current_straight_product_list = []
    customer.current_backward_product_list = []

    customer.current_straight_product_list.extend(bot.get_discount_products())
    product = customer.current_straight_product_list.pop()
    customer.current_backward_product_list.append(product)
    customer.save()

    bot.send_product_preview(
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
    customer = bot.get_customer(user_id=message.from_user.id)

    if message.reply_to_message.text == TEXTS['address_add_name']:
        customer.current_address_creation_form = bot.get_default_address()
        customer.current_address_creation_form.first_name = message.text.title()
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
        customer.add_address(customer.current_address_creation_form)
        del customer.current_address_creation_form
        customer.save()
        row = [InlineKeyboardButton(text=TEXTS['order_proceed'], callback_data='order_proceed')]
        kb = bot.create_inline_keyboard(row)
        bot.send_message(text=TEXTS['address_add_success'], chat_id=message.chat.id, reply_markup=kb)
    else:
        bot.send_message(text=TEXTS['not_correct'], chat_id=message.chat.id)

        kb = bot.get_general_keyboard(customer)

        bot.send_message(reply_markup=kb,
                         chat_id=message.chat.id,
                         text=f"{message.chat.first_name}, {TEXTS['greeting_message']}",
                         parse_mode='html'
                         )


# @bot.message_handler(func=lambda message: message.text == START_KB['news'])
# def news_handler(message):
#     pass


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
    customer = bot.get_customer(user_id=message.from_user.id)
    kb = bot.get_general_keyboard(customer)

    bot.send_message(reply_markup=kb,
                     chat_id=message.chat.id,
                     text=f"{message.chat.first_name}, {TEXTS['greeting_message']}",
                     parse_mode='html'
                     )
