from telebot import TeleBot
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from ..db.models import Customer, Category, Product, Address, CartItem, Cart
from .keyboards import START_KB, TEXTS
from typing import List
from copy import copy
from mongoengine import DoesNotExist


class WebShopBot(TeleBot):

    def __init(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def se_categories(self,
                      buttons: List[InlineKeyboardButton],
                      chat_id: int,
                      text: str,
                      back_button: InlineKeyboardButton = None,
                      message_id: int = None,
                      delete_message_id: int = None,
                      **kwargs):

        kb = InlineKeyboardMarkup(row_width=3)

        if back_button:
            kb.row(back_button)

        kb.add(*buttons)

        params = dict(chat_id=chat_id, text=text, reply_markup=kb, **kwargs)

        if message_id:
            params['message_id'] = message_id
            self.edit_message_text(**params)
        else:
            self.send_message(**params)
            if delete_message_id:
                self.delete_message(chat_id=chat_id, message_id=delete_message_id)

    def create_inline_keyboard(self, *buttons: List[InlineKeyboardButton]):

        kb = InlineKeyboardMarkup()

        for row in buttons:
            kb.row(*row)

        return kb

    def root_categories_buttons(self):
        categories = Category.get_root()
        buttons = [InlineKeyboardButton(text=category.title, callback_data=f'category{category.id}') for category in
                   categories]
        return buttons

    def send_product_preview(
            self,
            product: Product,
            chat_id: int,
            send_prev_button: bool = False,
            send_next_button: bool = False,
            send_all_products_button: bool = True,
            delete_message_id: int = None):

        return_to_category = product.category.parent.id if product.category.parent else 'root'

        first_row = [
            InlineKeyboardButton(text=TEXTS['details'],
                                 callback_data=f'product{product.id}'),
            InlineKeyboardButton(text=TEXTS['back_to_category'],
                                 callback_data=f'category{return_to_category}'),
            InlineKeyboardButton(text=TEXTS['add_to_cart'],
                                 callback_data=f'to_cart{product.id}')
        ]

        second_row = []

        if send_prev_button:
            second_row.append(InlineKeyboardButton(text=TEXTS['previous'],
                                                   callback_data=f'previous_product'))

        if send_next_button:
            second_row.append(InlineKeyboardButton(text=TEXTS['next'],
                                                   callback_data=f'next_product'))

        third_row = []

        if send_all_products_button:
            third_row.append(InlineKeyboardButton(text=TEXTS['send_all_products'],
                                                  callback_data=f'all_products'))

        kb = self.create_inline_keyboard(first_row, second_row, third_row)

        caption = f'{product.title}\n\n' \
            f'{f"<s>{product.price}</s> <b>" if product.discount_perc else ""}{product.get_price()}₴' \
            f'{"</b> 🔥" if product.discount_perc else ""}'

        self.send_photo(
            chat_id=chat_id,
            photo=product.image.read(),
            caption=caption,
            disable_notification=True,
            reply_markup=kb,
            parse_mode='html'
        )
        # needed for correct work of image.read()
        product.image.seek(0)

        if delete_message_id:
            self.delete_message(chat_id=chat_id, message_id=delete_message_id)

    def send_product_full_view(
            self,
            product: Product,
            chat_id: int,
            delete_message_id: int
    ):
        first_row = [
            InlineKeyboardButton(text=TEXTS['back'],
                                 callback_data=f'next_product{product.id}'),
            InlineKeyboardButton(text=TEXTS['add_to_cart'],
                                 callback_data=f'to_cart{product.id}')
        ]

        kb = self.create_inline_keyboard(first_row)

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

        self.send_photo(
            chat_id=chat_id,
            photo=product.image.read(),
            caption='\n'.join(caption),
            disable_notification=True,
            reply_markup=kb,
            parse_mode='html'
        )
        product.image.seek(0)

        if delete_message_id:
            self.delete_message(chat_id=chat_id, message_id=delete_message_id)

    def create_customer(
            self,
            user_id: int,
            username: str,
            first_name: str = None,
            last_name: str = None
    ):
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

    def get_general_keyboard(
            self,
            customer: Customer
    ):
        buttons = []
        for key, value in START_KB.items():
            if key != 'cart':
                buttons.append(KeyboardButton(value))
            else:
                buttons.append(KeyboardButton(value.format(f'({customer.get_or_create_current_cart().total_items})')))

        kb = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        kb.add(*buttons)

        return kb

    def get_cart_item_text(
            self,
            item: CartItem
    ):
        text = f'<b>{item.product.title}</b>, ' \
            f'{TEXTS["price"]}: <b>{item.product_price}₴</b>, ' \
            f'{TEXTS["quantity_short"]}: <b>{item.quantity}</b>, ' \
            f'{TEXTS["subsum"]}: <b>{item.item_subsum}₴</b>'
        return text

    def get_cart_item_kb(
            self,
            item: CartItem
    ):
        buttons = []
        buttons.append(InlineKeyboardButton(
            text=TEXTS['product_view'],
            callback_data=f"product{item.product.id}"
        ))
        if item.quantity > 1:
            buttons.append(InlineKeyboardButton(
                text=TEXTS['-1'],
                callback_data=f"cart_item_modification" \
                    f"sub" \
                    f"{item.product.id}"
            ))
        buttons.append(InlineKeyboardButton(
            text=TEXTS['+1'],
            callback_data=f"cart_item_modificationadd{item.product.id}"
        ))
        buttons.append(InlineKeyboardButton(
            text=TEXTS['delete_item'],
            callback_data=f"cart_item_modificationdel{item.product.id}"
        ))

        kb = self.create_inline_keyboard(buttons)

        return kb

    def se_total_sum(
            self,
            cart: Cart,
            chat_id: int,
            edit_message_id: int = None
    ):
        buttons = [
            InlineKeyboardButton(text=TEXTS['cart_delete'], callback_data='cart_delete'),
            InlineKeyboardButton(text=TEXTS['order_proceed'], callback_data='order_proceed')
        ]
        kb = self.create_inline_keyboard(buttons)

        final_message = f"{TEXTS['total_cost']}: <b>{cart.total_cost}₴</b>"
        if not cart.items:
            final_message = TEXTS['no_cart_items']
            kb = None

        if edit_message_id:
            sum_message_id = self.edit_message_text(
                text=final_message,
                chat_id=chat_id,
                message_id=edit_message_id,
                reply_markup=kb,
                parse_mode='html'
            )
            return sum_message_id

        else:
            sum_message_id = self.send_message(
                chat_id=chat_id,
                text=final_message,
                reply_markup=kb,
                parse_mode='html',
                disable_notification=True
            ).message_id

            return sum_message_id

    def get_category(self, **kwargs):
        return Category.objects.get(**kwargs)

    def get_product(self, **kwargs):
        return Product.objects.get(**kwargs)

    def get_customer(self, **kwargs):
        return Customer.objects.get(**kwargs)

    def get_discount_products(self):
        return Product.get_discount_products()

    def get_default_address(self):
        return Address(
            first_name='dummy',
            last_name='dummy',
            city='dummy',
            phone_number='0000000000',
            nova_poshta_branch=1
        )
