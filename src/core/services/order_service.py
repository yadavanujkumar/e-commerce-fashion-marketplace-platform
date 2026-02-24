# src/core/services/order_service.py

import logging
from typing import List, Dict, Any
from uuid import UUID, uuid4
from decimal import Decimal
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class OrderItem:
    product_id: UUID
    quantity: int
    price: Decimal

@dataclass
class Order:
    id: UUID = field(default_factory=uuid4)
    user_id: UUID
    items: List[OrderItem]
    total_amount: Decimal
    status: OrderStatus = OrderStatus.PENDING

class OrderService:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_order(self, user_id: UUID, items: List[Dict[str, Any]]) -> Order:
        logger.info(f"Creating order for user {user_id} with items: {items}")
        order_items = []
        total_amount = Decimal('0.00')

        for item in items:
            product_id = UUID(item['product_id'])
            quantity = item['quantity']
            price = Decimal(item['price'])
            order_items.append(OrderItem(product_id, quantity, price))
            total_amount += price * quantity

        order = Order(user_id=user_id, items=order_items, total_amount=total_amount)
        self._save_order(order)
        logger.info(f"Order created with ID: {order.id}")
        return order

    def _save_order(self, order: Order):
        logger.debug(f"Saving order: {order}")
        try:
            self.db_session.add(order)
            self.db_session.commit()
        except IntegrityError as e:
            logger.error(f"Failed to save order: {e}")
            self.db_session.rollback()
            raise

    def get_order(self, order_id: UUID) -> Order:
        logger.info(f"Retrieving order with ID: {order_id}")
        order = self.db_session.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.warning(f"Order with ID {order_id} not found.")
            raise ValueError(f"Order with ID {order_id} not found.")
        return order

    def update_order_status(self, order_id: UUID, status: OrderStatus) -> Order:
        logger.info(f"Updating order {order_id} status to {status}")
        order = self.get_order(order_id)
        order.status = status
        self.db_session.commit()
        logger.info(f"Order {order_id} status updated to {status}")
        return order

    def list_orders(self, user_id: UUID) -> List[Order]:
        logger.info(f"Listing orders for user {user_id}")
        orders = self.db_session.query(Order).filter(Order.user_id == user_id).all()
        logger.info(f"Found {len(orders)} orders for user {user_id}")
        return orders

# Example usage:
# db_session = ... # Obtain a SQLAlchemy session
# order_service = OrderService(db_session)
# order = order_service.create_order(user_id=some_user_id, items=[{'product_id': '...', 'quantity': 2, 'price': '19.99'}])