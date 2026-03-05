"""Standalone in-memory product service.

Implements the ProductService, Product, ProductNotFoundError, and
InvalidProductError used by the unit-test suite.
"""

from __future__ import annotations

from typing import Dict, Optional


class ProductNotFoundError(Exception):
    """Raised when a product cannot be found."""


class InvalidProductError(Exception):
    """Raised when product data fails validation."""


class Database:
    """Stub database back-end (used for integration tests with mocking)."""

    def save_product(self, product: "Product") -> bool:  # pragma: no cover
        return True

    def get_product(self, product_id: int) -> Optional["Product"]:  # pragma: no cover
        return None

    def delete_product(self, product_id: int) -> bool:  # pragma: no cover
        return True


class Product:
    """Simple product data object."""

    def __init__(
        self,
        id: int,
        name: str,
        price: float,
        stock: int,
        category: str,
    ) -> None:
        self.id = id
        self.name = name
        self.price = price
        self.stock = stock
        self.category = category

    def __repr__(self) -> str:  # pragma: no cover
        return f"Product(id={self.id}, name={self.name!r}, price={self.price})"


class ProductService:
    """In-memory product management service."""

    def __init__(self) -> None:
        self.products: Dict[int, Product] = {}

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def is_price_valid(self, price: Optional[float]) -> bool:
        """Return True if *price* is a positive number."""
        if price is None:
            return False
        try:
            return float(price) > 0
        except (TypeError, ValueError):
            return False

    def is_stock_valid(self, stock: Optional[int]) -> bool:
        """Return True if *stock* is a non-negative integer."""
        if stock is None:
            return False
        try:
            return int(stock) >= 0
        except (TypeError, ValueError):
            return False

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_product(self, product: Product) -> None:
        """Validate and add a product to the catalogue."""
        errors: list = []
        if not product.name or not product.name.strip():
            errors.append("Product name cannot be empty.")
        if not self.is_price_valid(product.price):
            errors.append("Product price must be a positive number.")
        if not self.is_stock_valid(product.stock):
            errors.append("Product stock must be a non-negative integer.")
        if errors:
            raise InvalidProductError(" ".join(errors))
        self.products[product.id] = product

    def get_product(self, product_id: int) -> Product:
        """Retrieve a product by ID."""
        product = self.products.get(product_id)
        if product is None:
            raise ProductNotFoundError(f"Product with ID {product_id} not found.")
        return product

    def update_product(self, product_id: int, **kwargs) -> Product:
        """Update fields on an existing product."""
        product = self.get_product(product_id)
        for key, value in kwargs.items():
            setattr(product, key, value)
        return product

    def delete_product(self, product_id: int) -> None:
        """Delete a product by ID."""
        if product_id not in self.products:
            raise ProductNotFoundError(f"Product with ID {product_id} not found.")
        del self.products[product_id]
