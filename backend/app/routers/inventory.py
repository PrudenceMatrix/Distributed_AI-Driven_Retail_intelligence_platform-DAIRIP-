import json
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.forecast import IdempotencyKey
from app.schemas import (
    ReceiveStockRequest,
    SellItemRequest,
    StockAdjustRequest,
    InventoryResponse,
    MessageResponse,
)
from app.services.inventory_service import inventory_service
from app.auth import require_any_role, require_manager_or_above
from app.core.exceptions import InsufficientStockError, ProductNotFoundError

router = APIRouter(prefix="/inventory", tags=["Inventory"])


def _check_idempotency(db: Session, key: str) -> IdempotencyKey | None:
    return db.scalar(select(IdempotencyKey).where(IdempotencyKey.key == key))


def _store_idempotency(db: Session, key: str, response_body: dict, status_code: int = 200):
    record = IdempotencyKey(
        key=key,
        response_body=json.dumps(response_body),
        status_code=status_code,
    )
    db.add(record)
    db.commit()


@router.post("/receive", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def receive_stock(
    body: ReceiveStockRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_manager_or_above)],
    x_idempotency_key: Annotated[str | None, Header()] = None,
):
    if x_idempotency_key:
        cached = _check_idempotency(db, x_idempotency_key)
        if cached:
            return MessageResponse(
                message="Duplicate request (idempotent response)",
                data=json.loads(cached.response_body),
            )

    try:
        result = inventory_service.receive_stock(
            db, body.product_id, body.branch_id, body.quantity, current_user.id
        )
    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if x_idempotency_key:
        _store_idempotency(db, x_idempotency_key, result)

    return MessageResponse(message="Stock received successfully", data=result)


@router.post("/sell", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def sell_item(
    body: SellItemRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_any_role)],
    x_idempotency_key: Annotated[str | None, Header()] = None,
):
    if x_idempotency_key:
        cached = _check_idempotency(db, x_idempotency_key)
        if cached:
            return MessageResponse(
                message="Duplicate request (idempotent response)",
                data=json.loads(cached.response_body),
            )

    try:
        result = inventory_service.sell_item(
            db,
            body.product_id,
            body.branch_id,
            body.quantity,
            body.unit_price,
            body.order_id,
            current_user.id,
        )
    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InsufficientStockError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if x_idempotency_key:
        _store_idempotency(db, x_idempotency_key, result)

    return MessageResponse(message="Sale processed successfully", data=result)


@router.post("/adjust", response_model=MessageResponse)
def adjust_stock(
    body: StockAdjustRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_manager_or_above)],
):
    try:
        result = inventory_service.adjust_stock(
            db, body.product_id, body.branch_id, body.delta, body.reason, current_user.id
        )
    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return MessageResponse(message="Stock adjusted", data=result)


@router.get("/{product_id}/{branch_id}", response_model=InventoryResponse)
def get_inventory(
    product_id: str,
    branch_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_any_role)],
):
    inv = inventory_service.get_inventory(db, product_id, branch_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory record not found")
    return inv


@router.post("/replay", response_model=MessageResponse)
def replay_projections(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_manager_or_above)],
):
    """Wipes inventory projections and rebuilds from event store. Use for recovery."""
    count = inventory_service.replay_projections(db)
    return MessageResponse(
        message="Projection replay complete",
        data={"events_replayed": count},
    )