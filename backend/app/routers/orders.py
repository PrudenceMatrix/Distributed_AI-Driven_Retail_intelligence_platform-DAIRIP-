from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas import MessageResponse
from app.auth import require_any_role, require_manager_or_above
from app.services.order_service import order_service
from app.core.exceptions import InsufficientStockError, ProductNotFoundError

router = APIRouter(prefix="/orders", tags=["Orders (POS)"])


class CreateOrderRequest(BaseModel):
    branch_id: str


class ScanItemRequest(BaseModel):
    barcode: str
    quantity: int = Field(default=1, gt=0)


class CheckoutRequest(BaseModel):
    payment_method: str = "cash"


class CancelOrderRequest(BaseModel):
    reason: str = Field(..., min_length=1)


@router.post("", response_model=MessageResponse, status_code=201)
def create_order(
    body: CreateOrderRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_any_role)],
):
    """Cashier opens a new cart. Returns order_id to use for scanning."""
    order = order_service.create_order(db, body.branch_id, current_user.id)
    return MessageResponse(
        message="Order created. Ready to scan items.",
        data={
            "order_id": order.id,
            "branch_id": order.branch_id,
            "cashier": current_user.full_name,
            "status": order.status.value,
        },
    )


@router.post("/{order_id}/scan", response_model=MessageResponse)
def scan_item(
    order_id: str,
    body: ScanItemRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_any_role)],
):
    """Scan a barcode and add product to the cart."""
    try:
        result = order_service.scan_item(
            db, order_id, body.barcode, body.quantity, current_user.id
        )
    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InsufficientStockError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return MessageResponse(message=f"'{result['product_name']}' added to cart.", data=result)


@router.post("/{order_id}/checkout", response_model=MessageResponse)
def checkout(
    order_id: str,
    body: CheckoutRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_any_role)],
):
    """
    Finalize the order. Deducts all stock atomically,
    fires events, returns receipt.
    """
    try:
        receipt = order_service.checkout(
            db, order_id, body.payment_method, current_user.id
        )
    except InsufficientStockError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return MessageResponse(message="Checkout complete.", data=receipt)


@router.post("/{order_id}/cancel", response_model=MessageResponse)
def cancel_order(
    order_id: str,
    body: CancelOrderRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_manager_or_above)],
):
    """Void/cancel an open order. Manager only."""
    try:
        result = order_service.cancel_order(
            db, order_id, body.reason, current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return MessageResponse(message="Order cancelled.", data=result)


@router.get("/{order_id}", response_model=MessageResponse)
def get_order(
    order_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_any_role)],
):
    """Get order details and current cart contents."""
    try:
        order = order_service.get_order(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    receipt = order_service._build_receipt(order)
    return MessageResponse(message="Order retrieved.", data=receipt)