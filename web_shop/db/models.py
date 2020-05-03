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
        subcategory_obj.parent = self
        self.subcategories.append(subcategory_obj.save())
        self.save()

    @property
    def products(self):
        return Product.objects(category=self)

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

    @classmethod
    def get_discount_products(cls):
        return cls.objects(discount_perc__gt=0)

    def get_price(self):
        return (100 - self.discount_perc) * self.price / 100


class News(me.Document):
    title = me.StringField(min_length=2, max_length=512)
    body = me.StringField(min_length=2)
    pub_date = me.DateTimeField(default=datetime.datetime.now())
    image = me.FileField()


# WTF???
class Texts(me.Document):
    choices = (
        ('Greeting', 'Greeting'),
        ('Buy', 'Buy')
    )

    text = me.StringField(choices=choices)


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


class Customer(me.Document):
    user_id = me.IntField(unique=True)
    username = me.StringField(min_length=1, max_length=256)

    address_list = me.EmbeddedDocumentListField(Address)

    first_name = me.StringField(min_lenght=1, max_length=256)
    last_name = me.StringField(min_lenght=1, max_length=256)

    current_straight_product_list = me.ListField()
    current_backward_product_list = me.ListField()

    current_address_creation_form = Address(
        first_name='dummy',
        last_name='dummy',
        city='dummy',
        phone_number = '0000000000',
        nova_poshta_branch = 1
    )

    def get_or_create_current_cart(self) -> Tuple[bool, 'Cart']:
        created = False
        try:
            cart = Cart.objects.get(customer=self, is_archived=False)
        except DoesNotExist:
            cart = Cart.objects.create(customer=self)

        return cart

    def add_address(self):
        self.address_list.append(self.current_address_creation_form)


class CartItem(me.EmbeddedDocument):
    product = me.ReferenceField('Product')
    quantity = me.IntField(min_value=1, default=1)
    is_archived = me.BooleanField(default=False)
    _order_product_price = me.IntField()

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
