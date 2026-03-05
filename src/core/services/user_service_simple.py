"""Standalone in-memory user service.

Implements the UserService, User, UserCreationError, and UserNotFoundError
used by the unit-test suite.
"""

from __future__ import annotations

import re
from typing import Dict, Optional


class UserCreationError(Exception):
    """Raised when user creation fails due to invalid data."""


class UserNotFoundError(Exception):
    """Raised when a requested user cannot be found."""


class User:
    """Simple user data object."""

    def __init__(self, username: str, email: str, password: str) -> None:
        self.username = username
        self.email = email
        self.password = password

    def __repr__(self) -> str:  # pragma: no cover
        return f"User(username={self.username!r}, email={self.email!r})"


class UserService:
    """In-memory user management service."""

    _EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self) -> None:
        self._users: Dict[str, User] = {}

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self, user: User) -> None:
        if not user.username or not user.username.strip():
            raise UserCreationError("Invalid user data: username must not be empty.")
        if not self._EMAIL_RE.match(user.email):
            raise UserCreationError("Invalid user data: email is not valid.")
        if not user.password or len(user.password) < 8:
            raise UserCreationError(
                "Invalid user data: password must be at least 8 characters."
            )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_user(self, user: User) -> User:
        """Create and store a new user after validating the data."""
        self._validate(user)
        if user.username in self._users:
            raise UserCreationError(
                f"Invalid user data: username {user.username!r} already exists."
            )
        self._users[user.username] = user
        return user

    def get_user(self, username: str) -> User:
        """Retrieve a user by username."""
        user = self._users.get(username)
        if user is None:
            raise UserNotFoundError(f"User not found: {username!r}")
        return user

    def update_user(self, username: str, updates: dict) -> User:
        """Update fields on an existing user."""
        user = self.get_user(username)
        for key, value in updates.items():
            setattr(user, key, value)
        return user

    def delete_user(self, username: str) -> None:
        """Delete a user by username."""
        if username not in self._users:
            raise UserNotFoundError(f"User not found: {username!r}")
        del self._users[username]
