import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas import TokenResponse, UserCreate, UserResponse
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    """Login with email + password. Returns JWT token."""
    user = db.scalar(select(User).where(User.email == form_data.username))
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="This account has been deactivated.")

    token = create_access_token({"sub": user.id, "role": user.role.value})
    return TokenResponse(access_token=token)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: UserCreate,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Self-registration — open to all. No token required.
    Any new staff member can create their own account.
    Role is validated against allowed values: admin, manager, cashier.
    """
    # Check duplicate email
    existing = db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    # Validate role
    try:
        role = UserRole(body.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role '{body.role}'. Must be one of: admin, manager, cashier"
        )

    # Validate password length
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")

    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=role,
        branch_id=body.branch_id or "branch-001",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Returns the currently logged-in user's profile."""
    return current_user
