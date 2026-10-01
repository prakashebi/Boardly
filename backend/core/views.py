import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from werkzeug.utils import secure_filename

from core.models import User, Entity, AuditEvent, Membership, UserRole, EntityStatus, MemberRole
from core.serializers import (
    UserCreateSerializer, UserReadSerializer, UserUpdateSerializer, UserSelfUpdateSerializer,
    LoginRequestSerializer, TokenSerializer,
    EntityCreateSerializer, EntityReadSerializer, EntityUpdateSerializer, EntityListResponseSerializer,
    MemberInviteSerializer, MemberRoleUpdateSerializer, MemberReadSerializer,
    AuditEventReadSerializer, AuditEventListResponseSerializer,
)
from core.security import create_access_token, hash_password, verify_password
from core.permissions import IsAuthenticated, IsActive, IsAdmin, CanWriteContent
from core.search import get_search_service


ALLOWED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "gif", "webp",
    "txt", "md", "csv",
    "doc", "docx", "xls", "xlsx",
    "zip", "tar", "gz",
}


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _check_entity_permission(entity, current_user, require_owner_or_admin=False):
    if current_user.role == UserRole.ADMIN:
        return

    if entity.owner_id == current_user.id:
        return

    if require_owner_or_admin:
        raise PermissionDenied("Only the entity owner or an admin can perform this action")

    membership = Membership.objects.filter(
        entity_id=entity.id,
        user_id=current_user.id,
    ).exists()
    if membership:
        return

    if entity.entity_type in ("column", "card") and entity.metadata:
        board_id_str = entity.metadata.get("board_id")
        if board_id_str:
            try:
                board_id = uuid.UUID(board_id_str)
            except (ValueError, TypeError, AttributeError):
                board_id = None
            if board_id:
                board = Entity.objects.filter(id=board_id, is_deleted=False).first()
                if board:
                    if board.owner_id == current_user.id:
                        return
                    board_membership = Membership.objects.filter(
                        entity_id=board_id,
                        user_id=current_user.id,
                    ).exists()
                    if board_membership:
                        return

    raise PermissionDenied("Access denied: you are not a member of this entity")


# ── Auth ─────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([])
def register(request):
    serializer = UserCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    if User.objects.filter(email=serializer.validated_data["email"]).exists():
        raise ValidationError("Email already registered")

    user = serializer.save()
    return Response(UserReadSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([])
def login(request):
    serializer = LoginRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = User.objects.filter(email=serializer.validated_data["email"]).first()
    if not user or not verify_password(serializer.validated_data["password"], user.hashed_password):
        raise ValidationError("Invalid credentials")
    if not user.is_active:
        raise PermissionDenied("Account is disabled")

    token = create_access_token(str(user.id))
    return Response(TokenSerializer({"access_token": token, "token_type": "bearer"}).data)


# ── Users ────────────────────────────────────────────────────────────────

@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, IsActive])
def user_me(request):
    if request.method == "GET":
        return Response(UserReadSerializer(request.user).data)

    serializer = UserSelfUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = request.user
    if serializer.validated_data.get("email"):
        user.email = serializer.validated_data["email"]
    if serializer.validated_data.get("username"):
        user.username = serializer.validated_data["username"]
    if serializer.validated_data.get("password"):
        user.hashed_password = hash_password(serializer.validated_data["password"])
    user.save()

    return Response(UserReadSerializer(user).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def user_list(request):
    if request.method == "GET":
        users = User.objects.all().order_by("created_at")
        return Response(UserReadSerializer(users, many=True).data)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, IsAdmin])
def user_detail(request, user_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise NotFound("User not found")

    if request.method == "GET":
        return Response(UserReadSerializer(user).data)

    serializer = UserUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    if serializer.validated_data.get("email"):
        user.email = serializer.validated_data["email"]
    if serializer.validated_data.get("username"):
        user.username = serializer.validated_data["username"]
    if serializer.validated_data.get("role"):
        user.role = serializer.validated_data["role"]
    if serializer.validated_data.get("is_active") is not None:
        user.is_active = serializer.validated_data["is_active"]
    user.save()

    return Response(UserReadSerializer(user).data)


# ── Entities ─────────────────────────────────────────────────────────────

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsActive])
def entity_list_create(request):
    if request.method == "GET":
        entity_type = request.query_params.get("entity_type")
        status_param = request.query_params.get("status")
        q = request.query_params.get("q")
        skip = int(request.query_params.get("skip", 0))
        limit = min(int(request.query_params.get("limit", 50)), 200)

        query = Entity.objects.filter(is_deleted=False)

        if request.user.role != UserRole.ADMIN:
            member_entity_ids = Membership.objects.filter(user_id=request.user.id).values_list("entity_id", flat=True)
            accessible_board_ids = Entity.objects.filter(
                entity_type="board",
                is_deleted=False,
            ).filter(
                Q(owner_id=request.user.id) | Q(id__in=member_entity_ids)
            ).values_list("id", flat=True)

            query = query.filter(
                Q(owner_id=request.user.id)
                | Q(id__in=member_entity_ids)
                | (
                    Q(entity_type__in=["column", "card"])
                    & Q(metadata__board_id__isnull=False)
                )
            )

        if entity_type:
            query = query.filter(entity_type=entity_type)

        if status_param:
            query = query.filter(status=status_param)

        if q:
            results = get_search_service().search(
                q,
                entity_types=[entity_type] if entity_type else None,
                limit=200,
            )
            if not results:
                return Response(EntityListResponseSerializer({"total": 0, "items": []}).data)
            matching_ids = [uuid.UUID(r.entity_id) for r in results]
            query = query.filter(id__in=matching_ids)

        total = query.count()
        rows = query[skip:skip+limit]

        items = EntityReadSerializer(rows, many=True).data
        return Response(EntityListResponseSerializer({"total": total, "items": items}).data)

    # POST
    if not request.user or request.user.role == UserRole.VIEWER:
        raise PermissionDenied("Viewers have read-only access")

    serializer = EntityCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    entity = Entity.objects.create(
        entity_type=serializer.validated_data["entity_type"],
        title=serializer.validated_data["title"],
        description=serializer.validated_data.get("description"),
        status=serializer.validated_data.get("status", EntityStatus.ACTIVE),
        metadata=serializer.validated_data.get("metadata"),
        owner_id=request.user.id,
    )

    AuditEvent.objects.create(
        event_type="entity.created",
        actor_id=request.user.id,
        entity_type=serializer.validated_data["entity_type"],
        payload={"title": serializer.validated_data["title"]},
    )

    get_search_service().index_entity(
        str(entity.id),
        entity.entity_type,
        entity.title,
        entity.description,
        entity.metadata,
    )

    return Response(EntityReadSerializer(entity).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsActive])
def entity_detail(request, entity_id):
    entity = Entity.objects.filter(id=entity_id, is_deleted=False).first()
    if not entity:
        raise NotFound("Entity not found")

    if request.method == "GET":
        _check_entity_permission(entity, request.user)
        return Response(EntityReadSerializer(entity).data)

    if not request.user or request.user.role == UserRole.VIEWER:
        raise PermissionDenied("Viewers have read-only access")

    _check_entity_permission(entity, request.user)

    if request.method == "PATCH":
        serializer = EntityUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_fields = {}
        if serializer.validated_data.get("title") is not None:
            entity.title = serializer.validated_data["title"]
            updated_fields["title"] = serializer.validated_data["title"]
        if serializer.validated_data.get("description") is not None:
            entity.description = serializer.validated_data["description"]
            updated_fields["description"] = serializer.validated_data["description"]
        if serializer.validated_data.get("status") is not None:
            entity.status = serializer.validated_data["status"]
            updated_fields["status"] = serializer.validated_data["status"]
        if serializer.validated_data.get("metadata") is not None:
            entity.metadata = serializer.validated_data["metadata"]
            updated_fields["metadata"] = serializer.validated_data["metadata"]

        entity.save()

        AuditEvent.objects.create(
            event_type="entity.updated",
            actor_id=request.user.id,
            entity_id=entity.id,
            entity_type=entity.entity_type,
            payload=updated_fields,
        )

        get_search_service().update_entity(
            str(entity.id),
            entity.title,
            entity.description,
            entity.metadata,
        )

        return Response(EntityReadSerializer(entity).data)

    # DELETE
    _check_entity_permission(entity, request.user, require_owner_or_admin=True)

    entity.is_deleted = True
    entity.save()

    AuditEvent.objects.create(
        event_type="entity.deleted",
        actor_id=request.user.id,
        entity_id=entity.id,
        entity_type=entity.entity_type,
        payload={"title": entity.title},
    )

    get_search_service().delete_entity(str(entity.id))

    return Response(status=status.HTTP_204_NO_CONTENT)


# ── Members ──────────────────────────────────────────────────────────────

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsActive])
def member_list_create(request, entity_id):
    entity = Entity.objects.filter(id=entity_id, is_deleted=False).first()
    if not entity:
        raise NotFound("Entity not found")

    if request.method == "GET":
        _check_entity_permission(entity, request.user)

        memberships = Membership.objects.filter(entity_id=entity.id).select_related()
        items = []
        for m in memberships:
            user = User.objects.filter(id=m.user_id).first()
            if user:
                items.append({
                    "id": m.id,
                    "entity_id": m.entity_id,
                    "user_id": m.user_id,
                    "username": user.username,
                    "email": user.email,
                    "role": m.role,
                    "invited_by": m.invited_by,
                    "created_at": m.created_at,
                })

        return Response(MemberReadSerializer(items, many=True).data)

    # POST
    _check_entity_permission(entity, request.user, require_owner_or_admin=True)

    serializer = MemberInviteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    target_user = User.objects.filter(email=serializer.validated_data["email"]).first()
    if not target_user:
        raise NotFound("No user found with that email address")

    if target_user.id == entity.owner_id:
        raise ValidationError("Cannot invite the entity owner as a member")

    existing = Membership.objects.filter(
        entity_id=entity.id,
        user_id=target_user.id,
    ).exists()
    if existing:
        raise ValidationError("User is already a member")

    membership = Membership.objects.create(
        entity_id=entity.id,
        user_id=target_user.id,
        role=serializer.validated_data.get("role", MemberRole.VIEWER),
        invited_by=request.user.id,
    )

    if entity.entity_type == "board" and entity.metadata:
        workspace_id_str = entity.metadata.get("workspace_id")
        if workspace_id_str:
            try:
                workspace_id = uuid.UUID(workspace_id_str)
            except (ValueError, TypeError, AttributeError):
                workspace_id = None
            if workspace_id:
                workspace = Entity.objects.filter(id=workspace_id, is_deleted=False).first()
                if workspace and workspace.owner_id != target_user.id:
                    existing_ws = Membership.objects.filter(
                        entity_id=workspace_id,
                        user_id=target_user.id,
                    ).exists()
                    if not existing_ws:
                        Membership.objects.create(
                            entity_id=workspace_id,
                            user_id=target_user.id,
                            role=MemberRole.VIEWER,
                            invited_by=request.user.id,
                        )

    member_data = {
        "id": membership.id,
        "entity_id": membership.entity_id,
        "user_id": membership.user_id,
        "username": target_user.username,
        "email": target_user.email,
        "role": membership.role,
        "invited_by": membership.invited_by,
        "created_at": membership.created_at,
    }
    return Response(MemberReadSerializer(member_data).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsActive])
def member_detail(request, entity_id, member_user_id):
    entity = Entity.objects.filter(id=entity_id, is_deleted=False).first()
    if not entity:
        raise NotFound("Entity not found")

    membership = Membership.objects.filter(
        entity_id=entity.id,
        user_id=member_user_id,
    ).first()
    if not membership:
        raise NotFound("Member not found")

    if request.method == "PATCH":
        _check_entity_permission(entity, request.user, require_owner_or_admin=True)

        serializer = MemberRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership.role = serializer.validated_data["role"]
        membership.save()

        user = User.objects.filter(id=membership.user_id).first()
        member_data = {
            "id": membership.id,
            "entity_id": membership.entity_id,
            "user_id": membership.user_id,
            "username": user.username if user else "",
            "email": user.email if user else "",
            "role": membership.role,
            "invited_by": membership.invited_by,
            "created_at": membership.created_at,
        }
        return Response(MemberReadSerializer(member_data).data)

    # DELETE
    if request.user.id != member_user_id:
        _check_entity_permission(entity, request.user, require_owner_or_admin=True)

    membership.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── Attachments ──────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsActive])
def upload_attachment(request, entity_id):
    if not request.user or request.user.role == UserRole.VIEWER:
        raise PermissionDenied("Viewers have read-only access")

    entity = Entity.objects.filter(id=entity_id, is_deleted=False).first()
    if not entity:
        raise NotFound("Entity not found")

    _check_entity_permission(entity, request.user)

    file = request.FILES.get("file")
    if not file:
        raise ValidationError("No file provided")

    if not file.name or not _allowed(file.name):
        raise ValidationError("File type not allowed")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > max_bytes:
        raise ValidationError(f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

    attachment_id = str(uuid.uuid4())
    safe_name = secure_filename(file.name)
    stored_name = f"{attachment_id}_{safe_name}"

    entity_dir = Path(settings.UPLOAD_FOLDER) / str(entity_id)
    entity_dir.mkdir(parents=True, exist_ok=True)
    with open(entity_dir / stored_name, "wb") as f:
        shutil.copyfileobj(file.file, f)

    metadata = dict(entity.metadata or {})
    attachments = list(metadata.get("attachments", []))
    attachments.append({
        "id": attachment_id,
        "name": safe_name,
        "size": size,
        "type": file.content_type or "application/octet-stream",
        "stored_name": stored_name,
        "uploaded_by": request.user.username,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })
    metadata["attachments"] = attachments
    entity.metadata = metadata
    entity.save()

    return Response(EntityReadSerializer(entity).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsActive])
def download_attachment(request, entity_id, attachment_id):
    entity = Entity.objects.filter(id=entity_id, is_deleted=False).first()
    if not entity:
        raise NotFound("Entity not found")

    _check_entity_permission(entity, request.user)

    metadata = entity.metadata or {}
    attachment = next((a for a in metadata.get("attachments", []) if a["id"] == attachment_id), None)
    if not attachment:
        raise NotFound("Attachment not found")

    file_path = Path(settings.UPLOAD_FOLDER) / str(entity_id) / attachment["stored_name"]
    if not file_path.exists():
        raise NotFound("File not found on server")

    return FileResponse(open(file_path, "rb"), as_attachment=True, filename=attachment["name"])


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsActive])
def delete_attachment(request, entity_id, attachment_id):
    if not request.user or request.user.role == UserRole.VIEWER:
        raise PermissionDenied("Viewers have read-only access")

    entity = Entity.objects.filter(id=entity_id, is_deleted=False).first()
    if not entity:
        raise NotFound("Entity not found")

    _check_entity_permission(entity, request.user)

    metadata = dict(entity.metadata or {})
    attachments = list(metadata.get("attachments", []))
    attachment = next((a for a in attachments if a["id"] == attachment_id), None)
    if not attachment:
        raise NotFound("Attachment not found")

    file_path = Path(settings.UPLOAD_FOLDER) / str(entity_id) / attachment["stored_name"]
    if file_path.exists():
        file_path.unlink()

    metadata["attachments"] = [a for a in attachments if a["id"] != attachment_id]
    entity.metadata = metadata
    entity.save()

    return Response(EntityReadSerializer(entity).data)


# ── Events ───────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsActive])
def list_events(request):
    if request.user.role not in [UserRole.ADMIN, UserRole.MEMBER]:
        raise PermissionDenied("You don't have permission to view events")

    event_type = request.query_params.get("event_type")
    entity_id = request.query_params.get("entity_id")
    actor_id = request.query_params.get("actor_id")
    skip = int(request.query_params.get("skip", 0))
    limit = min(int(request.query_params.get("limit", 50)), 200)

    query = AuditEvent.objects.all().order_by("-created_at")

    if event_type:
        query = query.filter(event_type=event_type)
    if entity_id:
        try:
            query = query.filter(entity_id=uuid.UUID(entity_id))
        except ValueError:
            pass
    if actor_id:
        try:
            query = query.filter(actor_id=uuid.UUID(actor_id))
        except ValueError:
            pass

    total = query.count()
    rows = query[skip:skip+limit]

    items = AuditEventReadSerializer(rows, many=True).data
    return Response(AuditEventListResponseSerializer({"total": total, "items": items}).data)
