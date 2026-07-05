import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    """Resolve the bearer token to a User row, or raise 401."""
    user_id = decode_access_token(token, get_settings())
    user = db.get(User, uuid.UUID(user_id)) if user_id else None
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def roles_required(*roles: UserRole):
    """Dependency factory: enforce auth + active status + role membership."""
    def checker(current_user: CurrentUser) -> User:
        if not current_user.is_active:
            raise HTTPException(status_code=401, detail="User not found")
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return checker


def check_entity_permission(
    entity, current_user: User, db: Session, require_owner_or_admin: bool = False
) -> None:
    """Raise 403 if user has no access to the entity.

    Admins pass unconditionally. Owners always pass. Members pass unless
    require_owner_or_admin=True (used for invite/remove operations).
    For columns and cards, board-level membership is also accepted.
    """
    from app.models.entity import Entity  # avoid circular import
    from app.models.membership import Membership  # avoid circular import

    if current_user.role == UserRole.admin:
        return

    if entity.owner_id == current_user.id:
        return

    if require_owner_or_admin:
        raise HTTPException(status_code=403, detail="Only the entity owner or an admin can perform this action")

    membership = db.scalar(
        select(Membership).where(
            Membership.entity_id == entity.id,
            Membership.user_id == current_user.id,
        )
    )
    if membership:
        return

    # For columns and cards, also accept membership on the parent board
    if entity.entity_type in ("column", "card") and entity.metadata_:
        board_id_str = entity.metadata_.get("board_id")
        if board_id_str:
            try:
                board_id = uuid.UUID(board_id_str)
            except (ValueError, AttributeError):
                board_id = None
            if board_id:
                board = db.scalar(
                    select(Entity).where(Entity.id == board_id, Entity.is_deleted.is_(False))
                )
                if board:
                    if board.owner_id == current_user.id:
                        return
                    board_membership = db.scalar(
                        select(Membership).where(
                            Membership.entity_id == board_id,
                            Membership.user_id == current_user.id,
                        )
                    )
                    if board_membership:
                        return

    raise HTTPException(status_code=403, detail="Access denied: you are not a member of this entity")


def require_write_access(current_user: User) -> None:
    """Raise 403 if the user has viewer (read-only) role."""
    if current_user.role == UserRole.viewer:
        raise HTTPException(status_code=403, detail="Viewers have read-only access")
