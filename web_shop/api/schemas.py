from marshmallow import Schema, fields, ValidationError, validates, validates_schema
import re


def validate_slug(value):
    p = re.compile('^[A-Za-z_]+$')
    is_valid = bool(p.fullmatch(value))
    if not is_valid:
        raise ValidationError('Value should be ^[A-Za-z_]+$')


class CategorySchema(Schema):
    id = fields.String(dump_only=True)

    title = fields.String(required=True, min_length=2, max_length=256)
    slug = fields.String(required=True, min_length=2, max_length=512, validate=validate_slug)
    description = fields.String(min_length=2)
    subcategories = fields.List(fields.Nested(lambda: CategorySchema(exclude=("parent",)), dump_only=True))
    parent = fields.Nested(lambda: CategorySchema(exclude=("subcategories",)), dump_only=True)

    @validates_schema
    def validate_curator_requires_faculty(self, data, **kwargs):
        if 'subcategories' not in data and 'parent' not in data:
            raise ValidationError('Category at least has to have parent or subcategories')


class CategoryPostSchema(CategorySchema):
    subcategories = fields.List(fields.String(min_length=2, max_length=256))
    parent = fields.String(min_length=2, max_length=256, validate=validate_slug)

    @validates('subcategories')
    def validate_marks(self, value):
        for sub in value:
            validate_slug(sub)


class CategoryPutSchema(CategoryPostSchema):
    def __init__(self):
        super().__init__()
        self.fields['title'].required = False
        self.fields['slug'].required = False


class CharacteristicsSchema(Schema):
    height = fields.Float(validate=lambda v: v > 0)
    width = fields.Float(validate=lambda v: v > 0)
    depth = fields.Float(validate=lambda v: v > 0)
    weight = fields.Float(validate=lambda v: v > 0)


class ProductSchema(Schema):
    id = fields.String(dump_only=True)

    title = fields.String(required=True, min_length=2, max_length=256)
    slug = fields.String(required=True, min_length=2, max_length=512, validate=validate_slug)
    description = fields.String(min_length=2)
    price = fields.Float(required=True, validate=lambda v: v >= 0)
    discount_perc = fields.Int(required=True, validate=lambda card: 0 <= card <= 100)
    characteristics = fields.Nested(CharacteristicsSchema)
    category = fields.Nested(CategorySchema, required=True)
    image = fields.String(required=True)


class ProductPostSchema(ProductSchema):
    def __init__(self):
        super().__init__()
        self.fields['discount_perc'].required = False

    category = fields.String(min_length=2, max_length=256, validate=validate_slug, required=True)
    image = fields.String(min_length=2, max_length=256, required=True)


class ProductPutSchema(ProductPostSchema):
    def __init__(self):
        super().__init__()
        self.fields['slug'].required = False
        self.fields['title'].required = False
        self.fields['price'].required = False
        self.fields['discount_perc'].required = False
        self.fields['category'].required = False
        self.fields['image'].required = False


class AdressSchema(Schema):
    id = fields.String(dump_only=True)

    first_name = fields.String(required=True, min_lenght=1, max_length=256)
    last_name = fields.String(required=True, min_lenght=1, max_length=256)
    city = fields.String(min_lenght=3, max_length=256, required=True)
    phone_number = fields.String(required=True)
    nova_poshta_branch = fields.Int(required=True, validate=lambda v: 0 < v <= 100000)

    @validates
    def validate_phone_number(self, value):
        p = re.compile('^0\d{9}$')
        is_valid = bool(p.fullmatch(value))
        if not is_valid:
            raise ValidationError('Value should be in format 0123456789')


class CustomerSchema(Schema):
    id = fields.String(dump_only=True)

    user_id = fields.Int(required=True)
    username = fields.String(min_length=1, max_length=256)

    address_list = fields.List(fields.Nested(AdressSchema))

    first_name = fields.String(min_length=1, max_length=256)
    last_name = fields.String(min_length=1, max_length=256)


class OrderItemSchema(Schema):
    product = fields.Nested(lambda: ProductSchema(exclude=('discount_perc', 'category', 'price')))
    quantity = fields.Int(required=True, validate=lambda v: v > 0)
    product_price = fields.Float(required=True, validate=lambda v: v >= 0)
    item_subsum = fields.Float(required=True, validate=lambda v: v >= 0)


class OrderSchema(Schema):
    id = fields.String(dump_only=True)
    customer = fields.Nested(lambda: CustomerSchema(exclude=("address_list",)), required=True)
    items = fields.List(fields.Nested(OrderItemSchema, required=True))
    address = fields.Nested(AdressSchema, required=True)
    total_cost = fields.Float(required=True, validate=lambda v: v >= 0)
    total_items = fields.Int(required=True, validate=lambda v: v > 0)
    distinct_items = fields.Int(required=True, validate=lambda v: v > 0)
