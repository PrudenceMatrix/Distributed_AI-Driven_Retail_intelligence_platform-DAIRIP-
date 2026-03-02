from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid


class EventType(str, Enum):
    # Inventory events
    STOCK_RECEIVED = "StockReceived"
    ITEM_SOLD = "ItemSold"
    ITEM_RESERVED = "ItemReserved"
    RESERVATION_RELEASED = "ReservationReleased"
    STOCK_ADJUSTED = "StockAdjusted"

    # Product events
    PRODUCT_CREATED = "ProductCreated"
    PRODUCT_UPDATED = "ProductUpdated"

    # Pricing events
    PRICE_ADJUSTED = "PriceAdjusted"

    # Order events
    ORDER_CREATED = "OrderCreated"
    ORDER_ITEM_ADDED = "OrderItemAdded"
    ORDER_COMPLETED = "OrderCompleted"
    ORDER_CANCELLED = "OrderCancelled"


class AggregateType(str, Enum):
    PRODUCT = "product"
    ORDER = "order"
    INVENTORY = "inventory"


@dataclass
class DomainEvent:
    event_type: EventType
    aggregate_id: str
    aggregate_type: AggregateType
    payload: dict[str, Any]
    branch_id: str | None = None
    created_by: str | None = None
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)


# ── Inventory Events ──────────────────────────────────────────────────────────

@dataclass
class StockReceivedEvent(DomainEvent):
    def __init__(self, product_id, branch_id, quantity,
                 created_by=None, correlation_id=None):
        super().__init__(
            event_type=EventType.STOCK_RECEIVED,
            aggregate_id=product_id,
            aggregate_type=AggregateType.INVENTORY,
            payload={"product_id": product_id, "branch_id": branch_id,
                     "quantity": quantity},
            branch_id=branch_id, created_by=created_by,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )


@dataclass
class ItemSoldEvent(DomainEvent):
    def __init__(self, product_id, branch_id, quantity, unit_price,
                 order_id, created_by=None, correlation_id=None):
        super().__init__(
            event_type=EventType.ITEM_SOLD,
            aggregate_id=product_id,
            aggregate_type=AggregateType.INVENTORY,
            payload={"product_id": product_id, "branch_id": branch_id,
                     "quantity": quantity, "unit_price": unit_price,
                     "order_id": order_id},
            branch_id=branch_id, created_by=created_by,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )


@dataclass
class StockAdjustedEvent(DomainEvent):
    def __init__(self, product_id, branch_id, delta, reason,
                 created_by=None, correlation_id=None):
        super().__init__(
            event_type=EventType.STOCK_ADJUSTED,
            aggregate_id=product_id,
            aggregate_type=AggregateType.INVENTORY,
            payload={"product_id": product_id, "branch_id": branch_id,
                     "delta": delta, "reason": reason},
            branch_id=branch_id, created_by=created_by,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )


@dataclass
class PriceAdjustedEvent(DomainEvent):
    def __init__(self, product_id, branch_id, old_price, new_price,
                 discount_percentage, risk_score, reason, created_by=None):
        super().__init__(
            event_type=EventType.PRICE_ADJUSTED,
            aggregate_id=product_id,
            aggregate_type=AggregateType.PRODUCT,
            payload={"product_id": product_id, "branch_id": branch_id,
                     "old_price": old_price, "new_price": new_price,
                     "discount_percentage": discount_percentage,
                     "risk_score": risk_score, "reason": reason},
            branch_id=branch_id, created_by=created_by,
        )


# ── Order Events ──────────────────────────────────────────────────────────────

@dataclass
class OrderCreatedEvent(DomainEvent):
    def __init__(self, order_id, branch_id, cashier_id):
        super().__init__(
            event_type=EventType.ORDER_CREATED,
            aggregate_id=order_id,
            aggregate_type=AggregateType.ORDER,
            payload={"order_id": order_id, "branch_id": branch_id,
                     "cashier_id": cashier_id},
            branch_id=branch_id, created_by=cashier_id,
        )


@dataclass
class OrderItemAddedEvent(DomainEvent):
    def __init__(self, order_id, branch_id, product_id, product_name,
                 barcode, quantity, unit_price, cashier_id):
        super().__init__(
            event_type=EventType.ORDER_ITEM_ADDED,
            aggregate_id=order_id,
            aggregate_type=AggregateType.ORDER,
            payload={"order_id": order_id, "product_id": product_id,
                     "product_name": product_name, "barcode": barcode,
                     "quantity": quantity, "unit_price": unit_price},
            branch_id=branch_id, created_by=cashier_id,
        )


@dataclass
class OrderCompletedEvent(DomainEvent):
    def __init__(self, order_id, branch_id, cashier_id, subtotal,
                 tax_amount, total_amount, payment_method, item_count):
        super().__init__(
            event_type=EventType.ORDER_COMPLETED,
            aggregate_id=order_id,
            aggregate_type=AggregateType.ORDER,
            payload={"order_id": order_id, "branch_id": branch_id,
                     "subtotal": subtotal, "tax_amount": tax_amount,
                     "total_amount": total_amount,
                     "payment_method": payment_method,
                     "item_count": item_count},
            branch_id=branch_id, created_by=cashier_id,
        )


@dataclass
class OrderCancelledEvent(DomainEvent):
    def __init__(self, order_id, branch_id, reason, cancelled_by):
        super().__init__(
            event_type=EventType.ORDER_CANCELLED,
            aggregate_id=order_id,
            aggregate_type=AggregateType.ORDER,
            payload={"order_id": order_id, "reason": reason},
            branch_id=branch_id, created_by=cancelled_by,
        )