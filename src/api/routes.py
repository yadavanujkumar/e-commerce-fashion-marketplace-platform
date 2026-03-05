from flask import Flask, request, jsonify, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError
import logging
from datetime import timedelta
from werkzeug.exceptions import HTTPException
import sys
import os

# Make the services importable when running through this module
_services_dir = os.path.join(os.path.dirname(__file__), '..', 'core', 'services')
if _services_dir not in sys.path:
    sys.path.insert(0, _services_dir)

from recommendation_service import RecommendationService, Product as RecommendationProduct
from styling_service import StylingService, Product as StylingProduct

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

# Register Blueprint (after all routes including AI endpoints are defined below)
# app.register_blueprint(api_bp) – moved to the bottom of this file

# ---------------------------------------------------------------------------
# AI Services – recommendation and styling engines
# ---------------------------------------------------------------------------

recommendation_service = RecommendationService()
styling_service = StylingService()


def _infer_category(product) -> str:
    """Infer the outfit category from a Product ORM object using the styling engine."""
    proxy = StylingProduct(
        id=product.id,
        name=product.name,
        category="",
        price=product.price,
        description=product.description or "",
    )
    return styling_service.categorise_item(proxy)


def _product_to_rec(product):
    """Convert a SQLAlchemy Product ORM object to a RecommendationProduct."""
    return RecommendationProduct(
        id=product.id,
        name=product.name,
        category=_infer_category(product),
        price=product.price,
        description=product.description or "",
    )


def _product_to_styling(product):
    """Convert a SQLAlchemy Product ORM object to a StylingProduct."""
    return StylingProduct(
        id=product.id,
        name=product.name,
        category=_infer_category(product),
        price=product.price,
        description=product.description or "",
    )


def _refresh_catalogue():
    """Refresh the recommendation catalogue with the latest products from the DB.

    Only adds products that are not already registered, to avoid redundant work.
    """
    products = Product.query.all()
    for p in products:
        if p.id not in recommendation_service._products:
            recommendation_service.add_product(_product_to_rec(p))
    """Serialise a product (ORM or lightweight) to a JSON-friendly dict."""
    return {
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "description": getattr(product, "description", ""),
        "category": getattr(product, "category", ""),
    }


# ---------------------------------------------------------------------------
# AI Recommendation Endpoints
# ---------------------------------------------------------------------------


@api_bp.route('/api/v1/recommendations', methods=['GET'])
@jwt_required()
def get_recommendations():
    """Return personalised product recommendations for the current user.

    Query params:
        n (int, optional): Number of recommendations to return (default 5).

    Returns:
        JSON list of recommended products.
    """
    user_id = str(get_jwt_identity())
    n = request.args.get('n', 5, type=int)

    _refresh_catalogue()

    recommendations = recommendation_service.get_recommendations(user_id, n=n)
    return jsonify([_product_dict(p) for p in recommendations]), 200


@api_bp.route('/api/v1/products/<int:product_id>/similar', methods=['GET'])
def get_similar_products(product_id):
    """Return products similar to the given product.

    Path params:
        product_id: ID of the reference product.

    Query params:
        n (int, optional): Number of similar products to return (default 5).

    Returns:
        JSON list of similar products.
    """
    n = request.args.get('n', 5, type=int)
    product = Product.query.get(product_id)
    if not product:
        raise CustomException("Product not found", 404)

    _refresh_catalogue()

    from recommendation_service import ProductNotFoundError as RecPNFE
    try:
        similar = recommendation_service.get_similar_products(product_id, n=n)
    except RecPNFE:
        raise CustomException("Product not found in recommendation catalogue", 404)

    return jsonify([_product_dict(p) for p in similar]), 200


@api_bp.route('/api/v1/trending', methods=['GET'])
def get_trending():
    """Return trending products, optionally filtered by category.

    Query params:
        n (int, optional): Number of products to return (default 10).
        category (str, optional): Filter results to this category.

    Returns:
        JSON list of trending products.
    """
    n = request.args.get('n', 10, type=int)
    category = request.args.get('category')

    _refresh_catalogue()

    trending = recommendation_service.get_trending(n=n, category=category)
    return jsonify([_product_dict(p) for p in trending]), 200


@api_bp.route('/api/v1/recommendations/record-view', methods=['POST'])
@jwt_required()
def record_product_view():
    """Record that the current user viewed a product.

    Request body:
        product_id (int): ID of the viewed product.

    Returns:
        JSON acknowledgement.
    """
    user_id = str(get_jwt_identity())
    data = request.get_json()
    product_id = data.get('product_id')
    if product_id is None:
        raise CustomException("product_id is required", 400)
    recommendation_service.record_view(user_id, int(product_id))
    return jsonify({"message": "View recorded"}), 200


# ---------------------------------------------------------------------------
# AI Styling Endpoints
# ---------------------------------------------------------------------------


@api_bp.route('/api/v1/styling/outfit', methods=['GET'])
def suggest_outfit():
    """Suggest complementary items to complete an outfit.

    Query params:
        product_id (int): ID of the anchor product.
        max_items (int, optional): Maximum items to include (default 4).

    Returns:
        JSON list of complementary products.
    """
    product_id = request.args.get('product_id', type=int)
    if product_id is None:
        raise CustomException("product_id query parameter is required", 400)

    base_product = Product.query.get(product_id)
    if not base_product:
        raise CustomException("Product not found", 404)

    max_items = request.args.get('max_items', 4, type=int)
    all_products = Product.query.all()
    styling_products = [_product_to_styling(p) for p in all_products]
    base_styling = _product_to_styling(base_product)

    outfit = styling_service.suggest_outfit(base_styling, styling_products, max_items=max_items)
    return jsonify([_product_dict(p) for p in outfit]), 200


@api_bp.route('/api/v1/styling/profile', methods=['GET'])
@jwt_required()
def get_style_profile():
    """Return the style profile for the current user based on their purchases.

    Returns:
        JSON object with preferred_categories, preferred_styles, preferred_colors,
        and avg_price.
    """
    user_id = get_jwt_identity()

    # Retrieve the user's orders and derive their purchase history
    user_orders = Order.query.filter_by(user_id=user_id).all()
    purchased_product_ids = {o.product_id for o in user_orders}
    purchased_products = [
        _product_to_styling(p)
        for p in Product.query.filter(Product.id.in_(purchased_product_ids)).all()
    ] if purchased_product_ids else []

    profile = styling_service.get_style_profile(purchased_products)
    return jsonify(profile), 200


# Register Blueprint after all routes (including AI endpoints) are defined
app.register_blueprint(api_bp)

# Health Check Endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)