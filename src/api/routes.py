from flask import Flask, request, jsonify, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from datetime import datetime, timedelta
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
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'postgresql://user:password@localhost/ecommerce'
)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'change-me-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
app.config['CORS_HEADERS'] = 'Content-Type'

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define Blueprints
api_bp = Blueprint('api', __name__)

# Pagination defaults
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100

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

# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(60), nullable=True)
    brand = db.Column(db.String(80), nullable=True)
    size = db.Column(db.String(20), nullable=True)
    color = db.Column(db.String(40), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    total_price = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ---------------------------------------------------------------------------
# Schemas for validation
# ---------------------------------------------------------------------------

class UserSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=1))
    email = fields.Email(required=False)
    password = fields.Str(required=True, validate=validate.Length(min=6))

class ProductSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(required=False)
    price = fields.Float(required=True, validate=validate.Range(min=0.01))
    category = fields.Str(required=False)
    brand = fields.Str(required=False)
    size = fields.Str(required=False)
    color = fields.Str(required=False)
    image_url = fields.Url(required=False)
    stock_quantity = fields.Int(required=False, validate=validate.Range(min=0))

class ProductUpdateSchema(Schema):
    name = fields.Str(required=False, validate=validate.Length(min=1))
    description = fields.Str(required=False)
    price = fields.Float(required=False, validate=validate.Range(min=0.01))
    category = fields.Str(required=False)
    brand = fields.Str(required=False)
    size = fields.Str(required=False)
    color = fields.Str(required=False)
    image_url = fields.Url(required=False)
    stock_quantity = fields.Int(required=False, validate=validate.Range(min=0))

class OrderSchema(Schema):
    product_id = fields.Int(required=True)
    quantity = fields.Int(required=False, validate=validate.Range(min=1), load_default=1)

# ---------------------------------------------------------------------------
# Helper: pagination
# ---------------------------------------------------------------------------

def _paginate_query(query):
    """Apply pagination to a SQLAlchemy query and return (items, meta)."""
    page = request.args.get('page', DEFAULT_PAGE, type=int)
    per_page = min(
        request.args.get('per_page', DEFAULT_PER_PAGE, type=int),
        MAX_PER_PAGE,
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    meta = {
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
    }
    return pagination.items, meta

# ---------------------------------------------------------------------------
# User Authentication
# ---------------------------------------------------------------------------

@api_bp.route('/api/v1/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        UserSchema().load(data)
        new_user = User(
            username=data['username'],
            email=data.get('email'),
        )
        new_user.set_password(data['password'])
        db.session.add(new_user)
        db.session.commit()
        return jsonify({
            "message": "User registered successfully",
            "user": {"id": new_user.id, "username": new_user.username},
        }), 201
    except ValidationError as err:
        raise CustomException(f"Validation error: {err.messages}", 422)
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        db.session.rollback()
        raise CustomException("Internal server error", 500)

@api_bp.route('/api/v1/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200
    else:
        raise CustomException("Invalid credentials", 401)

# ---------------------------------------------------------------------------
# Product Management
# ---------------------------------------------------------------------------

def _serialize_product(product):
    """Serialise a Product ORM object to a JSON-friendly dict."""
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "category": product.category,
        "brand": product.brand,
        "size": product.size,
        "color": product.color,
        "image_url": product.image_url,
        "stock_quantity": product.stock_quantity,
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
    }


@api_bp.route('/api/v1/products', methods=['GET'])
def get_products():
    """List products with optional filtering and pagination.

    Query params:
        category, brand, color, size: Filter by field value.
        min_price, max_price: Filter by price range.
        q: Search by name (case-insensitive partial match).
        sort: Sort field (price, name, created_at). Prefix with - for descending.
        page, per_page: Pagination controls.
    """
    query = Product.query

    # Filtering
    category = request.args.get('category')
    brand = request.args.get('brand')
    color = request.args.get('color')
    size = request.args.get('size')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    search = request.args.get('q')

    if category:
        query = query.filter(Product.category.ilike(f'%{category}%'))
    if brand:
        query = query.filter(Product.brand.ilike(f'%{brand}%'))
    if color:
        query = query.filter(Product.color.ilike(f'%{color}%'))
    if size:
        query = query.filter(Product.size == size)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))

    # Sorting
    sort = request.args.get('sort', 'created_at')
    descending = sort.startswith('-')
    sort_field = sort.lstrip('-')
    column = getattr(Product, sort_field, Product.created_at)
    query = query.order_by(column.desc() if descending else column.asc())

    items, meta = _paginate_query(query)
    return jsonify({"products": [_serialize_product(p) for p in items], "meta": meta}), 200


