import pytest
import requests
from typing import Dict, Any

# Constants for the API endpoints and test data
BASE_URL = "http://localhost:8000/api/v1"
PRODUCT_ENDPOINT = f"{BASE_URL}/products"
ORDER_ENDPOINT = f"{BASE_URL}/orders"
USER_ENDPOINT = f"{BASE_URL}/users"

# Sample test data
TEST_USER = {
    "username": "testuser",
    "email": "testuser@example.com",
    "password": "securepassword123"
}

TEST_PRODUCT = {
    "name": "Stylish T-Shirt",
    "description": "A stylish t-shirt for everyday wear.",
    "price": 19.99,
    "stock": 100
}

TEST_ORDER = {
    "user_id": 1,
    "product_id": 1,
    "quantity": 2
}

@pytest.fixture(scope="module")
def setup_api():
    """Fixture to setup and teardown the API for integration tests."""
    # Setup: Create a test user
    response = requests.post(USER_ENDPOINT, json=TEST_USER)
    assert response.status_code == 201, "Failed to create test user"
    yield response.json()  # Provide the created user data for tests
    # Teardown: Delete the test user
    user_id = response.json().get("id")
    requests.delete(f"{USER_ENDPOINT}/{user_id}")

@pytest.fixture(scope="module")
def setup_product():
    """Fixture to setup and teardown a product for integration tests."""
    response = requests.post(PRODUCT_ENDPOINT, json=TEST_PRODUCT)
    assert response.status_code == 201, "Failed to create test product"
    yield response.json()  # Provide the created product data for tests
    # Teardown: Delete the test product
    product_id = response.json().get("id")
    requests.delete(f"{PRODUCT_ENDPOINT}/{product_id}")

@pytest.mark.parametrize("quantity, expected_status", [
    (1, 201),  # Happy path
    (0, 400),  # Edge case: Zero quantity
    (5, 201),  # Happy path: Valid quantity
])
def test_create_order(setup_api, setup_product, quantity, expected_status):
    """Test creating an order with various quantities."""
    order_data = TEST_ORDER.copy()
    order_data["quantity"] = quantity
    response = requests.post(ORDER_ENDPOINT, json=order_data)
    assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"

def test_get_product(setup_product):
    """Test retrieving a product by ID."""
    product_id = setup_product.get("id")
    response = requests.get(f"{PRODUCT_ENDPOINT}/{product_id}")
    assert response.status_code == 200, "Failed to retrieve product"
    assert response.json().get("name") == TEST_PRODUCT["name"], "Product name does not match"

def test_update_product(setup_product):
    """Test updating a product's details."""
    product_id = setup_product.get("id")
    updated_data = {"price": 24.99}
    response = requests.put(f"{PRODUCT_ENDPOINT}/{product_id}", json=updated_data)
    assert response.status_code == 200, "Failed to update product"
    assert response.json().get("price") == updated_data["price"], "Product price was not updated correctly"

def test_delete_product(setup_product):
    """Test deleting a product."""
    product_id = setup_product.get("id")
    response = requests.delete(f"{PRODUCT_ENDPOINT}/{product_id}")
    assert response.status_code == 204, "Failed to delete product"
    # Verify that the product no longer exists
    response = requests.get(f"{PRODUCT_ENDPOINT}/{product_id}")
    assert response.status_code == 404, "Product was not deleted successfully"

def test_create_order_invalid_user(setup_product):
    """Test creating an order with an invalid user ID."""
    invalid_order_data = TEST_ORDER.copy()
    invalid_order_data["user_id"] = 99999  # Non-existent user
    response = requests.post(ORDER_ENDPOINT, json=invalid_order_data)
    assert response.status_code == 404, "Expected 404 for invalid user ID"

def test_create_order_invalid_product(setup_api):
    """Test creating an order with an invalid product ID."""
    invalid_order_data = TEST_ORDER.copy()
    invalid_order_data["product_id"] = 99999  # Non-existent product
    response = requests.post(ORDER_ENDPOINT, json=invalid_order_data)
    assert response.status_code == 404, "Expected 404 for invalid product ID"

def test_performance_create_order(setup_api, setup_product):
    """Performance test for creating multiple orders."""
    import time
    start_time = time.time()
    for _ in range(100):  # Simulate load
        response = requests.post(ORDER_ENDPOINT, json=TEST_ORDER)
        assert response.status_code == 201, "Failed to create order during performance test"
    duration = time.time() - start_time
    assert duration < 5, "Performance test exceeded time limit"

def test_error_handling_invalid_json(setup_api):
    """Test error handling for invalid JSON input."""
    response = requests.post(ORDER_ENDPOINT, json="invalid_json")
    assert response.status_code == 400, "Expected 400 for invalid JSON input"