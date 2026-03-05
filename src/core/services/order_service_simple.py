"""Standalone in-memory order service.

Implements the OrderService, Order, User, Product, InsufficientStockError,
and InvalidOrderError used by the unit-test suite.
"""

from __future__ import annotations

from typing import List, Optional


class InsufficientStockError(Exception):
    """Raised when a product has insufficient stock for the requested quantity."""


class InvalidOrderError(Exception):
    """Raised when order parameters are invalid."""


class User:
    """Minimal user data object."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id

    def __repr__(self) -> str:  # pragma: no cover
        return f"User(user_id={self.user_id!r})"


class Product:
    """Minimal product data object with stock tracking."""

    def __init__(self, product_id: str, stock: int) -> None:
        self.product_id = product_id
        self.stock = stock

    def __repr__(self) -> str:  # pragma: no cover
        return f"Product(product_id={self.product_id!r}, stock={self.stock})"


class Order:
    """Represents a placed order."""

    def __init__(self, user_id: str, product_id: str, quantity: int) -> None:
        self.user_id = user_id
        self.product_id = product_id
        self.quantity = quantity

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Order(user_id={self.user_id!r}, product_id={self.product_id!r}, "
            f"quantity={self.quantity})"
        )


class ProductService:
    """Stub product service (used for integration tests with mocking)."""

    def get_product(self, product_id: str) -> Optional[Product]:  # pragma: no cover
        return None


class OrderService:
    """In-memory order management service.

    Business rules:
    - Orders must have a positive quantity.
    - A single order cannot exceed MAX_ORDER_QUANTITY units.
    - The product must have sufficient stock for quantities ≤ MAX_ORDER_QUANTITY.
    """

    MAX_ORDER_QUANTITY: int = 10

    def __init__(self) -> None:
        self._orders: List[Order] = []

    def create_order(self, user: User, product: Product, quantity: int) -> Order:
        """Create and record a new order.

        Args:
            user: The ordering user.
            product: The product being ordered.
            quantity: Number of units to order.

        Returns:
            The created Order.

        Raises:
            InvalidOrderError: If *quantity* is not a positive integer, or
                exceeds MAX_ORDER_QUANTITY.
            InsufficientStockError: If *product* stock is less than *quantity*
                (for quantities within the allowed maximum).
        """
        if quantity <= 0:
            raise InvalidOrderError("Order quantity must be greater than zero.")
        if quantity > self.MAX_ORDER_QUANTITY:
            raise InvalidOrderError("Order quantity exceeds available stock.")
        if quantity > product.stock:
            raise InsufficientStockError(
                f"Insufficient stock for product {product.product_id!r}."
            )
        order = Order(user_id=user.user_id, product_id=product.product_id, quantity=quantity)
        self._orders.append(order)
        return order
