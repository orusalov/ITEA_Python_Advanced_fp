from flask_restful import Resource
from ..db.models import Characteristics, Category, Product, Customer, Cart
from mongoengine import DoesNotExist, ValidationError as VE
from .schemas import (
    CategorySchema,
    CategoryPostSchema,
    CategoryPutSchema,
    ProductSchema,
    ProductPostSchema,
    ProductPutSchema,
    CustomerSchema,
    OrderSchema,
    ValidationError
)
from flask import request
import requests


class CategoryResource(Resource):

    def get(self, slug=None):
        if slug:
            try:
                category = Category.objects.get(slug=slug)
            except (DoesNotExist, VE):
                return 'No such category'
            return CategorySchema().dump(category)
        else:
            categories = Category.objects()
            return CategorySchema().dump(categories, many=True)

    def post(self):
        try:
            data = CategoryPostSchema().load(request.get_json())
        except ValidationError as err:
            return str(err)

        parent = None
        if data.get('parent'):
            parent = Category.objects.get(slug=data['parent'])
            del data['parent']

        subcategories = []
        if data.get('subcategories'):
            subcategories = data['subcategories']
            del data['subcategories']

        try:
            category = Category.objects.create(**data)
        except VE as err:
            return str(err)

        if parent:
            category.add_parent(parent)

        for c in subcategories:
            try:
                subcategory = Category.objects.get(slug=c.strip())
                category.add_subcategory(subcategory)
            except (DoesNotExist, VE):
                continue

        return CategorySchema().dump(category)

    def put(self, slug):
        category = Category.objects.get(slug=slug)

        try:
            data = CategoryPutSchema().load(request.get_json())
        except ValidationError as err:
            return str(err)

        parent = None
        if data.get('parent'):
            parent = Category.objects.get(slug=data['parent'])
            del data['parent']

        subcategories = []
        if data.get('subcategories'):
            for c in data['subcategories']:
                try:
                    subcategory = Category.objects.get(slug=c.strip())
                except (DoesNotExist, VE):
                    continue

                subcategories.append(subcategory)

            del data['subcategories']
        if data:
            category.modify(**data)

        if parent and parent != category.parent:
            category.parent.del_subcategory(category)
            category.add_parent(parent)

        if subcategories and subcategories != category.subcategories:
            subs_to_remove = set(category.subcategories) - set(subcategories)
            subs_to_add = set(subcategories) - set(category.subcategories)

            # Remove subcategories, that were in old list and not in new
            for rem in subs_to_remove:
                category.del_subcategory(rem)

            # Add difference
            for add_ in subs_to_add:
                category.add_subcategory(add_)

        category.save()

        return CategorySchema().dump(category)

    def delete(self, slug):
        category = Category.objects.get(slug=slug)

        if category.subcategories:
            return 'Category can\'t be deleted while has subcategories'

        if category.parent:
            category.parent.del_subcategory(category)

        category.delete()
        return f'Deleted {slug}'


class ProductResource(Resource):

    def get(self, slug=None):
        if slug:
            try:
                product = Product.objects.get(slug=slug)
            except (DoesNotExist, VE):
                return 'No such product'

            return ProductSchema().dump(product)
        else:
            products = Product.objects()
            return ProductSchema().dump(products, many=True)

    def post(self):
        try:
            data = ProductPostSchema().load(request.get_json())
        except ValidationError as err:
            return str(err)

        data['category'] = Category.objects.get(slug=data['category'])
        data['image'] = requests.get(data['image']).content

        try:
            product = Product.objects.create(**data)
        except VE as err:
            return str(err)

        return ProductSchema().dump(product)

    def put(self, slug):
        product = Product.objects.get(slug=slug)

        try:
            data = ProductPutSchema().load(request.get_json())
        except ValidationError as err:
            return str(err)

        if data.get('category'):
            data['category'] = Category.objects.get(slug=data['category'])
        if data.get('image'):
            data['image'] = requests.get(data['image']).content

        if data:
            product.modify(**data)
        return ProductSchema().dump(product)

    def delete(self, slug):
        product = Product.objects.get(slug=slug)
        product.archive()

        return f'Archived {slug}'


class CustomerResource(Resource):

    def get(self, username=None):
        if id:
            try:
                customer = Customer.objects.get(username=username, is_archived=False)
            except (DoesNotExist, VE):
                return 'No such customer'

            return CustomerSchema().dump(customer)
        else:
            customers = Customer.objects(is_archived=False)
            return CustomerSchema().dump(customers, many=True)

    def delete(self, id):
        customer = Customer.objects.get(id=id)
        customer.archive()

        return f'Archived {id}'


class OrderResource(Resource):

    def get(self, id=None):
        if id:
            try:
                order = Cart.objects.get(id=id, is_archived=True)
            except (DoesNotExist, VE):
                return 'No such order'

            return OrderSchema().dump(order)
        else:
            orders = Cart.objects(is_archived=True)
            return OrderSchema().dump(orders, many=True)
