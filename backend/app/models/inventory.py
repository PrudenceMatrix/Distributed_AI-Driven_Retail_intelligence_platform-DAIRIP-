from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class InventoryProjection(Base):
    """
    Read-optimized projection of current inventory state.
    Never mutated directly by business logic — only updated by projection handlers
    that consume events from the event store.
    """

    __tablename__ = "inventory_projections"

    __table_args__ = (
        UniqueConstraint("product_id", "branch_id", name="uq_inventory_product_branch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False, index=True
    )
    branch_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    available_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_event_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # tracks which event version we're at
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="inventory_projections")  # noqa: F821

    @property
    def total_quantity(self) -> int:
        return self.available_quantity + self.reserved_quantity

    def __repr__(self) -> str:
        return (
            f"<InventoryProjection product={self.product_id} "
            f"branch={self.branch_id} qty={self.available_quantity}>"
        )