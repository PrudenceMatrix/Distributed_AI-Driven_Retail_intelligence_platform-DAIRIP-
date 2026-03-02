import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    is_perishable: Mapped[bool] = mapped_column(Boolean, default=False)
    base_price: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, nullable=False)
    expiry_days: Mapped[int | None] = mapped_column(nullable=True)  # shelf life in days
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    inventory_projections: Mapped[list["InventoryProjection"]] = relationship(  # noqa: F821
        "InventoryProjection", back_populates="product", lazy="select"
    )
    demand_forecasts: Mapped[list["DemandForecast"]] = relationship(  # noqa: F821
        "DemandForecast", back_populates="product", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Product sku={self.sku} name={self.name}>"