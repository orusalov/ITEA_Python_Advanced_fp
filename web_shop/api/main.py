from flask import Flask
from flask_restful import Api
from .resources import *

app = Flask(__name__)
api = Api(app)

api.add_resource(CategoryResource, 'api/category', 'api/category/<slug>')
api.add_resource(ProductResource, 'api/product', 'api/product/<slug>')
api.add_resource(CustomerResource, 'api/customer', 'api/customer/<id>')
api.add_resource(OrderResource, 'api/order', 'api/order/<id>')
