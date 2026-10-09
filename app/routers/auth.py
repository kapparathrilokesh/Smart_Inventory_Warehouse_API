from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.auth.security import hash_password, verify_password
from app.database import get_db
from app.models.user import User, UserRole
from app.auth.dependencies import get_current_user
from app.auth.dependencies import require_roles

from app.schemas.auth import (
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    existing_username = db.query(User).filter(
        User.username == user_data.username
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=409,
            detail="Username already exists"
        )

    existing_email = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=409,
            detail="Email already exists"
        )

    # Public registration can only create Warehouse Staff
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=UserRole.WAREHOUSE_STAFF,
        warehouse_id=user_data.warehouse_id,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=TokenResponse
)
def login_user(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.username == login_data.username
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not verify_password(
        login_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="User account is inactive"
        )

    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role.value
    })

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get(
    "/me",
    response_model=UserResponse
)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user

@router.post(
    "/staff",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def create_staff(
    user_data: UserRegister,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    )
):
    if user_data.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin accounts cannot be created through this endpoint"
        )

    if user_data.role == UserRole.WAREHOUSE_STAFF and not user_data.warehouse_id:
        raise HTTPException(
            status_code=400,
            detail="Warehouse Staff must be assigned a warehouse"
        )

    if db.query(User).filter(
        User.username == user_data.username
    ).first():
        raise HTTPException(
            status_code=409,
            detail="Username already exists"
        )

    if db.query(User).filter(
        User.email == user_data.email
    ).first():
        raise HTTPException(
            status_code=409,
            detail="Email already exists"
        )

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
        warehouse_id=user_data.warehouse_id,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user