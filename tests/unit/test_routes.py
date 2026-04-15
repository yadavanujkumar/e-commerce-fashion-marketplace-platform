"""Unit tests for the upgraded Flask API routes.

Tests cover: password hashing, product CRUD with fashion fields, order
management with stock/quantity/status, product filtering/search, pagination,
and order cancellation.
"""

import json
import pytest
import sys
import os

# Ensure the services directory is on the path before the app is imported
_services_dir = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'core', 'services'
)
if _services_dir not in sys.path:
    sys.path.insert(0, os.path.abspath(_services_dir))

# Override the database URI *before* importing the app so SQLAlchemy
# never attempts to connect to PostgreSQL.
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from src.api.routes import app, db


@pytest.fixture()
def client():
    """Create a Flask test client with an in-memory SQLite database."""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['JWT_SECRET_KEY'] = 'test-secret'

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def _register(client, username='testuser', password='securepass123', email=None):
    """Helper: register a user and return the response."""
    payload = {'username': username, 'password': password}
    if email:
        payload['email'] = email
    return client.post(
        '/api/v1/auth/register',
        data=json.dumps(payload),
        content_type='application/json',
    )


def _login(client, username='testuser', password='securepass123'):
    """Helper: login and return the JWT access token."""
    resp = client.post(
        '/api/v1/auth/login',
        data=json.dumps({'username': username, 'password': password}),
        content_type='application/json',
    )
    return resp.get_json()['access_token']


def _auth_header(token):
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


# ---------------------------------------------------------------------------
# Auth / password hashing
# ---------------------------------------------------------------------------

