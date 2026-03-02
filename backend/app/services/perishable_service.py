import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.product import Product
from app.models.inventory import InventoryProjection
from app.models.forecast import DemandForecast, PricingRule
from app.events import (
    event_store_service,
    event_dispatcher,
    PriceAdjustedEvent,
)
from app.core.exceptions import ProductNotFoundError

logger = logging.getLogger(__name__)


class PerishableService:
    """
    Perishable Optimization Engine.

    Risk Formula (from design doc):
        risk_score = (current_stock - predicted_demand) / days_to_expiry

    If risk_score > threshold:
        - Generate PriceAdjusted event
        - Update pricing_rules table
        - Discount scales with risk severity

    Discount tiers:
        risk 1.5–3.0  → 10% discount
        risk 3.0–5.0  → 20% discount
        risk 5.0–8.0  → 30% discount
        risk > 8.0    → 40% discount (maximum)
    """

    RISK_THRESHOLD = 1.5

    DISCOUNT_TIERS = [
        (8.0, 0.40),
        (5.0, 0.30),
        (3.0, 0.20),
        (1.5, 0.10),
    ]

    def analyze_product(
        self,
        db: Session,
        product_id: str,
        branch_id: str,
        created_by: str | None = None,
    ) -> dict:
        """
        Run risk analysis on a perishable product.
        Returns risk assessment and applies discount if threshold exceeded.
        """
        product = db.get(Product, product_id)
        if not product:
            raise ProductNotFoundError(f"Product {product_id} not found")

        if not product.is_perishable:
            return {
                "product_id": product_id,
                "product_name": product.name,
                "is_perishable": False,
                "action": "skipped",
                "reason": "Product is not perishable",
            }

        if not product.expiry_days:
            return {
                "product_id": product_id,
                "product_name": product.name,
                "is_perishable": True,
                "action": "skipped",
                "reason": "No expiry_days defined for product",
            }

        # Get current stock
        current_stock = self._get_stock(db, product_id, branch_id)

        # Get predicted demand for expiry window
        predicted_demand = self._get_predicted_demand(
            db, product_id, branch_id, product.expiry_days
        )

        # Calculate risk score
        days_to_expiry = product.expiry_days
        if days_to_expiry <= 0:
            risk_score = 999.0  # already expired
        else:
            risk_score = (current_stock - predicted_demand) / days_to_expiry

        result = {
            "product_id": product_id,
            "product_name": product.name,
            "branch_id": branch_id,
            "current_stock": current_stock,
            "predicted_demand": round(predicted_demand, 1),
            "days_to_expiry": days_to_expiry,
            "risk_score": round(risk_score, 3),
            "risk_threshold": self.RISK_THRESHOLD,
        }

        if risk_score > self.RISK_THRESHOLD:
            discount = self._calculate_discount(risk_score)
            old_price = product.current_price
            new_price = round(product.base_price * (1 - discount), 2)

            # Fire PriceAdjusted domain event
            event = PriceAdjustedEvent(
                product_id=product_id,
                branch_id=branch_id,
                old_price=old_price,
                new_price=new_price,
                discount_percentage=discount * 100,
                risk_score=risk_score,
                reason=f"Perishable risk score {risk_score:.2f} exceeded threshold {self.RISK_THRESHOLD}",
                created_by=created_by,
            )
            stored = event_store_service.append(db, event)
            event_dispatcher.dispatch(stored, db)

            # Update product current price
            product.current_price = new_price

            # Upsert pricing rule
            self._upsert_pricing_rule(
                db, product_id, branch_id, discount, risk_score, new_price
            )

            db.commit()

            result.update({
                "action": "discount_applied",
                "discount_percentage": round(discount * 100, 1),
                "old_price": old_price,
                "new_price": new_price,
                "event_id": stored.id,
            })

            logger.info(
                f"Perishable discount applied: product={product_id} "
                f"risk={risk_score:.2f} discount={discount*100:.0f}% "
                f"price {old_price}→{new_price}"
            )
        else:
            result.update({
                "action": "no_action",
                "reason": f"Risk score {risk_score:.2f} below threshold {self.RISK_THRESHOLD}",
            })

        return result

    def analyze_all_perishables(
        self,
        db: Session,
        branch_id: str,
        created_by: str | None = None,
    ) -> list[dict]:
        """
        Run risk analysis on ALL perishable products for a branch.
        Call this on a schedule (e.g. every morning).
        """
        stmt = select(Product).where(Product.is_perishable == True)  # noqa: E712
        products = list(db.scalars(stmt).all())

        results = []
        for product in products:
            try:
                result = self.analyze_product(db, product.id, branch_id, created_by)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to analyze product {product.id}: {e}")
                results.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "action": "error",
                    "reason": str(e),
                })

        return results

    def _get_stock(self, db: Session, product_id: str, branch_id: str) -> int:
        stmt = select(InventoryProjection).where(
            InventoryProjection.product_id == product_id,
            InventoryProjection.branch_id == branch_id,
        )
        projection = db.scalar(stmt)
        return projection.available_quantity if projection else 0

    def _get_predicted_demand(
        self, db: Session, product_id: str, branch_id: str, days: int
    ) -> float:
        """Sum forecasted demand over the expiry window."""
        cutoff = datetime.utcnow() + timedelta(days=days)
        stmt = select(DemandForecast).where(
            DemandForecast.product_id == product_id,
            DemandForecast.branch_id == branch_id,
            DemandForecast.forecast_date <= cutoff,
        )
        forecasts = list(db.scalars(stmt).all())

        if forecasts:
            return sum(f.predicted_demand for f in forecasts)

        # No forecast data yet — use a conservative estimate
        from app.services.forecast_service import forecast_service
        logger.info(f"No forecast found for {product_id}, generating on-the-fly...")
        try:
            forecast_service.forecast_product(db, product_id, branch_id, days)
            forecasts = list(db.scalars(stmt).all())
            return sum(f.predicted_demand for f in forecasts) if forecasts else days * 5.0
        except Exception:
            return days * 5.0  # fallback: 5 units/day

    def _calculate_discount(self, risk_score: float) -> float:
        """Map risk score to discount percentage."""
        for threshold, discount in self.DISCOUNT_TIERS:
            if risk_score >= threshold:
                return discount
        return 0.10  # minimum discount

    def _upsert_pricing_rule(
        self,
        db: Session,
        product_id: str,
        branch_id: str,
        discount: float,
        risk_score: float,
        new_price: float,
    ):
        stmt = select(PricingRule).where(
            PricingRule.product_id == product_id,
            PricingRule.branch_id == branch_id,
        )
        rule = db.scalar(stmt)

        if rule:
            rule.discount_percentage = discount * 100
            rule.risk_score = risk_score
            rule.adjusted_price = new_price
            rule.is_active = True
            rule.updated_at = datetime.utcnow()
        else:
            rule = PricingRule(
                product_id=product_id,
                branch_id=branch_id,
                discount_percentage=discount * 100,
                risk_score=risk_score,
                adjusted_price=new_price,
                reason="Auto-generated by perishable optimizer",
                is_active=True,
            )
            db.add(rule)


# Singleton
perishable_service = PerishableService()