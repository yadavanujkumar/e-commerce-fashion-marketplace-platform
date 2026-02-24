from flask import Flask, request, jsonify, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError
import logging
from datetime import timedelta
from werkzeug.exceptions import HTTPException

# Initialize Flask app and extensions
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/ecommerce'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
app.config['CORS_HEADERS'] = 'Content-Type'

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define Blueprints
api_bp = Blueprint('api', __name__)

# Custom Exception Handling
class CustomException(Exception):
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code

@app.errorhandler(CustomException)
def handle_custom_exception(error):
    response = jsonify({'error': error.message})
    response.status_code = error.status_code
    return response

@app.errorhandler(HTTPException)
def handle_http_exception(error):
    response = jsonify({'error': error.description})
    response.status_code = error.code
    return response

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

# Schemas for validation
class UserSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=1))
    password = fields.Str(required=True, validate=validate.Length(min=6))

class ProductSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(required=False)
    price = fields.Float(required=True)

# User Authentication
@api_bp.route('/api/v1/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        UserSchema().load(data)
        new_user = User(username=data['username'], password=data['password'])  # Password should be hashed
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except ValidationError as err:
        raise CustomException(f"Validation error: {err.messages}", 422)
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        raise CustomException("Internal server error", 500)

@api_bp.route('/api/v1/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and user.password == data['password']:  # Password should be verified with hashing
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200
    else:
        raise CustomException("Invalid credentials", 401)

# Product Management
@api_bp.route('/api/v1/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    product_schema = ProductSchema(many=True)
    return jsonify(product_schema.dump(products)), 200

@api_bp.route('/api/v1/products', methods=['POST'])
@jwt_required()
def create_product():
    try:
        data = request.get_json()
        ProductSchema().load(data)
        new_product = Product(name=data['name'], description=data.get('description'), price=data['price'])
        db.session.add(new_product)
        db.session.commit()
        return jsonify({"message": "Product created successfully"}), 201
    except ValidationError as err:
        raise CustomException(f"Validation error: {err.messages}", 422)
    except Exception as e:
        logger.error(f"Error during product creation: {str(e)}")
        raise CustomException("Internal server error", 500)

# Order Management
@api_bp.route('/api/v1/orders', methods=['POST'])
@jwt_required()
def create_order():
    user_id = get_jwt_identity()
    data = request.get_json()
    product = Product.query.get(data['product_id'])
    if not product:
        raise CustomException("Product not found", 404)

    new_order = Order(user_id=user_id, product_id=product.id)
    db.session.add(new_order)
    db.session.commit()
    return jsonify({"message": "Order created successfully"}), 201

# Register Blueprint
app.register_blueprint(api_bp)

# Health Check Endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)