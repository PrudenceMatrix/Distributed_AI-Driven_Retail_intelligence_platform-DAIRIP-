from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas import MessageResponse
from app.auth import require_any_role, require_manager_or_above
from app.services.forecast_service import forecast_service
from app.services.perishable_service import perishable_service
from app.core.exceptions import ProductNotFoundError

router = APIRouter(prefix="/ai", tags=["AI Engine"])


@router.get("/forecast/{product_id}/{branch_id}", response_model=MessageResponse)
def get_demand_forecast(
    product_id: str,
    branch_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_any_role)],
    horizon_days: int = 7,
):
    """
    Generate AI demand forecast for a product at a branch.
    Uses historical ItemSold events + sklearn linear regression.
    Returns daily predicted demand for next N days.
    """
    try:
        result = forecast_service.forecast_product(
            db, product_id, branch_id, horizon_days
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return MessageResponse(message="Forecast generated successfully", data=result)


@router.post("/perishable/analyze/{product_id}/{branch_id}", response_model=MessageResponse)
def analyze_perishable(
    product_id: str,
    branch_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_manager_or_above)],
):
    """
    Run perishable risk analysis on a single product.

    Risk formula: (current_stock - predicted_demand) / days_to_expiry

    If risk exceeds threshold:
    - Fires PriceAdjusted domain event
    - Applies automatic discount
    - Updates pricing_rules table
    """
    try:
        result = perishable_service.analyze_product(
            db, product_id, branch_id, current_user.id
        )
    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return MessageResponse(message="Perishable analysis complete", data=result)


@router.post("/perishable/analyze-all/{branch_id}", response_model=MessageResponse)
def analyze_all_perishables(
    branch_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_manager_or_above)],
):
    """
    Run perishable risk analysis on ALL perishable products for a branch.
    Intended to be called every morning as a batch job.
    """
    results = perishable_service.analyze_all_perishables(
        db, branch_id, current_user.id
    )

    discounts_applied = sum(1 for r in results if r.get("action") == "discount_applied")
    skipped = sum(1 for r in results if r.get("action") == "skipped")

    return MessageResponse(
        message=f"Batch analysis complete. {discounts_applied} discounts applied, {skipped} skipped.",
        data={
            "branch_id": branch_id,
            "products_analyzed": len(results),
            "discounts_applied": discounts_applied,
            "results": results,
        },
    )


@router.get("/pricing-rules/{branch_id}", response_model=MessageResponse)
def get_active_pricing_rules(
    branch_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_any_role)],
):
    """Returns all active auto-generated discount rules for a branch."""
    from sqlalchemy import select
    from app.models.forecast import PricingRule
    from app.models.product import Product

    stmt = (
        select(PricingRule, Product)
        .join(Product, PricingRule.product_id == Product.id)
        .where(
            PricingRule.branch_id == branch_id,
            PricingRule.is_active == True,  # noqa: E712
        )
    )
    rows = db.execute(stmt).all()

    rules = [
        {
            "product_id": rule.product_id,
            "product_name": product.name,
            "sku": product.sku,
            "original_price": product.base_price,
            "discounted_price": rule.adjusted_price,
            "discount_percentage": rule.discount_percentage,
            "risk_score": rule.risk_score,
            "updated_at": rule.updated_at.isoformat(),
        }
        for rule, product in rows
    ]

    return MessageResponse(
        message=f"{len(rules)} active pricing rules",
        data={"branch_id": branch_id, "rules": rules},
    )