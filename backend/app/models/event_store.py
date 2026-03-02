import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class EventStore(Base):
    """
    Append-only event log. NEVER update or delete rows here.
    Every state change in the system must flow through this table.
    """

    __tablename__ = "event_store"

    __table_args__ = (
        # Fast replay queries: ORDER BY aggregate_id, version
        Index("ix_event_store_aggregate_version", "aggregate_id", "version"),
        # Fast replay by time: for full system replay
        Index("ix_event_store_created_at", "created_at"),
        # Fast queries by event type
        Index("ix_event_store_event_type", "event_type"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # aggregate_id is the product_id or order_id this event belongs to
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g. "product", "order"
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "ItemSold", "StockReceived"
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )  # ties commands to events
    branch_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)  # user_id
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<EventStore type={self.event_type} "
            f"aggregate={self.aggregate_id} v={self.version}>"
        )