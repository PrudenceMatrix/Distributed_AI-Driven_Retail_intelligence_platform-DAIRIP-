from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Any


# ── Product Schemas ───────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    is_perishable: bool = False
    base_price: float = Field(..., gt=0)
    expiry_days: int | None = Field(None, gt=0)

    @field_validator("sku")
    @classmethod
    def sku_uppercase(cls, v: str) -> str:
        return v.strip().upper()


class ProductResponse(BaseModel):
    id: str
    name: str
    sku: str
    category: str
    is_perishable: bool
    base_price: float
    current_price: float
    expiry_days: int | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Inventory Schemas ─────────────────────────────────────────────────────────

class ReceiveStockRequest(BaseModel):
    product_id: str
    branch_id: str
    quantity: int = Field(..., gt=0)


class SellItemRequest(BaseModel):
    product_id: str
    branch_id: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    order_id: str


class StockAdjustRequest(BaseModel):
    product_id: str
    branch_id: str
    delta: int  # can be negative
    reason: str = Field(..., min_length=1, max_length=255)


class InventoryResponse(BaseModel):
    product_id: str
    branch_id: str
    available_quantity: int
    reserved_quantity: int
    current_price: float
    last_event_version: int
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Event Schemas ─────────────────────────────────────────────────────────────

class EventResponse(BaseModel):
    id: str
    aggregate_id: str
    aggregate_type: str
    event_type: str
    payload: dict[str, Any]
    version: int
    branch_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Auth Schemas ──────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str = Field(..., min_length=8)
    role: str = "cashier"
    branch_id: str | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    branch_id: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Generic Response ──────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    data: dict[str, Any] | None = None