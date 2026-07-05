import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from werkzeug.utils import secure_filename

from app.api.deps import CurrentUser, DbSession, check_entity_permission, require_write_access
from app.core.config import get_settings
from app.models.entity import Entity
from app.schemas.entity import EntityRead

router = APIRouter(tags=["attachments"])

ALLOWED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "gif", "webp",
    "txt", "md", "csv",
    "doc", "docx", "xls", "xlsx",
    "zip", "tar", "gz",
}


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _entity_or_404(db: DbSession, entity_id: uuid.UUID) -> Entity:
    entity = db.scalar(select(Entity).where(Entity.id == entity_id, Entity.is_deleted.is_(False)))
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.post("/api/v1/entities/{entity_id}/attachments", response_model=EntityRead, status_code=201)
def upload_attachment(
    entity_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    require_write_access(current_user)

    entity = _entity_or_404(db, entity_id)
    check_entity_permission(entity, current_user, db)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")

    if not _allowed(file.filename):
        raise HTTPException(status_code=400, detail="File type not allowed")

    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_size_mb}MB limit")

    attachment_id = str(uuid.uuid4())
    safe_name = secure_filename(file.filename)
    stored_name = f"{attachment_id}_{safe_name}"

    entity_dir = Path(settings.upload_folder) / str(entity_id)
    entity_dir.mkdir(parents=True, exist_ok=True)
    with open(entity_dir / stored_name, "wb") as f:
        shutil.copyfileobj(file.file, f)

    metadata = dict(entity.metadata_ or {})
    attachments = list(metadata.get("attachments", []))
    attachments.append({
        "id": attachment_id,
        "name": safe_name,
        "size": size,
        "type": file.content_type or "application/octet-stream",
        "stored_name": stored_name,
        "uploaded_by": current_user.username,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })
    metadata["attachments"] = attachments
    entity.metadata_ = metadata
    db.commit()
    db.refresh(entity)

    return entity


@router.get("/api/v1/attachments/{entity_id}/{attachment_id}")
def download_attachment(entity_id: uuid.UUID, attachment_id: str, current_user: CurrentUser, db: DbSession):
    entity = _entity_or_404(db, entity_id)
    check_entity_permission(entity, current_user, db)

    metadata = entity.metadata_ or {}
    attachment = next((a for a in metadata.get("attachments", []) if a["id"] == attachment_id), None)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    settings = get_settings()
    file_path = Path(settings.upload_folder) / str(entity_id) / attachment["stored_name"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(file_path.resolve(), filename=attachment["name"])


@router.delete("/api/v1/entities/{entity_id}/attachments/{attachment_id}", response_model=EntityRead)
def delete_attachment(entity_id: uuid.UUID, attachment_id: str, current_user: CurrentUser, db: DbSession):
    require_write_access(current_user)

    entity = _entity_or_404(db, entity_id)
    check_entity_permission(entity, current_user, db)

    metadata = dict(entity.metadata_ or {})
    attachments = list(metadata.get("attachments", []))
    attachment = next((a for a in attachments if a["id"] == attachment_id), None)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    settings = get_settings()
    file_path = Path(settings.upload_folder) / str(entity_id) / attachment["stored_name"]
    if file_path.exists():
        file_path.unlink()

    metadata["attachments"] = [a for a in attachments if a["id"] != attachment_id]
    entity.metadata_ = metadata
    db.commit()
    db.refresh(entity)

    return entity
