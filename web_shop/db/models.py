import mongoengine as me
import datetime
from .db_config import DB_CONFIG
from typing import Tuple
from mongoengine import DoesNotExist
from ..bot.keyboards import TEXTS

me.connect(**DB_CONFIG)


class Characteristics(me.EmbeddedDocument):
    height = me.DecimalField()
    width = me.DecimalField()
    depth = me.DecimalField()
    weight = me.DecimalField()


class Category(me.Document):
    title = me.StringField(min_length=2, max_length=256, required=True)
    description = me.StringField(min_length=2)
    slug = me.StringField(min_length=2, max_length=512, unique=True, required=True)
    subcategories = me.ListField(me.ReferenceField('self'))  # Category
    parent = me.ReferenceField('self')

    def add_subcategory(self, subcategory_obj):
        if not self.subcategories.count(subcategory_obj):
            subcategory_obj.parent = self
            self.subcategories.append(subcategory_obj.save())
            self.save()

    def del_subcategory(self, subcategory_obj):
        if self.subcategories.count(subcategory_obj):
            subcategory_obj.parent = None
            self.subcategories.remove(subcategory_obj.save())
            self.save()

    def add_parent(self, parent):
        parent.add_subcategory(self)

    @property
    def products(self):
        return Product.objects(category=self, is_archived=False)

    @property
    def is_root(self):
        return self.parent is None

    @property
    def is_leaf(self):
        return not self.subcategories

    @classmethod
    def get_root(cls):
        return cls.objects(parent=None)


class Product(me.Document):
    title = me.StringField(min_length=2, max_length=256, required=True)
    description = me.StringField(min_length=2)
    slug = me.StringField(min_length=2, max_length=512, unique=True, required=True)
    price = me.DecimalField(min_value=0, precision=2, force_string=True, required=True)
    characteristics = me.EmbeddedDocumentField(Characteristics)
    discount_perc = me.IntField(min_value=0, max_value=100, default=0)
    category = me.ReferenceField(Category)
    image = me.FileField()
    is_archived = me.BooleanField(required=True, default=False)

    @classmethod
    def get_discount_products(cls):
        return cls.objects(discount_perc__gt=0, is_archived=False)

    def get_price(self):
        return (100 - self.discount_perc) * self.price / 100

    def archive(self):
        self.is_archived = True
        self.save()


# class Texts(me.Document):
#     choices = (
#         ('greeting_message', 'Приветсвтую в телеграм магазине 🏬'),
#         ('categories_message', 'Выберите категорию'),
#         ('back', '⏮️Назад'),
#         ('back_to_category', '⬆️Наверх⬆️'),
#         ('add_to_cart', 'Добавить в 🛒'),
#         ('price', 'Цена'),
#         ('details', 'Подробнее'),
#         ('next', 'Следующий продукт ⏭️'),
#         ('previous', '⏮️Предыдущий продукт'),
#         ('send_all_products', 'Отправить все товары категории'),
#         ('characteristics', 'Характеристики'),
#         ('height', 'Высота'),
#         ('width', 'Ширина'),
#         ('depth', 'Глубина'),
#         ('weight', 'Вес'),
#         ('discount', 'Скидка'),
#         ('added_to_cart', 'Добавлено в 🛒'),
#         ('no_cart_items', 'В корзине пусто'),
#         ('delete_item', 'Удалить 🗑️'),
#         ('-1', '-1'),
#         ('+1', '+1'),
#         ('quantity_short', 'Кол-во'),
#         ('subsum', 'Сумма'),
#         ('total_cost', 'Итого'),
#         ('product_view', '🔍'),
#         ('start_cart_text', 'Корзина имеет {} позиции'),
#         ('cart_delete', 'Удалить корзину'),
#         ('cart_deleted', 'Корзина удалена'),
#         ('order_proceed', 'Оформить заказ'),
#         ('yes', 'Да'),
#         ('cancel', 'Отмена'),
#         ('cart_delete_approval', 'Вы уверены, что хотите удалить корзину?'),
#         ('address_delete_approval', 'Вы уверены, что хотите удалить адрес?'),
#         ('choose_address', 'Выберите адрес доставки или создайте новый'),
#         ('choose_this_address', 'Выбрать ✅'),
#         ('no_addresses', 'Нет сохраненных адресов'),
#         ('address_disclaimer',
#          'Мы осуществляем доставку только по Украине Новой Почтой\nдля отправки нам нужны реквизиты'),
#         ('address_NP_branch', 'Отделение Новой Почты:'),
#         ('address_add', 'Добавить адрес'),
#         ('address_add_name', 'Имя получателя:'),
#         ('address_add_surname', 'Фамилия получателя:'),
#         ('address_add_city', 'Населенный пункт:'),
#         ('address_add_phone', 'Номер получателя:'),
#         ('address_add_NP_number', 'Номер отделения Новой Почты:'),
#         ('address_add_success', 'Адрес добавлен успешно'),
#         ('shipping_address', 'Адрес доставки:'),
#         ('order_confirmation', 'Заказ подтверждаю'),
#         ('order_ended', 'Заказ успешно оформлен\nВ ближайшее время мы с вами свяжемся.\n😊😊😊 Хорошего дня 😊😊😊'),
#         ('not_correct', 'Некорректный ввод')
#     )
#
#     text = me.StringField(choices=choices)


