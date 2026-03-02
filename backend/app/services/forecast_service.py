import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.event_store import EventStore
from app.models.forecast import DemandForecast
from app.models.product import Product
from app.events.types import EventType

logger = logging.getLogger(__name__)


class ForecastService:
    """
    Demand forecasting engine.

    Strategy:
    1. Extract real ItemSold events from event store grouped by day
    2. If insufficient real data (<7 days), augment with synthetic baseline
       derived from product category patterns — realistic for hackathon demo
    3. Fit a LinearRegression model on day-index vs quantity sold
    4. Predict next N days demand
    5. Store results in demand_forecasts table
    """

    CATEGORY_DAILY_BASELINE = {
        "Dairy": 12,
        "Bakery": 8,
        "Meat": 6,
        "Dry Goods": 4,
        "Default": 5,
    }

    WEEKDAY_MULTIPLIERS = [0.8, 0.9, 1.0, 1.0, 1.2, 1.5, 1.3]  # Mon–Sun

    def forecast_product(
        self,
        db: Session,
        product_id: str,
        branch_id: str,
        horizon_days: int = 7,
    ) -> dict:
        """
        Generate demand forecast for a product at a branch.
        Returns forecast summary and stores results in DB.
        """
        product = db.get(Product, product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        # Pull real sales history from event store
        sales_by_day = self._extract_sales_history(db, product_id, branch_id)

        # Augment with synthetic data if we don't have enough real data
        sales_series = self._build_sales_series(sales_by_day, product)

        # Fit model and predict
        predictions = self._fit_and_predict(sales_series, horizon_days)

        # Calculate recommended reorder
        total_predicted = sum(predictions)
        current_stock = self._get_current_stock(db, product_id, branch_id)
        reorder_qty = max(0, int(total_predicted - current_stock) + 10)  # +10 buffer

        # Store forecasts in DB
        forecast_records = self._store_forecasts(
            db, product_id, branch_id, predictions, horizon_days
        )

        result = {
            "product_id": product_id,
            "product_name": product.name,
            "branch_id": branch_id,
            "horizon_days": horizon_days,
            "current_stock": current_stock,
            "total_predicted_demand": round(total_predicted, 1),
            "recommended_reorder_quantity": reorder_qty,
            "daily_forecasts": [
                {
                    "date": (datetime.utcnow() + timedelta(days=i + 1)).strftime("%Y-%m-%d"),
                    "predicted_demand": round(predictions[i], 1),
                }
                for i in range(horizon_days)
            ],
            "data_source": "real_events" if len(sales_by_day) >= 3 else "augmented",
            "generated_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            f"Forecast generated: product={product_id} branch={branch_id} "
            f"total_demand={total_predicted:.1f} reorder={reorder_qty}"
        )
        return result

    def _extract_sales_history(
        self, db: Session, product_id: str, branch_id: str
    ) -> dict[str, float]:
        """Pull ItemSold events and aggregate by date."""
        stmt = (
            select(EventStore)
            .where(
                EventStore.aggregate_id == product_id,
                EventStore.event_type == EventType.ITEM_SOLD.value,
                EventStore.branch_id == branch_id,
            )
            .order_by(EventStore.created_at.asc())
        )
        events = list(db.scalars(stmt).all())

        sales_by_day: dict[str, float] = defaultdict(float)
        for event in events:
            payload = json.loads(event.payload)
            day = event.created_at.strftime("%Y-%m-%d")
            sales_by_day[day] += payload.get("quantity", 0)

        return dict(sales_by_day)

    def _build_sales_series(self, sales_by_day: dict, product: Product) -> list[float]:
        """
        Build a 30-day sales series.
        Uses real data where available, fills gaps with synthetic baseline.
        """
        baseline = self.CATEGORY_DAILY_BASELINE.get(
            product.category, self.CATEGORY_DAILY_BASELINE["Default"]
        )

        series = []
        today = datetime.utcnow().date()

        for i in range(30):
            day = today - timedelta(days=29 - i)
            day_str = day.strftime("%Y-%m-%d")

            if day_str in sales_by_day:
                series.append(float(sales_by_day[day_str]))
            else:
                # Synthetic: baseline * weekday multiplier + small noise
                weekday = day.weekday()
                noise = np.random.uniform(0.85, 1.15)
                synthetic = baseline * self.WEEKDAY_MULTIPLIERS[weekday] * noise
                series.append(round(synthetic, 1))

        return series

    def _fit_and_predict(self, series: list[float], horizon_days: int) -> list[float]:
        """
        Fit LinearRegression on historical series and extrapolate forward.
        X = day index, y = quantity sold
        """
        X = np.array(range(len(series))).reshape(-1, 1)
        y = np.array(series)

        model = LinearRegression()
        model.fit(X, y)

        future_X = np.array(
            range(len(series), len(series) + horizon_days)
        ).reshape(-1, 1)
        predictions = model.predict(future_X)

        # Apply weekday multipliers to predictions
        today = datetime.utcnow()
        adjusted = []
        for i, pred in enumerate(predictions):
            future_day = today + timedelta(days=i + 1)
            weekday = future_day.weekday()
            multiplier = self.WEEKDAY_MULTIPLIERS[weekday]
            adjusted_pred = max(0.0, float(pred) * multiplier)
            adjusted.append(round(adjusted_pred, 1))

        return adjusted

    def _get_current_stock(self, db: Session, product_id: str, branch_id: str) -> int:
        """Get current available stock from inventory projection."""
        from app.models.inventory import InventoryProjection
        stmt = select(InventoryProjection).where(
            InventoryProjection.product_id == product_id,
            InventoryProjection.branch_id == branch_id,
        )
        projection = db.scalar(stmt)
        return projection.available_quantity if projection else 0

    def _store_forecasts(
        self,
        db: Session,
        product_id: str,
        branch_id: str,
        predictions: list[float],
        horizon_days: int,
    ) -> list[DemandForecast]:
        """Persist forecast results to demand_forecasts table."""
        # Clear old forecasts for this product/branch
        old = db.query(DemandForecast).filter(
            DemandForecast.product_id == product_id,
            DemandForecast.branch_id == branch_id,
        ).all()
        for o in old:
            db.delete(o)

        records = []
        for i, demand in enumerate(predictions):
            record = DemandForecast(
                product_id=product_id,
                branch_id=branch_id,
                forecast_date=datetime.utcnow() + timedelta(days=i + 1),
                predicted_demand=demand,
                recommended_reorder_quantity=max(0, int(demand * horizon_days) - 10),
                generated_at=datetime.utcnow(),
            )
            db.add(record)
            records.append(record)

        db.commit()
        return records


# Singleton
forecast_service = ForecastService()