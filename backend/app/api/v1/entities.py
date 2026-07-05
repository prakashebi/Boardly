import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import and_, cast, func, or_, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.api.deps import CurrentUser, DbSession, check_entity_permission, require_write_access
from app.models.entity import Entity, EntityStatus
from app.models.event import AuditEvent
from app.models.membership import Membership
from app.models.user import UserRole
from app.schemas.entity import EntityCreate, EntityListResponse, EntityRead, EntityUpdate
from app.services.search import get_search_service

router = APIRouter(prefix="/api/v1/entities", tags=["entities"])


@router.get("", response_model=EntityListResponse)
def list_entities(
    current_user: CurrentUser,
    db: DbSession,
    entity_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 50,
):
    limit = min(limit, 200)

    stmt = select(Entity).where(Entity.is_deleted.is_(False))

    # Admins see all entities; others see entities they own or are members of,
    # plus columns/cards that belong to any board they can access.
    if current_user.role != UserRole.admin:
        member_entity_ids = select(Membership.entity_id).where(Membership.user_id == current_user.id)
        accessible_board_ids = (
            select(Entity.id)
            .where(
                Entity.entity_type == "board",
                Entity.is_deleted.is_(False),
                or_(Entity.owner_id == current_user.id, Entity.id.in_(member_entity_ids)),
            )
        )
        stmt = stmt.where(
            or_(
                Entity.owner_id == current_user.id,
                Entity.id.in_(member_entity_ids),
                and_(
                    Entity.entity_type.in_(["column", "card"]),
                    Entity.metadata_["board_id"].astext.isnot(None),
                    cast(Entity.metadata_["board_id"].astext, PG_UUID(as_uuid=True)).in_(accessible_board_ids),
                ),
            )
        )

    if entity_type:
        stmt = stmt.where(Entity.entity_type == entity_type)
    if status:
        stmt = stmt.where(Entity.status == EntityStatus(status))
    if q:
        results = get_search_service().search(
            q,
            entity_types=[entity_type] if entity_type else None,
            limit=200,
        )
        if not results:
            return EntityListResponse(total=0, items=[])
        matching_ids = [uuid.UUID(r.entity_id) for r in results]
        stmt = stmt.where(Entity.id.in_(matching_ids))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.offset(skip).limit(limit)).all()

    return EntityListResponse(total=total or 0, items=[EntityRead.model_validate(r) for r in rows])


@router.post("", response_model=EntityRead, status_code=201)
def create_entity(payload: EntityCreate, current_user: CurrentUser, db: DbSession):
    require_write_access(current_user)  # viewers cannot create

    entity = Entity(
        entity_type=payload.entity_type,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        metadata_=payload.metadata,
        owner_id=current_user.id,
    )
    db.add(entity)
    db.add(AuditEvent(
        event_type="entity.created",
        actor_id=current_user.id,
        entity_type=payload.entity_type,
        payload={"title": payload.title},
    ))
    db.commit()
    db.refresh(entity)

    get_search_service().index_entity(
        str(entity.id), entity.entity_type, entity.title, entity.description, entity.metadata_
    )

    return entity


@router.get("/{entity_id}", response_model=EntityRead)
def get_entity(entity_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    entity = db.scalar(select(Entity).where(Entity.id == entity_id, Entity.is_deleted.is_(False)))
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    check_entity_permission(entity, current_user, db)
    return entity


@router.patch("/{entity_id}", response_model=EntityRead)
def update_entity(entity_id: uuid.UUID, payload: EntityUpdate, current_user: CurrentUser, db: DbSession):
    require_write_access(current_user)

    entity = db.scalar(select(Entity).where(Entity.id == entity_id, Entity.is_deleted.is_(False)))
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    check_entity_permission(entity, current_user, db)

    updated_fields: dict = {}
    for field, value in payload.model_dump(exclude_none=True).items():
        if field == "metadata":
            entity.metadata_ = value
        else:
            setattr(entity, field, value)
        updated_fields[field] = value

    db.add(AuditEvent(
        event_type="entity.updated",
        actor_id=current_user.id,
        entity_id=entity.id,
        entity_type=entity.entity_type,
        payload=updated_fields,
    ))
    db.commit()
    db.refresh(entity)

    get_search_service().update_entity(
        str(entity.id), entity.title, entity.description, entity.metadata_
    )

    return entity


@router.delete("/{entity_id}", status_code=204)
def delete_entity(entity_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    require_write_access(current_user)

    entity = db.scalar(select(Entity).where(Entity.id == entity_id, Entity.is_deleted.is_(False)))
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    check_entity_permission(entity, current_user, db, require_owner_or_admin=True)

    entity.is_deleted = True
    db.add(AuditEvent(
        event_type="entity.deleted",
        actor_id=current_user.id,
        entity_id=entity.id,
        entity_type=entity.entity_type,
        payload={"title": entity.title},
    ))
    db.commit()

    get_search_service().delete_entity(str(entity.id))