class TestAuth:
    def test_register_success(self, client):
        resp = _register(client)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['message'] == 'User registered successfully'
        assert 'user' in data
        assert data['user']['username'] == 'testuser'

    def test_register_short_password(self, client):
        resp = _register(client, password='abc')
        assert resp.status_code == 422

    def test_login_success(self, client):
        _register(client)
        resp = client.post(
            '/api/v1/auth/login',
            data=json.dumps({'username': 'testuser', 'password': 'securepass123'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert 'access_token' in resp.get_json()

    def test_login_wrong_password(self, client):
        _register(client)
        resp = client.post(
            '/api/v1/auth/login',
            data=json.dumps({'username': 'testuser', 'password': 'wrongpass'}),
            content_type='application/json',
        )
        assert resp.status_code == 401

    def test_password_is_hashed(self, client):
        """Ensure the raw password is not stored in the database."""
        _register(client)
        from src.api.routes import User as RouteUser
        with app.app_context():
            user = RouteUser.query.filter_by(username='testuser').first()
            assert user.password_hash != 'securepass123'
            assert user.check_password('securepass123')


# ---------------------------------------------------------------------------
# Product CRUD with fashion fields
# ---------------------------------------------------------------------------

FASHION_PRODUCT = {
    'name': 'Silk Blouse',
    'description': 'A luxurious silk blouse for all occasions.',
    'price': 89.99,
    'category': 'tops',
    'brand': 'Elegance',
    'size': 'M',
    'color': 'ivory',
    'stock_quantity': 50,
}


class TestProductCRUD:
    def test_create_product_with_fashion_fields(self, client):
        _register(client)
        token = _login(client)
        resp = client.post(
            '/api/v1/products',
            data=json.dumps(FASHION_PRODUCT),
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        product = resp.get_json()['product']
        assert product['name'] == 'Silk Blouse'
        assert product['category'] == 'tops'
        assert product['brand'] == 'Elegance'
        assert product['size'] == 'M'
        assert product['color'] == 'ivory'
        assert product['stock_quantity'] == 50

    def test_get_product_by_id(self, client):
        _register(client)
        token = _login(client)
        # Create
        resp = client.post(
            '/api/v1/products',
            data=json.dumps(FASHION_PRODUCT),
            headers=_auth_header(token),
        )
        pid = resp.get_json()['product']['id']
        # Fetch
        resp = client.get(f'/api/v1/products/{pid}')
        assert resp.status_code == 200
        assert resp.get_json()['name'] == 'Silk Blouse'

    def test_get_product_not_found(self, client):
        resp = client.get('/api/v1/products/999')
        assert resp.status_code == 404

    def test_update_product(self, client):
        _register(client)
        token = _login(client)
        resp = client.post(
            '/api/v1/products',
            data=json.dumps(FASHION_PRODUCT),
            headers=_auth_header(token),
        )
        pid = resp.get_json()['product']['id']
        # Update
        resp = client.put(
            f'/api/v1/products/{pid}',
            data=json.dumps({'price': 79.99, 'color': 'pearl'}),
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        updated = resp.get_json()['product']
        assert updated['price'] == 79.99
        assert updated['color'] == 'pearl'
        # Other fields unchanged
        assert updated['name'] == 'Silk Blouse'

    def test_delete_product(self, client):
        _register(client)
        token = _login(client)
        resp = client.post(
            '/api/v1/products',
            data=json.dumps(FASHION_PRODUCT),
            headers=_auth_header(token),
        )
        pid = resp.get_json()['product']['id']
        resp = client.delete(f'/api/v1/products/{pid}', headers=_auth_header(token))
        assert resp.status_code == 200
        # Confirm deletion
        resp = client.get(f'/api/v1/products/{pid}')
        assert resp.status_code == 404

    def test_create_product_requires_auth(self, client):
        resp = client.post(
            '/api/v1/products',
            data=json.dumps(FASHION_PRODUCT),
            content_type='application/json',
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Product filtering / search / pagination
# ---------------------------------------------------------------------------

class TestProductFiltering:
    def _seed_products(self, client):
        _register(client)
        token = _login(client)
        products = [
            {**FASHION_PRODUCT, 'name': 'Red Dress', 'category': 'dresses',
             'color': 'red', 'price': 120.0, 'brand': 'Glamour'},
            {**FASHION_PRODUCT, 'name': 'Blue Jeans', 'category': 'bottoms',
             'color': 'blue', 'price': 59.99, 'brand': 'DenimCo'},
            {**FASHION_PRODUCT, 'name': 'White Sneakers', 'category': 'footwear',
             'color': 'white', 'price': 99.00, 'brand': 'SportStep'},
            {**FASHION_PRODUCT, 'name': 'Silk Blouse', 'category': 'tops',
             'color': 'ivory', 'price': 89.99, 'brand': 'Elegance'},
        ]
        for p in products:
            client.post(
                '/api/v1/products',
                data=json.dumps(p),
                headers=_auth_header(token),
            )
        return token

    def test_list_products_paginated(self, client):
        self._seed_products(client)
        resp = client.get('/api/v1/products?per_page=2&page=1')
        data = resp.get_json()
        assert resp.status_code == 200
        assert len(data['products']) == 2
        assert data['meta']['total'] == 4
        assert data['meta']['pages'] == 2

    def test_filter_by_category(self, client):
        self._seed_products(client)
        resp = client.get('/api/v1/products?category=dresses')
        data = resp.get_json()
        assert all(p['category'] == 'dresses' for p in data['products'])

    def test_filter_by_price_range(self, client):
        self._seed_products(client)
        resp = client.get('/api/v1/products?min_price=80&max_price=100')
        data = resp.get_json()
        for p in data['products']:
            assert 80 <= p['price'] <= 100

    def test_search_by_name(self, client):
        self._seed_products(client)
        resp = client.get('/api/v1/products?q=silk')
        data = resp.get_json()
        assert len(data['products']) >= 1
        assert any('Silk' in p['name'] for p in data['products'])

    def test_filter_by_brand(self, client):
        self._seed_products(client)
        resp = client.get('/api/v1/products?brand=DenimCo')
        data = resp.get_json()
        assert len(data['products']) == 1
        assert data['products'][0]['brand'] == 'DenimCo'


# ---------------------------------------------------------------------------
# Order management (quantity, stock, cancellation)
# ---------------------------------------------------------------------------

class TestOrderManagement:
    def _setup_order(self, client):
        """Register, login, create a product and return (token, product_id)."""
        _register(client)
        token = _login(client)
        resp = client.post(
            '/api/v1/products',
            data=json.dumps(FASHION_PRODUCT),
            headers=_auth_header(token),
        )
        pid = resp.get_json()['product']['id']
        return token, pid

    def test_create_order_with_quantity(self, client):
        token, pid = self._setup_order(client)
        resp = client.post(
            '/api/v1/orders',
            data=json.dumps({'product_id': pid, 'quantity': 2}),
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        order = resp.get_json()['order']
        assert order['quantity'] == 2
        assert order['total_price'] == round(FASHION_PRODUCT['price'] * 2, 2)
        assert order['status'] == 'pending'

    def test_create_order_insufficient_stock(self, client):
        token, pid = self._setup_order(client)
        resp = client.post(
            '/api/v1/orders',
            data=json.dumps({'product_id': pid, 'quantity': 999}),
            headers=_auth_header(token),
        )
        assert resp.status_code == 400
        assert 'Insufficient stock' in resp.get_json()['error']

    def test_create_order_reduces_stock(self, client):
        token, pid = self._setup_order(client)
        client.post(
            '/api/v1/orders',
            data=json.dumps({'product_id': pid, 'quantity': 3}),
            headers=_auth_header(token),
        )
        resp = client.get(f'/api/v1/products/{pid}')
        assert resp.get_json()['stock_quantity'] == FASHION_PRODUCT['stock_quantity'] - 3

    def test_list_orders(self, client):
        token, pid = self._setup_order(client)
        client.post(
            '/api/v1/orders',
            data=json.dumps({'product_id': pid, 'quantity': 1}),
            headers=_auth_header(token),
        )
        resp = client.get('/api/v1/orders', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['orders']) == 1
        assert 'meta' in data

    def test_get_order_by_id(self, client):
        token, pid = self._setup_order(client)
        resp = client.post(
            '/api/v1/orders',
            data=json.dumps({'product_id': pid, 'quantity': 1}),
            headers=_auth_header(token),
        )
        oid = resp.get_json()['order']['id']
        resp = client.get(f'/api/v1/orders/{oid}', headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()['id'] == oid

    def test_cancel_order(self, client):
        token, pid = self._setup_order(client)
        resp = client.post(
            '/api/v1/orders',
            data=json.dumps({'product_id': pid, 'quantity': 5}),
            headers=_auth_header(token),
        )
        oid = resp.get_json()['order']['id']
        # Cancel
        resp = client.post(f'/api/v1/orders/{oid}/cancel', headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()['order']['status'] == 'cancelled'
        # Stock restored
        resp = client.get(f'/api/v1/products/{pid}')
        assert resp.get_json()['stock_quantity'] == FASHION_PRODUCT['stock_quantity']

    def test_cancel_non_pending_order_fails(self, client):
        token, pid = self._setup_order(client)
        resp = client.post(
            '/api/v1/orders',
            data=json.dumps({'product_id': pid, 'quantity': 1}),
            headers=_auth_header(token),
        )
        oid = resp.get_json()['order']['id']
        # Cancel once (should succeed)
        client.post(f'/api/v1/orders/{oid}/cancel', headers=_auth_header(token))
        # Cancel again (already cancelled, should fail)
        resp = client.post(f'/api/v1/orders/{oid}/cancel', headers=_auth_header(token))
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_check(self, client):
        resp = client.get('/health')
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'healthy'
