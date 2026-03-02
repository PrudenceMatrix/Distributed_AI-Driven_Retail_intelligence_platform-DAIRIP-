import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.inventory import InventoryProjection
from app.models.product import Product
from app.events import (
    event_store_service,
    event_dispatcher,
    StockReceivedEvent,
    ItemSoldEvent,
    StockAdjustedEvent,
)
from app.core.exceptions import (
    InsufficientStockError,
    ProductNotFoundError,
)

logger = logging.getLogger(__name__)


class InventoryService:

    def receive_stock(
        self,
        db: Session,
        product_id: str,
        branch_id: str,
        quantity: int,
        created_by: str | None = None,
    ) -> dict:
        """
        Record stock receipt for a product at a branch.
        Appends StockReceived event → projection handler updates inventory.
        """
        self._assert_product_exists(db, product_id)

        event = StockReceivedEvent(
            product_id=product_id,
            branch_id=branch_id,
            quantity=quantity,
            created_by=created_by,
        )

        stored = event_store_service.append(db, event)
        event_dispatcher.dispatch(stored, db)
        db.commit()

        logger.info(f"Stock received: product={product_id} branch={branch_id} qty={quantity}")
        return {
            "event_id": stored.id,
            "product_id": product_id,
            "branch_id": branch_id,
            "quantity_added": quantity,
            "version": stored.version,
        }

    def sell_item(
        self,
        db: Session,
        product_id: str,
        branch_id: str,
        quantity: int,
        unit_price: float,
        order_id: str,
        created_by: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        """
        Process a sale transaction.

        Flow:
        1. Check idempotency key (handled by middleware/router)
        2. Validate product exists
        3. Lock inventory row and validate available stock
        4. Append ItemSold event
        5. Dispatch to projection handler
        6. Commit
        """
        self._assert_product_exists(db, product_id)

        # Lock the inventory row for this product/branch (SELECT FOR UPDATE)
        projection = db.execute(
            select(InventoryProjection)
            .where(
                InventoryProjection.product_id == product_id,
                InventoryProjection.branch_id == branch_id,
            )
            .with_for_update()
        ).scalar_one_or_none()

        available = projection.available_quantity if projection else 0

        if available < quantity:
            raise InsufficientStockError(
                f"Cannot sell {quantity} units of product {product_id} "
                f"in branch {branch_id}. Available: {available}."
            )

        event = ItemSoldEvent(
            product_id=product_id,
            branch_id=branch_id,
            quantity=quantity,
            unit_price=unit_price,
            order_id=order_id,
            created_by=created_by,
        )

        stored = event_store_service.append(db, event)
        event_dispatcher.dispatch(stored, db)
        db.commit()

        logger.info(
            f"Item sold: product={product_id} branch={branch_id} "
            f"qty={quantity} price={unit_price} order={order_id}"
        )
        return {
            "event_id": stored.id,
            "product_id": product_id,
            "branch_id": branch_id,
            "quantity_sold": quantity,
            "unit_price": unit_price,
            "order_id": order_id,
            "version": stored.version,
        }

    def adjust_stock(
        self,
        db: Session,
        product_id: str,
        branch_id: str,
        delta: int,
        reason: str,
        created_by: str | None = None,
    ) -> dict:
        """Manual stock correction (shrinkage, damage, audit adjustment)."""
        self._assert_product_exists(db, product_id)

        event = StockAdjustedEvent(
            product_id=product_id,
            branch_id=branch_id,
            delta=delta,
            reason=reason,
            created_by=created_by,
        )

        stored = event_store_service.append(db, event)
        event_dispatcher.dispatch(stored, db)
        db.commit()

        return {
            "event_id": stored.id,
            "product_id": product_id,
            "branch_id": branch_id,
            "delta": delta,
            "reason": reason,
            "version": stored.version,
        }

    def get_inventory(
        self,
        db: Session,
        product_id: str,
        branch_id: str,
    ) -> InventoryProjection | None:
        stmt = select(InventoryProjection).where(
            InventoryProjection.product_id == product_id,
            InventoryProjection.branch_id == branch_id,
        )
        return db.scalar(stmt)

    def replay_projections(self, db: Session) -> int:
        """
        Full event replay: clears all inventory projections and rebuilds from scratch.
        USE WITH CAUTION in production. Safe for hackathon demos.
        Returns count of events replayed.
        """
        logger.warning("Starting full inventory projection replay...")

        # Clear projection table
        db.query(InventoryProjection).delete()
        db.flush()

        # Replay all events
        all_events = event_store_service.get_all_events_ordered(db)
        replayed = 0

        for stored_event in all_events:
            event_dispatcher.dispatch(stored_event, db)
            replayed += 1

        db.commit()
        logger.warning(f"Replay complete. {replayed} events processed.")
        return replayed

    def _assert_product_exists(self, db: Session, product_id: str) -> Product:
        product = db.get(Product, product_id)
        if not product:
            raise ProductNotFoundError(f"Product {product_id} not found.")
        return product


# Singleton
inventory_service = InventoryService()