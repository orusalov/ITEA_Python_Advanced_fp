import mongoengine as me
import datetime
from .db_config import DB_CONFIG
from typing import Tuple

me.connect(**DB_CONFIG)


class Characteristics(me.EmbeddedDocument):
    height = me.DecimalField()
    width = me.DecimalField()
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


class Texts(me.Document):
    choices = (
        ('Greeting', 'Greeting'),
        ('Buy', 'Buy')
    )

    text = me.StringField(choices=choices)


class Customer(me.Document):
    user_id = me.IntField(unique=True)
    username = me.StringField(min_length=1, max_length=256)

    phone_number = me.StringField(min_length=9)
    address = me.StringField()
    first_name = me.StringField(min_lenght=1, max_length=256)
    last_name = me.StringField(min_lenght=1, max_length=256)
    age = me.IntField(min_value=12, max_value=99)

    def get_or_create_current_cart(self) -> Tuple[bool, 'Cart']:
        created = False
        cart = Cart.objects.get(customer=self, is_archived=False)

        if cart:
            return created, cart
        else:
            created = True
            return created, Cart.objects.create(customer=self)


class CartItem(me.EmbeddedDocument):
    product = me.ReferenceField('Product')
    quantity = me.IntField(min_value=1, default=1)

    @property
    def price(self):
        return self.product.get_price() * self.quantity




class Cart(me.Document):
    customer = me.ReferenceField(Customer)
    cart_items = me.EmbeddedDocumentListField(CartItem)
    is_archived = me.BooleanField(default=False)

    def add_item(self, product: Product):
        cart_item = CartItem()
        cart_item.product = product

        if cart_item in self.cart_items:
            self.cart_items[self.cart_items.index(cart_item)].quantity += 1
        else:
            self.cart_items.append(cart_item)

        self.save()

    def archive(self):
        self.is_archived = True
        self.save()