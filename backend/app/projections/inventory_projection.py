import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.inventory import InventoryProjection
from app.models.event_store import EventStore
from app.events.dispatcher import register_handler
from app.events.types import EventType

logger = logging.getLogger(__name__)


def _get_or_create_projection(
    db: Session, product_id: str, branch_id: str, current_price: float = 0.0
) -> InventoryProjection:
    stmt = select(InventoryProjection).where(
        InventoryProjection.product_id == product_id,
        InventoryProjection.branch_id == branch_id,
    )
    projection = db.scalar(stmt)
    if not projection:
        projection = InventoryProjection(
            product_id=product_id,
            branch_id=branch_id,
            available_quantity=0,
            reserved_quantity=0,
            current_price=current_price,
        )
        db.add(projection)
        db.flush()
    return projection


@register_handler(EventType.STOCK_RECEIVED)
def handle_stock_received(event: EventStore, db: Session) -> None:
    payload = json.loads(event.payload)
    projection = _get_or_create_projection(db, payload["product_id"], payload["branch_id"])
    projection.available_quantity += payload["quantity"]
    projection.last_event_version = event.version
    logger.info(
        f"[Projection] StockReceived: product={payload['product_id']} "
        f"branch={payload['branch_id']} +{payload['quantity']}"
    )


@register_handler(EventType.ITEM_SOLD)
def handle_item_sold(event: EventStore, db: Session) -> None:
    payload = json.loads(event.payload)
    projection = _get_or_create_projection(db, payload["product_id"], payload["branch_id"])

    if projection.available_quantity < payload["quantity"]:
        # This should never happen because the service layer validates first,
        # but we guard defensively here.
        logger.error(
            f"[Projection] ITEM_SOLD would result in negative stock for "
            f"product={payload['product_id']} branch={payload['branch_id']}"
        )
        return

    projection.available_quantity -= payload["quantity"]
    projection.last_event_version = event.version
    logger.info(
        f"[Projection] ItemSold: product={payload['product_id']} "
        f"branch={payload['branch_id']} -{payload['quantity']}"
    )


@register_handler(EventType.STOCK_ADJUSTED)
def handle_stock_adjusted(event: EventStore, db: Session) -> None:
    payload = json.loads(event.payload)
    projection = _get_or_create_projection(db, payload["product_id"], payload["branch_id"])
    projection.available_quantity = max(0, projection.available_quantity + payload["delta"])
    projection.last_event_version = event.version
    logger.info(
        f"[Projection] StockAdjusted: product={payload['product_id']} "
        f"delta={payload['delta']} reason={payload['reason']}"
    )


@register_handler(EventType.PRICE_ADJUSTED)
def handle_price_adjusted(event: EventStore, db: Session) -> None:
    payload = json.loads(event.payload)
    projection = _get_or_create_projection(db, payload["product_id"], payload["branch_id"])
    projection.current_price = payload["new_price"]
    projection.last_event_version = event.version
    logger.info(
        f"[Projection] PriceAdjusted: product={payload['product_id']} "
        f"new_price={payload['new_price']} discount={payload['discount_percentage']}%"
    )