import uuid
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod
from app.models.product import Product
from app.models.inventory import InventoryProjection
from app.events.store import event_store_service
from app.events.dispatcher import event_dispatcher
from app.events.types import (
    OrderCreatedEvent, OrderItemAddedEvent,
    OrderCompletedEvent, OrderCancelledEvent, ItemSoldEvent,
)
from app.core.exceptions import (
    InsufficientStockError, ProductNotFoundError,
)

logger = logging.getLogger(__name__)


class OrderService:

    def create_order(
        self, db: Session, branch_id: str, cashier_id: str
    ) -> Order:
        """Open a new cart/order for a cashier."""
        order = Order(
            id=str(uuid.uuid4()),
            branch_id=branch_id,
            cashier_id=cashier_id,
            status=OrderStatus.OPEN,
        )
        db.add(order)

        event = OrderCreatedEvent(order.id, branch_id, cashier_id)
        stored = event_store_service.append(db, event)
        event_dispatcher.dispatch(stored, db)

        db.commit()
        db.refresh(order)
        logger.info(f"Order created: {order.id} branch={branch_id}")
        return order

    def scan_item(
        self,
        db: Session,
        order_id: str,
        barcode: str,
        quantity: int,
        cashier_id: str,
    ) -> dict:
        """
        Cashier scans a barcode. Looks up product, validates stock,
        adds item to order. Does NOT deduct stock yet — that happens at checkout.
        """
        order = self._get_open_order(db, order_id)

        # Look up product by barcode
        product = db.scalar(
            select(Product).where(Product.barcode == barcode)
        )
        if not product:
            raise ProductNotFoundError(
                f"No product found with barcode '{barcode}'. "
                f"Check the barcode or add the product first."
            )

        # Check stock availability
        projection = db.scalar(
            select(InventoryProjection).where(
                InventoryProjection.product_id == product.id,
                InventoryProjection.branch_id == order.branch_id,
            )
        )
        available = projection.available_quantity if projection else 0

        # Also count already-reserved quantity in this order
        already_in_order = sum(
            item.quantity for item in order.items
            if item.product_id == product.id
        )

        if available < (already_in_order + quantity):
            raise InsufficientStockError(
                f"Insufficient stock for '{product.name}'. "
                f"Available: {available}, In cart: {already_in_order}, "
                f"Requested: {quantity}."
            )

        unit_price = product.current_price
        line_total = round(unit_price * quantity, 2)

        # Check if product already in order — update quantity
        existing_item = next(
            (i for i in order.items if i.product_id == product.id), None
        )
        if existing_item:
            existing_item.quantity += quantity
            existing_item.line_total = round(
                existing_item.unit_price * existing_item.quantity, 2
            )
        else:
            item = OrderItem(
                order_id=order_id,
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                barcode=barcode,
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total,
            )
            db.add(item)
            order.items.append(item)

        # Recalculate order totals
        db.flush()
        self._recalculate_totals(order)

        # Fire event
        event = OrderItemAddedEvent(
            order_id, order.branch_id, product.id,
            product.name, barcode, quantity, unit_price, cashier_id
        )
        stored = event_store_service.append(db, event)
        event_dispatcher.dispatch(stored, db)

        db.commit()
        db.refresh(order)

        return {
            "order_id": order_id,
            "product_id": product.id,
            "product_name": product.name,
            "sku": product.sku,
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": line_total,
            "order_subtotal": order.subtotal,
            "order_total": order.total_amount,
            "items_in_cart": len(order.items),
        }

    def checkout(
        self,
        db: Session,
        order_id: str,
        payment_method: str,
        cashier_id: str,
    ) -> dict:
        """
        Finalize the order:
        1. Validate all items still have stock
        2. Deduct inventory for each item (fires ItemSold events)
        3. Mark order as completed
        4. Return receipt
        """
        order = self._get_open_order(db, order_id)

        if not order.items:
            raise ValueError("Cannot checkout an empty order.")

        try:
            payment = PaymentMethod(payment_method)
        except ValueError:
            raise ValueError(
                f"Invalid payment method '{payment_method}'. "
                f"Use: cash, card, mpesa"
            )

        # Deduct stock for each item — fires ItemSold events
        for item in order.items:
            projection = db.execute(
                select(InventoryProjection)
                .where(
                    InventoryProjection.product_id == item.product_id,
                    InventoryProjection.branch_id == order.branch_id,
                )
                .with_for_update()
            ).scalar_one_or_none()

            available = projection.available_quantity if projection else 0
            if available < item.quantity:
                raise InsufficientStockError(
                    f"Stock changed during checkout. "
                    f"'{item.product_name}' only has {available} units left."
                )

            sell_event = ItemSoldEvent(
                product_id=item.product_id,
                branch_id=order.branch_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                order_id=order_id,
                created_by=cashier_id,
            )
            stored = event_store_service.append(db, sell_event)
            event_dispatcher.dispatch(stored, db)

        # Complete the order
        order.status = OrderStatus.COMPLETED
        order.payment_method = payment
        order.completed_at = datetime.utcnow()

        completed_event = OrderCompletedEvent(
            order_id=order_id,
            branch_id=order.branch_id,
            cashier_id=cashier_id,
            subtotal=order.subtotal,
            tax_amount=order.tax_amount,
            total_amount=order.total_amount,
            payment_method=payment_method,
            item_count=len(order.items),
        )
        stored = event_store_service.append(db, completed_event)
        event_dispatcher.dispatch(stored, db)

        db.commit()
        db.refresh(order)

        logger.info(
            f"Order completed: {order_id} total={order.total_amount} "
            f"payment={payment_method}"
        )
        return self._build_receipt(order)

    def cancel_order(
        self, db: Session, order_id: str, reason: str, cancelled_by: str
    ) -> dict:
        order = self._get_open_order(db, order_id)
        order.status = OrderStatus.CANCELLED

        event = OrderCancelledEvent(
            order_id, order.branch_id, reason, cancelled_by
        )
        stored = event_store_service.append(db, event)
        event_dispatcher.dispatch(stored, db)

        db.commit()
        return {"order_id": order_id, "status": "cancelled", "reason": reason}

    def get_order(self, db: Session, order_id: str) -> Order:
        order = db.get(Order, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found.")
        return order

    def _get_open_order(self, db: Session, order_id: str) -> Order:
        order = db.get(Order, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found.")
        if order.status != OrderStatus.OPEN:
            raise ValueError(
                f"Order {order_id} is already {order.status.value}. "
                f"Cannot modify a {order.status.value} order."
            )
        return order

    def _recalculate_totals(self, order: Order):
        subtotal = sum(item.line_total for item in order.items)
        tax = round(subtotal * order.tax_rate, 2)
        order.subtotal = round(subtotal, 2)
        order.tax_amount = tax
        order.total_amount = round(subtotal + tax, 2)

    def _build_receipt(self, order: Order) -> dict:
        return {
            "receipt": {
                "order_id": order.id,
                "branch_id": order.branch_id,
                "cashier_id": order.cashier_id,
                "status": order.status.value,
                "payment_method": order.payment_method.value,
                "items": [
                    {
                        "product_name": item.product_name,
                        "sku": item.product_sku,
                        "barcode": item.barcode,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "line_total": item.line_total,
                    }
                    for item in order.items
                ],
                "subtotal": order.subtotal,
                "tax_rate_percent": order.tax_rate * 100,
                "tax_amount": order.tax_amount,
                "total_amount": order.total_amount,
                "created_at": order.created_at.isoformat(),
                "completed_at": order.completed_at.isoformat()
                if order.completed_at else None,
            }
        }


order_service = OrderService()