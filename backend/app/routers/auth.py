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
    require_admin,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    user = db.scalar(select(User).where(User.email == form_data.username))
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")

    token = create_access_token({"sub": user.id, "role": user.role.value})
    return TokenResponse(access_token=token)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    body: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    existing = db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid role: {body.role}")

    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=role,
        branch_id=body.branch_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user