@api_bp.route('/api/v1/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Return a single product by ID."""
    product = Product.query.get(product_id)
    if not product:
        raise CustomException("Product not found", 404)
    return jsonify(_serialize_product(product)), 200


@api_bp.route('/api/v1/products', methods=['POST'])
@jwt_required()
def create_product():
    try:
        data = request.get_json()
        ProductSchema().load(data)
        new_product = Product(
            name=data['name'],
            description=data.get('description'),
            price=data['price'],
            category=data.get('category'),
            brand=data.get('brand'),
            size=data.get('size'),
            color=data.get('color'),
            image_url=data.get('image_url'),
            stock_quantity=data.get('stock_quantity', 0),
        )
        db.session.add(new_product)
        db.session.commit()
        return jsonify({
            "message": "Product created successfully",
            "product": _serialize_product(new_product),
        }), 201
    except ValidationError as err:
        raise CustomException(f"Validation error: {err.messages}", 422)
    except Exception as e:
        logger.error(f"Error during product creation: {str(e)}")
        db.session.rollback()
        raise CustomException("Internal server error", 500)


@api_bp.route('/api/v1/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    """Update a product by ID."""
    product = Product.query.get(product_id)
    if not product:
        raise CustomException("Product not found", 404)
    try:
        data = request.get_json()
        ProductUpdateSchema().load(data)
        for field in ('name', 'description', 'price', 'category', 'brand',
                      'size', 'color', 'image_url', 'stock_quantity'):
            if field in data:
                setattr(product, field, data[field])
        db.session.commit()
        return jsonify({
            "message": "Product updated successfully",
            "product": _serialize_product(product),
        }), 200
    except ValidationError as err:
        raise CustomException(f"Validation error: {err.messages}", 422)
    except Exception as e:
        logger.error(f"Error during product update: {str(e)}")
        db.session.rollback()
        raise CustomException("Internal server error", 500)


@api_bp.route('/api/v1/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    """Delete a product by ID."""
    product = Product.query.get(product_id)
    if not product:
        raise CustomException("Product not found", 404)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted successfully"}), 200

# ---------------------------------------------------------------------------
# Order Management
# ---------------------------------------------------------------------------

def _serialize_order(order):
    """Serialise an Order ORM object to a JSON-friendly dict."""
    return {
        "id": order.id,
        "user_id": order.user_id,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "total_price": order.total_price,
        "status": order.status,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }


@api_bp.route('/api/v1/orders', methods=['POST'])
@jwt_required()
def create_order():
    user_id = get_jwt_identity()
    try:
        data = request.get_json()
        OrderSchema().load(data)
    except ValidationError as err:
        raise CustomException(f"Validation error: {err.messages}", 422)

    product = Product.query.get(data['product_id'])
    if not product:
        raise CustomException("Product not found", 404)

    quantity = data.get('quantity', 1)
    if product.stock_quantity < quantity:
        raise CustomException("Insufficient stock", 400)

    total_price = round(product.price * quantity, 2)

    new_order = Order(
        user_id=user_id,
        product_id=product.id,
        quantity=quantity,
        total_price=total_price,
        status='pending',
    )
    product.stock_quantity -= quantity
    db.session.add(new_order)
    db.session.commit()
    return jsonify({
        "message": "Order created successfully",
        "order": _serialize_order(new_order),
    }), 201


@api_bp.route('/api/v1/orders', methods=['GET'])
@jwt_required()
def get_orders():
    """List orders for the current user with pagination."""
    user_id = get_jwt_identity()
    query = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc())
    status_filter = request.args.get('status')
    if status_filter:
        query = query.filter(Order.status == status_filter)
    items, meta = _paginate_query(query)
    return jsonify({"orders": [_serialize_order(o) for o in items], "meta": meta}), 200


@api_bp.route('/api/v1/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    """Return a single order (only if it belongs to the current user)."""
    user_id = get_jwt_identity()
    order = Order.query.filter_by(id=order_id, user_id=user_id).first()
    if not order:
        raise CustomException("Order not found", 404)
    return jsonify(_serialize_order(order)), 200


@api_bp.route('/api/v1/orders/<int:order_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_order(order_id):
    """Cancel a pending order and restore stock."""
    user_id = get_jwt_identity()
    order = Order.query.filter_by(id=order_id, user_id=user_id).first()
    if not order:
        raise CustomException("Order not found", 404)
    if order.status != 'pending':
        raise CustomException("Only pending orders can be cancelled", 400)
    order.status = 'cancelled'
    product = Product.query.get(order.product_id)
    if product:
        product.stock_quantity += order.quantity
    db.session.commit()
    return jsonify({
        "message": "Order cancelled successfully",
        "order": _serialize_order(order),
    }), 200

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


def _product_dict(product):
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