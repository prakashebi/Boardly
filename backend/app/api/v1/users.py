import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, roles_required
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import UserRead, UserSelfUpdate, UserUpdate

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUser):
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(payload: UserSelfUpdate, current_user: CurrentUser, db: DbSession):
    """Members can update their own email, username, and password — not their role."""
    if payload.email is not None:
        current_user.email = payload.email
    if payload.username is not None:
        current_user.username = payload.username
    if payload.password is not None:
        current_user.hashed_password = hash_password(payload.password)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("", response_model=list[UserRead], dependencies=[Depends(roles_required(UserRole.admin))])
def list_users(db: DbSession):
    """Admin only — list all users."""
    return db.scalars(select(User).order_by(User.created_at)).all()


@router.get("/{user_id}", response_model=UserRead, dependencies=[Depends(roles_required(UserRole.admin))])
def get_user(user_id: uuid.UUID, db: DbSession):
    """Admin only — get any user by ID."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserRead, dependencies=[Depends(roles_required(UserRole.admin))])
def update_user(user_id: uuid.UUID, payload: UserUpdate, db: DbSession):
    """Admin only — update any user including role and active status."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.email is not None:
        user.email = payload.email
    if payload.username is not None:
        user.username = payload.username
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user
