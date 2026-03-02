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
    ORDER_COMPLETED = "OrderCompleted"
    ORDER_CANCELLED = "OrderCancelled"


class AggregateType(str, Enum):
    PRODUCT = "product"
    ORDER = "order"
    INVENTORY = "inventory"


@dataclass
class DomainEvent:
    """Base domain event. All events in the system derive from this."""

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
    def __init__(
        self,
        product_id: str,
        branch_id: str,
        quantity: int,
        created_by: str | None = None,
        correlation_id: str | None = None,
    ):
        super().__init__(
            event_type=EventType.STOCK_RECEIVED,
            aggregate_id=product_id,
            aggregate_type=AggregateType.INVENTORY,
            payload={"product_id": product_id, "branch_id": branch_id, "quantity": quantity},
            branch_id=branch_id,
            created_by=created_by,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )


@dataclass
class ItemSoldEvent(DomainEvent):
    def __init__(
        self,
        product_id: str,
        branch_id: str,
        quantity: int,
        unit_price: float,
        order_id: str,
        created_by: str | None = None,
        correlation_id: str | None = None,
    ):
        super().__init__(
            event_type=EventType.ITEM_SOLD,
            aggregate_id=product_id,
            aggregate_type=AggregateType.INVENTORY,
            payload={
                "product_id": product_id,
                "branch_id": branch_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "order_id": order_id,
            },
            branch_id=branch_id,
            created_by=created_by,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )


@dataclass
class StockAdjustedEvent(DomainEvent):
    def __init__(
        self,
        product_id: str,
        branch_id: str,
        delta: int,  # positive = add, negative = remove
        reason: str,
        created_by: str | None = None,
        correlation_id: str | None = None,
    ):
        super().__init__(
            event_type=EventType.STOCK_ADJUSTED,
            aggregate_id=product_id,
            aggregate_type=AggregateType.INVENTORY,
            payload={
                "product_id": product_id,
                "branch_id": branch_id,
                "delta": delta,
                "reason": reason,
            },
            branch_id=branch_id,
            created_by=created_by,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )


@dataclass
class PriceAdjustedEvent(DomainEvent):
    def __init__(
        self,
        product_id: str,
        branch_id: str,
        old_price: float,
        new_price: float,
        discount_percentage: float,
        risk_score: float,
        reason: str,
        created_by: str | None = None,
    ):
        super().__init__(
            event_type=EventType.PRICE_ADJUSTED,
            aggregate_id=product_id,
            aggregate_type=AggregateType.PRODUCT,
            payload={
                "product_id": product_id,
                "branch_id": branch_id,
                "old_price": old_price,
                "new_price": new_price,
                "discount_percentage": discount_percentage,
                "risk_score": risk_score,
                "reason": reason,
            },
            branch_id=branch_id,
            created_by=created_by,
        )