# src/core/services/product_service.py

import logging
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.core.models import Product, User
from src.core.schemas import ProductCreate, ProductUpdate, ProductResponse
from src.core.exceptions import ProductNotFoundException, ProductAlreadyExistsException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductService:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_product(self, product_data: ProductCreate, user: User) -> ProductResponse:
        """Create a new product listing."""
        logger.info(f"Creating product for user {user.id}: {product_data.name}")
        
        # Check if product already exists
        existing_product = self.db_session.query(Product).filter_by(name=product_data.name, seller_id=user.id).first()
        if existing_product:
            logger.error(f"Product '{product_data.name}' already exists for user {user.id}.")
            raise ProductAlreadyExistsException(f"Product '{product_data.name}' already exists.")

        new_product = Product(**product_data.dict(), seller_id=user.id)
        self.db_session.add(new_product)
        try:
            self.db_session.commit()
            logger.info(f"Product '{new_product.name}' created successfully.")
            return ProductResponse.from_orm(new_product)
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.exception("Failed to create product.")
            raise

    def update_product(self, product_id: int, product_data: ProductUpdate, user: User) -> ProductResponse:
        """Update an existing product listing."""
        logger.info(f"Updating product {product_id} for user {user.id}.")
        
        product = self.db_session.query(Product).filter_by(id=product_id, seller_id=user.id).first()
        if not product:
            logger.error(f"Product with id {product_id} not found for user {user.id}.")
            raise ProductNotFoundException(f"Product with id {product_id} not found.")

        for key, value in product_data.dict(exclude_unset=True).items():
            setattr(product, key, value)

        try:
            self.db_session.commit()
            logger.info(f"Product '{product.name}' updated successfully.")
            return ProductResponse.from_orm(product)
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.exception("Failed to update product.")
            raise

    def delete_product(self, product_id: int, user: User) -> None:
        """Delete a product listing."""
        logger.info(f"Deleting product {product_id} for user {user.id}.")
        
        product = self.db_session.query(Product).filter_by(id=product_id, seller_id=user.id).first()
        if not product:
            logger.error(f"Product with id {product_id} not found for user {user.id}.")
            raise ProductNotFoundException(f"Product with id {product_id} not found.")

        self.db_session.delete(product)
        try:
            self.db_session.commit()
            logger.info(f"Product '{product.name}' deleted successfully.")
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.exception("Failed to delete product.")
            raise

    def get_product(self, product_id: int) -> Optional[ProductResponse]:
        """Retrieve a product by its ID."""
        logger.info(f"Retrieving product {product_id}.")
        
        product = self.db_session.query(Product).filter_by(id=product_id).first()
        if not product:
            logger.error(f"Product with id {product_id} not found.")
            raise ProductNotFoundException(f"Product with id {product_id} not found.")
        
        return ProductResponse.from_orm(product)

    def search_products(self, query: str, filters: Optional[Dict[str, str]] = None) -> List[ProductResponse]:
        """Search for products based on a query and optional filters."""
        logger.info(f"Searching for products with query: {query} and filters: {filters}.")
        
        search_query = self.db_session.query(Product).filter(Product.name.ilike(f"%{query}%"))
        
        if filters:
            for key, value in filters.items():
                search_query = search_query.filter(getattr(Product, key) == value)

        products = search_query.all()
        logger.info(f"Found {len(products)} products matching the query.")
        return [ProductResponse.from_orm(product) for product in products]

# Exception classes
class ProductNotFoundException(Exception):
    pass

class ProductAlreadyExistsException(Exception):
    pass