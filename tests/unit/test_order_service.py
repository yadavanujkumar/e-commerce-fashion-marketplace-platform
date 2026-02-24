import pytest
from unittest.mock import patch, MagicMock
from order_service import OrderService, Order, Product, User, InsufficientStockError, InvalidOrderError

# Constants for test data
VALID_USER_ID = "user_123"
VALID_PRODUCT_ID = "product_456"
VALID_ORDER_QUANTITY = 2
INVALID_ORDER_QUANTITY = 0
EXCESSIVE_ORDER_QUANTITY = 1000
VALID_PRODUCT_STOCK = 10

@pytest.fixture
def user():
    """Fixture for creating a user."""
    return User(user_id=VALID_USER_ID)

@pytest.fixture
def product():
    """Fixture for creating a product with stock."""
    return Product(product_id=VALID_PRODUCT_ID, stock=VALID_PRODUCT_STOCK)

@pytest.fixture
def order_service():
    """Fixture for creating an instance of OrderService."""
    return OrderService()

@pytest.fixture
def mock_product_service():
    """Fixture for mocking the product service."""
    with patch('order_service.ProductService') as mock_service:
        yield mock_service

def test_create_order_happy_path(order_service, user, product):
    """Test creating an order successfully."""
    order = order_service.create_order(user, product, VALID_ORDER_QUANTITY)
    
    assert isinstance(order, Order), "Expected an instance of Order"
    assert order.user_id == VALID_USER_ID, "User ID does not match"
    assert order.product_id == VALID_PRODUCT_ID, "Product ID does not match"
    assert order.quantity == VALID_ORDER_QUANTITY, "Order quantity does not match"

def test_create_order_insufficient_stock(order_service, user, product):
    """Test creating an order with insufficient stock."""
    product.stock = 1  # Set stock to 1 for this test
    with pytest.raises(InsufficientStockError, match="Insufficient stock for product"):
        order_service.create_order(user, product, VALID_ORDER_QUANTITY)

def test_create_order_invalid_quantity(order_service, user, product):
    """Test creating an order with an invalid quantity."""
    with pytest.raises(InvalidOrderError, match="Order quantity must be greater than zero"):
        order_service.create_order(user, product, INVALID_ORDER_QUANTITY)

def test_create_order_excessive_quantity(order_service, user, product):
    """Test creating an order with an excessive quantity."""
    with pytest.raises(InvalidOrderError, match="Order quantity exceeds available stock"):
        order_service.create_order(user, product, EXCESSIVE_ORDER_QUANTITY)

@pytest.mark.parametrize("quantity,expected_exception", [
    (0, InvalidOrderError),
    (-1, InvalidOrderError),
    (VALID_PRODUCT_STOCK + 1, InvalidOrderError),
])
def test_create_order_invalid_quantities(order_service, user, product, quantity, expected_exception):
    """Test creating an order with various invalid quantities."""
    with pytest.raises(expected_exception):
        order_service.create_order(user, product, quantity)

def test_order_service_performance(order_service, user, product):
    """Performance test for creating multiple orders."""
    import time

    start_time = time.time()
    for _ in range(1000):
        order_service.create_order(user, product, 1)
    duration = time.time() - start_time

    assert duration < 2, "Creating 1000 orders took too long"

def test_order_service_integration(mock_product_service, order_service, user):
    """Integration test for order service with mocked product service."""
    mock_product_service.get_product.return_value = MagicMock(stock=10)
    
    order = order_service.create_order(user, mock_product_service.get_product(VALID_PRODUCT_ID), 1)
    
    assert order.user_id == user.user_id, "User ID does not match in integration test"
    assert order.product_id == VALID_PRODUCT_ID, "Product ID does not match in integration test"

@pytest.fixture(autouse=True)
def cleanup():
    """Fixture for cleanup after tests."""
    yield
    # Perform any necessary cleanup here, if needed
    pass