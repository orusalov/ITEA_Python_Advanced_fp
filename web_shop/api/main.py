from flask import Flask
from flask_restful import Api
from .resources import *

app = Flask(__name__)
api = Api(app)

api.add_resource(CategoryResource, '/category', '/category/<slug>')
api.add_resource(ProductResource, '/product', '/product/<slug>')
api.add_resource(CustomerResource, '/customer', '/customer/<id>')
api.add_resource(OrderResource, '/order', '/order/<id>')

if __name__ == '__main__':
    app.run(debug=True)