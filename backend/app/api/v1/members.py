import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, check_entity_permission
from app.models.entity import Entity
from app.models.membership import MemberRole, Membership
from app.models.user import User
from app.schemas.membership import MemberInvite, MemberRead, MemberRoleUpdate

router = APIRouter(prefix="/api/v1/entities", tags=["members"])


@router.get("/{entity_id}/members", response_model=list[MemberRead])
def list_members(entity_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    entity = _get_entity_or_404(db, entity_id)
    check_entity_permission(entity, current_user, db)

    memberships = db.scalars(select(Membership).where(Membership.entity_id == entity.id)).all()
    return [MemberRead.from_membership(m) for m in memberships]


@router.post("/{entity_id}/members", response_model=MemberRead, status_code=201)
def invite_member(entity_id: uuid.UUID, payload: MemberInvite, current_user: CurrentUser, db: DbSession):
    entity = _get_entity_or_404(db, entity_id)
    # Only owner or admin can invite
    check_entity_permission(entity, current_user, db, require_owner_or_admin=True)

    target_user = db.scalar(select(User).where(User.email == payload.email))
    if not target_user:
        raise HTTPException(status_code=404, detail="No user found with that email address")

    if target_user.id == entity.owner_id:
        raise HTTPException(status_code=409, detail="Cannot invite the entity owner as a member")

    existing = db.scalar(
        select(Membership).where(
            Membership.entity_id == entity.id,
            Membership.user_id == target_user.id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member")

    membership = Membership(
        entity_id=entity.id,
        user_id=target_user.id,
        role=payload.role,
        invited_by=current_user.id,
    )
    db.add(membership)

    # When adding a member to a board, ensure they can also see the parent workspace
    if entity.entity_type == "board" and entity.metadata_:
        workspace_id_str = entity.metadata_.get("workspace_id")
        if workspace_id_str:
            try:
                workspace_id = uuid.UUID(workspace_id_str)
            except (ValueError, AttributeError):
                workspace_id = None
            if workspace_id:
                workspace = db.scalar(
                    select(Entity).where(Entity.id == workspace_id, Entity.is_deleted.is_(False))
                )
                if workspace and workspace.owner_id != target_user.id:
                    existing_ws = db.scalar(
                        select(Membership).where(
                            Membership.entity_id == workspace_id,
                            Membership.user_id == target_user.id,
                        )
                    )
                    if not existing_ws:
                        db.add(Membership(
                            entity_id=workspace_id,
                            user_id=target_user.id,
                            role=MemberRole.viewer,
                            invited_by=current_user.id,
                        ))

    db.commit()
    db.refresh(membership)
    return MemberRead.from_membership(membership)


@router.patch("/{entity_id}/members/{member_user_id}", response_model=MemberRead)
def update_member_role(
    entity_id: uuid.UUID,
    member_user_id: uuid.UUID,
    payload: MemberRoleUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    entity = _get_entity_or_404(db, entity_id)
    check_entity_permission(entity, current_user, db, require_owner_or_admin=True)

    membership = _get_membership_or_404(db, entity.id, member_user_id)
    membership.role = payload.role
    db.commit()
    db.refresh(membership)
    return MemberRead.from_membership(membership)


@router.delete("/{entity_id}/members/{member_user_id}", status_code=204)
def remove_member(entity_id: uuid.UUID, member_user_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    entity = _get_entity_or_404(db, entity_id)

    # Allow self-removal or owner/admin removal
    if current_user.id != member_user_id:
        check_entity_permission(entity, current_user, db, require_owner_or_admin=True)

    membership = _get_membership_or_404(db, entity.id, member_user_id)
    db.delete(membership)
    db.commit()


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_entity_or_404(db: DbSession, entity_id: uuid.UUID) -> Entity:
    entity = db.scalar(select(Entity).where(Entity.id == entity_id, Entity.is_deleted.is_(False)))
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


def _get_membership_or_404(db: DbSession, entity_id: uuid.UUID, user_id: uuid.UUID) -> Membership:
    membership = db.scalar(
        select(Membership).where(
            Membership.entity_id == entity_id,
            Membership.user_id == user_id,
        )
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found")
    return membership
