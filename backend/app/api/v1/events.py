import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.api.deps import DbSession, roles_required
from app.models.event import AuditEvent
from app.models.user import UserRole
from app.schemas.event import AuditEventListResponse, AuditEventRead

router = APIRouter(
    prefix="/api/v1/events",
    tags=["events"],
    dependencies=[Depends(roles_required(UserRole.admin, UserRole.member))],
)


@router.get("", response_model=AuditEventListResponse)
def list_events(
    db: DbSession,
    event_type: str | None = None,
    entity_id: str | None = None,
    actor_id: str | None = None,
    skip: int = 0,
    limit: int = 50,
):
    limit = min(limit, 200)

    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc())
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if entity_id:
        stmt = stmt.where(AuditEvent.entity_id == uuid.UUID(entity_id))
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == uuid.UUID(actor_id))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.offset(skip).limit(limit)).all()

    return AuditEventListResponse(total=total or 0, items=[AuditEventRead.model_validate(r) for r in rows])
