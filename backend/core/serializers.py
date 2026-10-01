import re
from rest_framework import serializers
from core.models import User, Entity, AuditEvent, Membership, UserRole, EntityStatus, MemberRole


def validate_password_strength(value):
    errors = []
    if len(value) < 12:
        errors.append("at least 12 characters")
    if not re.search(r"[A-Z]", value):
        errors.append("an uppercase letter")
    if not re.search(r"[a-z]", value):
        errors.append("a lowercase letter")
    if not re.search(r"\d", value):
        errors.append("a number")
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>/?\\|`~]", value):
        errors.append("a special character")
    if errors:
        raise serializers.ValidationError("Password must contain " + ", ".join(errors))


def validate_username(value):
    if not value.replace("_", "").replace("-", "").isalnum():
        raise serializers.ValidationError("username may only contain letters, numbers, hyphens, and underscores")
    return value.lower()


class UserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(validators=[validate_username])
    password = serializers.CharField(validators=[validate_password_strength], write_only=True)

    def create(self, validated_data):
        from core.security import hash_password
        user = User.objects.create(
            email=validated_data["email"],
            username=validated_data["username"],
            hashed_password=hash_password(validated_data["password"]),
        )
        return user


class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "role", "is_active", "created_at"]


class UserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_null=True)
    username = serializers.CharField(required=False, allow_null=True, validators=[validate_username])
    role = serializers.ChoiceField(choices=UserRole.choices, required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, allow_null=True)


class UserSelfUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_null=True)
    username = serializers.CharField(required=False, allow_null=True, validators=[validate_username])
    password = serializers.CharField(required=False, allow_null=True, validators=[validate_password_strength], write_only=True)


class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TokenSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField()


class EntityCreateSerializer(serializers.Serializer):
    entity_type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=EntityStatus.choices, default=EntityStatus.ACTIVE)
    metadata = serializers.JSONField(required=False, allow_null=True)


class EntityReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = ["id", "entity_type", "title", "description", "status", "metadata", "owner_id", "created_at", "updated_at"]


class EntityUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=EntityStatus.choices, required=False, allow_null=True)
    metadata = serializers.JSONField(required=False, allow_null=True)


class EntityListResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    items = EntityReadSerializer(many=True)


class MemberInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=MemberRole.choices, default=MemberRole.VIEWER)


class MemberRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=MemberRole.choices)


class MemberReadSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    entity_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    username = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=MemberRole.choices)
    invited_by = serializers.UUIDField(allow_null=True)
    created_at = serializers.DateTimeField()


class AuditEventReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ["id", "event_type", "actor_id", "entity_id", "entity_type", "payload", "created_at"]


class AuditEventListResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    items = AuditEventReadSerializer(many=True)
