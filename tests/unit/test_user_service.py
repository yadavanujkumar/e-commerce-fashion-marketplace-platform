import pytest
from unittest.mock import patch, MagicMock
from user_service import UserService, User, UserCreationError, UserNotFoundError

# Constants for test data
VALID_USER_DATA = {
    "username": "testuser",
    "email": "testuser@example.com",
    "password": "SecurePassword123"
}

INVALID_USER_DATA = {
    "username": "",
    "email": "invalid-email",
    "password": "short"
}

@pytest.fixture
def user_service():
    """Fixture for UserService instance."""
    return UserService()

@pytest.fixture
def valid_user():
    """Fixture for a valid User instance."""
    return User(**VALID_USER_DATA)

@pytest.fixture
def invalid_user():
    """Fixture for an invalid User instance."""
    return User(**INVALID_USER_DATA)

def test_create_user_happy_path(user_service, valid_user):
    """Test creating a user with valid data."""
    user = user_service.create_user(valid_user)
    assert user.username == VALID_USER_DATA["username"], "Username does not match"
    assert user.email == VALID_USER_DATA["email"], "Email does not match"

def test_create_user_invalid_data(user_service, invalid_user):
    """Test creating a user with invalid data raises an error."""
    with pytest.raises(UserCreationError, match="Invalid user data"):
        user_service.create_user(invalid_user)

@pytest.mark.parametrize("username, email, password", [
    ("", "test@example.com", "ValidPass123"),
    ("testuser", "invalid-email", "ValidPass123"),
    ("testuser", "test@example.com", ""),
])
def test_create_user_edge_cases(user_service, username, email, password):
    """Test creating a user with edge case data."""
    user_data = {
        "username": username,
        "email": email,
        "password": password
    }
    with pytest.raises(UserCreationError, match="Invalid user data"):
        user_service.create_user(User(**user_data))

def test_get_user_happy_path(user_service, valid_user):
    """Test retrieving a user by username."""
    user_service.create_user(valid_user)
    retrieved_user = user_service.get_user(valid_user.username)
    assert retrieved_user.username == valid_user.username, "Retrieved username does not match"
    assert retrieved_user.email == valid_user.email, "Retrieved email does not match"

def test_get_user_not_found(user_service):
    """Test retrieving a user that does not exist raises an error."""
    with pytest.raises(UserNotFoundError, match="User not found"):
        user_service.get_user("nonexistentuser")

def test_update_user_happy_path(user_service, valid_user):
    """Test updating a user's information."""
    user_service.create_user(valid_user)
    updated_data = {"email": "newemail@example.com"}
    updated_user = user_service.update_user(valid_user.username, updated_data)
    assert updated_user.email == updated_data["email"], "Email was not updated correctly"

def test_update_user_not_found(user_service):
    """Test updating a user that does not exist raises an error."""
    with pytest.raises(UserNotFoundError, match="User not found"):
        user_service.update_user("nonexistentuser", {"email": "newemail@example.com"})

def test_delete_user_happy_path(user_service, valid_user):
    """Test deleting a user."""
    user_service.create_user(valid_user)
    user_service.delete_user(valid_user.username)
    with pytest.raises(UserNotFoundError, match="User not found"):
        user_service.get_user(valid_user.username)

def test_delete_user_not_found(user_service):
    """Test deleting a user that does not exist raises an error."""
    with pytest.raises(UserNotFoundError, match="User not found"):
        user_service.delete_user("nonexistentuser")

@pytest.mark.parametrize("username", ["testuser1", "testuser2", "testuser3"])
def test_create_multiple_users(user_service, username):
    """Test creating multiple users in a loop."""
    user_data = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "SecurePassword123"
    }
    user = user_service.create_user(User(**user_data))
    assert user.username == username, f"Failed to create user {username}"

def test_performance_create_user(user_service):
    """Test the performance of creating a user."""
    import time
    start_time = time.time()
    for i in range(1000):
        user_service.create_user(User(username=f"user{i}", email=f"user{i}@example.com", password="SecurePassword123"))
    duration = time.time() - start_time
    assert duration < 2, "Creating 1000 users took too long"

# Note: The UserService and User classes, as well as the UserCreationError and UserNotFoundError exceptions,
# should be implemented in the user_service module for this test suite to function correctly.