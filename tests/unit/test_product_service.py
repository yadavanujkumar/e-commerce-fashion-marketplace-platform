import pytest
from unittest.mock import patch, MagicMock
from product_service import ProductService, Product, ProductNotFoundError, InvalidProductError

# Constants for test data
VALID_PRODUCT_DATA = {
    "id": 1,
    "name": "Stylish T-Shirt",
    "price": 29.99,
    "stock": 100,
    "category": "Apparel"
}

INVALID_PRODUCT_DATA = {
    "id": 2,
    "name": "",
    "price": -10.00,
    "stock": -5,
    "category": "Apparel"
}

@pytest.fixture
def product_service():
    """Fixture for ProductService instance."""
    return ProductService()

@pytest.fixture
def valid_product():
    """Fixture for a valid product instance."""
    return Product(**VALID_PRODUCT_DATA)

@pytest.fixture
def invalid_product():
    """Fixture for an invalid product instance."""
    return Product(**INVALID_PRODUCT_DATA)

def test_add_product_happy_path(product_service, valid_product):
    """Test adding a valid product."""
    product_service.add_product(valid_product)
    assert valid_product.id in product_service.products
    assert product_service.products[valid_product.id] == valid_product

def test_add_product_invalid_name(product_service, invalid_product):
    """Test adding a product with an invalid name."""
    with pytest.raises(InvalidProductError, match="Product name cannot be empty."):
        product_service.add_product(invalid_product)

def test_add_product_invalid_price(product_service, invalid_product):
    """Test adding a product with an invalid price."""
    invalid_product.price = -10.00
    with pytest.raises(InvalidProductError, match="Product price must be a positive number."):
        product_service.add_product(invalid_product)

def test_get_product_happy_path(product_service, valid_product):
    """Test retrieving a product that exists."""
    product_service.add_product(valid_product)
    retrieved_product = product_service.get_product(valid_product.id)
    assert retrieved_product == valid_product

def test_get_product_not_found(product_service):
    """Test retrieving a product that does not exist."""
    with pytest.raises(ProductNotFoundError, match="Product with ID 999 not found."):
        product_service.get_product(999)

def test_update_product_happy_path(product_service, valid_product):
    """Test updating an existing product."""
    product_service.add_product(valid_product)
    updated_data = {"name": "Updated T-Shirt", "price": 34.99}
    product_service.update_product(valid_product.id, **updated_data)
    updated_product = product_service.get_product(valid_product.id)
    assert updated_product.name == "Updated T-Shirt"
    assert updated_product.price == 34.99

def test_update_product_not_found(product_service):
    """Test updating a product that does not exist."""
    with pytest.raises(ProductNotFoundError, match="Product with ID 999 not found."):
        product_service.update_product(999, name="New Name")

def test_delete_product_happy_path(product_service, valid_product):
    """Test deleting an existing product."""
    product_service.add_product(valid_product)
    product_service.delete_product(valid_product.id)
    assert valid_product.id not in product_service.products

def test_delete_product_not_found(product_service):
    """Test deleting a product that does not exist."""
    with pytest.raises(ProductNotFoundError, match="Product with ID 999 not found."):
        product_service.delete_product(999)

@pytest.mark.parametrize("price,expected", [
    (0, False),
    (10, True),
    (100, True),
    (29.99, True),
    (-1, False),
    (None, False),
])
def test_is_price_valid(product_service, price, expected):
    """Test price validation logic."""
    assert product_service.is_price_valid(price) == expected

@pytest.mark.parametrize("stock,expected", [
    (0, True),
    (10, True),
    (100, True),
    (-1, False),
    (None, False),
])
def test_is_stock_valid(product_service, stock, expected):
    """Test stock validation logic."""
    assert product_service.is_stock_valid(stock) == expected

def test_performance_add_product(product_service, valid_product):
    """Performance test for adding multiple products."""
    import time
    start_time = time.time()
    for i in range(1000):
        product_service.add_product(Product(id=i, name=f"Product {i}", price=10.00, stock=100, category="Apparel"))
    duration = time.time() - start_time
    assert duration < 1  # Ensure it takes less than 1 second

def test_integration_with_database(product_service):
    """Integration test with a mocked database."""
    with patch('product_service.Database') as MockDatabase:
        mock_db = MockDatabase.return_value
        mock_db.save_product.return_value = True
        product_service.database = mock_db
        
        product_service.add_product(valid_product)
        mock_db.save_product.assert_called_once_with(valid_product)

        mock_db.get_product.return_value = valid_product
        retrieved_product = product_service.get_product(valid_product.id)
        assert retrieved_product == valid_product

        mock_db.delete_product.return_value = True
        product_service.delete_product(valid_product.id)
        mock_db.delete_product.assert_called_once_with(valid_product.id)