class Address(me.EmbeddedDocument):
    first_name = me.StringField(min_lenght=1, max_length=256, required=True)
    last_name = me.StringField(min_lenght=1, max_length=256, required=True)
    city = me.StringField(min_lenght=3, max_length=256, required=True)
    phone_number = me.StringField(regex='^0\d{9}$', required=True)
    nova_poshta_branch = me.IntField(min_value=1, max_value=100000, required=True)

    def __str__(self):
        name = f'{self.first_name} {self.last_name}'
        np = f"{TEXTS['address_NP_branch']} {self.city}, #{self.nova_poshta_branch}"
        txt = '\n'.join((name, self.phone_number, np))

        return txt

    def __eq__(self, other):
        return str(self) == str(other)


class Customer(me.Document):
    user_id = me.IntField(unique=True)
    username = me.StringField(min_length=1, max_length=256)

    address_list = me.EmbeddedDocumentListField(Address)

    first_name = me.StringField(min_lenght=1, max_length=256)
    last_name = me.StringField(min_lenght=1, max_length=256)

    is_archived = me.BooleanField(default=False)

    current_straight_product_list = me.ListField()
    current_backward_product_list = me.ListField()

    current_address_creation_form = me.EmbeddedDocumentField(Address)

    def get_or_create_current_cart(self) -> Tuple[bool, 'Cart']:
        created = False
        try:
            cart = Cart.objects.get(customer=self, is_archived=False)
        except DoesNotExist:
            cart = Cart.objects.create(customer=self)

        return cart

    def add_address(self, address: Address):
        self.address_list.append(address)

    def archive(self):
        self.is_archived = True
        self.save()


class CartItem(me.EmbeddedDocument):
    product = me.ReferenceField('Product')
    quantity = me.IntField(min_value=1, default=1)
    is_archived = me.BooleanField(default=False)
    _order_product_price = me.DecimalField()

    @property
    def product_price(self):
        if self.is_archived:
            return self._order_product_price
        else:
            return self.product.get_price()

    @property
    def item_subsum(self):
        return self.product_price * self.quantity

    def __contains__(self, item):
        return self.product == item.product

    def __eq__(self, other):
        return self.product == other.product

    def archive(self):
        self._order_product_price = self.product.get_price()
        self.is_archived = True


class Cart(me.Document):
    customer = me.ReferenceField(Customer)
    items = me.EmbeddedDocumentListField(CartItem)
    is_archived = me.BooleanField(default=False)
    address = me.EmbeddedDocumentField(Address)

    _active_sum_message_id = me.IntField()

    @property
    def total_cost(self):
        return sum([cart_item.item_subsum for cart_item in self.items])

    @property
    def total_items(self):
        return sum([cart_item.quantity for cart_item in self.items])

    @property
    def distinct_items(self):
        return len(self.items)

    def add_item(self, product: Product):
        cart_item = CartItem()
        cart_item.product = product

        if cart_item in self.items:
            self.items[self.items.index(cart_item)].quantity += 1
        else:
            self.items.append(cart_item)

        self.save()
        return self.items[self.items.index(cart_item)]

    def sub_item(self, product: Product):
        search_item = CartItem()
        search_item.product = product

        if search_item in self.items:
            cart_item = self.items[self.items.index(search_item)]
            cart_item.quantity -= 1

            if cart_item.quantity == 0:
                cart_item = None
                self.del_item(product)

            self.save()

        return cart_item

    def del_item(self, product: Product):
        cart_item = CartItem()
        cart_item.product = product

        if cart_item in self.items:
            del self.items[self.items.index(cart_item)]

        self.save()

    def del_all_items(self):
        self.items = []
        self.save()

    def archive(self):

        for order_item in self.items:
            order_item.archive()

        self.is_archived = True
        self.save()
