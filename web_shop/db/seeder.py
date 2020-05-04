from random import randint
from .models import (
    Category,
    Product,
    Characteristics
)

import requests, io

def create_category(**kwargs):
    requirede_fields = ('title', 'slug')
    [kwargs[arg] for arg in requirede_fields]

    return Category.objects.create(**kwargs)


def create_product(**kwargs):
    requirede_fields = ('title', 'slug', 'price', 'image', 'category')
    [kwargs[arg] for arg in requirede_fields]

    image = kwargs['image']
    del kwargs['image']

    product = Product.objects.create(**kwargs)
    product.image.put(image, content_type='image/jpeg')
    product.save()
    return product


def get_category_data(unique_arg):
    return {
        'title': f'Category {unique_arg}',
        'slug': f'slug-{unique_arg}',
        'description': f'some description {unique_arg}'
    }

def get_product_data():
    title = input('title: ').strip()
    slug = input('slug: ').strip()
    description = input('description: ').strip()
    price = float(input('price: ').strip())
    photo_url = input('photo_url: ').strip()
    category_slug = input('category_slug: ').strip()
    discount_perc = input('discount_perc: ').strip()
    characteristics_height = input('characteristics_height: ').strip()
    characteristics_width = input('characteristics_width: ').strip()
    characteristics_depth = input('characteristics_depth: ').strip()
    characteristics_weight = input('characteristics_weight: ').strip()

    discount_perc = None if not discount_perc else int(discount_perc)
    characteristics_width = None if not characteristics_width else float(characteristics_width)
    characteristics_depth = None if not characteristics_depth else float(characteristics_depth)
    characteristics_weight = None if not characteristics_weight else float(characteristics_weight)
    characteristics_weight = None if not characteristics_weight else float(characteristics_weight)

    image = requests.get(photo_url).content
    category = Category.objects.get(slug=category_slug)
    characteristics = None
    if any((characteristics_height, characteristics_width, characteristics_depth, characteristics_weight)):
        characteristics = Characteristics(
            height=characteristics_height,
            width=characteristics_width,
            depth=characteristics_depth,
            weight=characteristics_weight
        )

    return_ = {
        'title': title,
        'slug': slug,
        'price': price,
        'image': image,
        'category': category
    }

    if characteristics:
        return_['characteristics'] = characteristics
    if description:
        return_['description'] = description
    if discount_perc:
        return_['discount_perc'] = discount_perc

    return return_