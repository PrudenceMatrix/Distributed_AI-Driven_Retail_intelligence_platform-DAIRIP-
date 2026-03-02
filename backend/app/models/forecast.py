from datetime import datetime
from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class DemandForecast(Base):
    __tablename__ = "demand_forecasts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False, index=True
    )
    branch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    forecast_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    predicted_demand: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_reorder_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped["Product"] = relationship("Product", back_populates="demand_forecasts")  # noqa: F821


class IdempotencyKey(Base):
    """
    Stores processed idempotency keys to prevent duplicate transaction processing.
    Records expire after 24 hours (enforced at application level).
    """

    __tablename__ = "idempotency_keys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    response_body: Mapped[str] = mapped_column(Text, nullable=True)  # cached JSON response
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PricingRule(Base):
    """Stores auto-generated discount rules from perishable optimization engine."""

    __tablename__ = "pricing_rules"

    __table_args__ = (
        UniqueConstraint("product_id", "branch_id", name="uq_pricing_product_branch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False, index=True
    )
    branch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    discount_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    adjusted_price: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )