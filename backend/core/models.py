import uuid
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"
    VIEWER = "viewer", "Viewer"


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True, max_length=255)
    username = models.CharField(unique=True, db_index=True, max_length=100)
    hashed_password = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.MEMBER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email

    @property
    def is_authenticated(self):
        return True


class EntityStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    ARCHIVED = "archived", "Archived"


class Entity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=EntityStatus.choices,
        default=EntityStatus.ACTIVE,
        db_index=True
    )
    metadata = models.JSONField(default=dict, null=True, blank=True)
    owner_id = models.UUIDField(null=True, blank=True, db_index=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "entities"

    def __str__(self):
        return self.title


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100, db_index=True)
    actor_id = models.UUIDField(null=True, blank=True, db_index=True)
    entity_id = models.UUIDField(null=True, blank=True, db_index=True)
    entity_type = models.CharField(max_length=100, null=True, blank=True)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_events"


class MemberRole(models.TextChoices):
    EDITOR = "editor", "Editor"
    VIEWER = "viewer", "Viewer"


class Membership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    role = models.CharField(max_length=20, choices=MemberRole.choices, default=MemberRole.VIEWER)
    invited_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "memberships"
        unique_together = ("entity_id", "user_id")
