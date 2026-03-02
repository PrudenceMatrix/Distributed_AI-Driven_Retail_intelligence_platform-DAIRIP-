import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.product import Product
from app.schemas import ProductCreate, ProductResponse, MessageResponse
from app.auth import require_manager_or_above, require_any_role
from app.models.user import User

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    body: ProductCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_manager_or_above)],
):
    # Check SKU uniqueness
    existing = db.scalar(select(Product).where(Product.sku == body.sku))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with SKU '{body.sku}' already exists.",
        )

    product = Product(
        id=str(uuid.uuid4()),
        name=body.name,
        sku=body.sku,
        category=body.category,
        is_perishable=body.is_perishable,
        base_price=body.base_price,
        current_price=body.base_price,
        expiry_days=body.expiry_days,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=list[ProductResponse])
def list_products(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_any_role)],
    category: str | None = None,
    is_perishable: bool | None = None,
):
    stmt = select(Product)
    if category:
        stmt = stmt.where(Product.category == category)
    if is_perishable is not None:
        stmt = stmt.where(Product.is_perishable == is_perishable)
    return list(db.scalars(stmt).all())


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_any_role)],
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product