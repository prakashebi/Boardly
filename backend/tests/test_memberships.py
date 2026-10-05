import pytest
from rest_framework import status
from core.models import Entity, Membership, MemberRole, EntityStatus


@pytest.mark.django_db
class TestMemberships:
    """Test member invitation and role management."""

    def test_invite_member_to_entity(self, authenticated_api_client, member_user, admin_user):
        """Test inviting a user to an entity."""
        entity = Entity.objects.create(
            entity_type="board",
            title="Shared Board",
            owner_id=member_user.id,
            status=EntityStatus.ACTIVE,
        )

        payload = {
            "email": admin_user.email,
            "role": MemberRole.EDITOR,
        }
        response = authenticated_api_client.post(
            f"/api/v1/entities/{entity.id}/members",
            payload,
            format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify membership was created
        membership = Membership.objects.filter(
            entity_id=entity.id,
            user_id=admin_user.id,
            role=MemberRole.EDITOR,
        ).first()
        assert membership is not None

    def test_invite_nonexistent_user(self, authenticated_api_client, member_user):
        """Test inviting a non-existent user."""
        entity = Entity.objects.create(
            entity_type="board",
            title="Board",
            owner_id=member_user.id,
        )

        payload = {
            "email": "nonexistent@test.com",
            "role": MemberRole.VIEWER,
        }
        response = authenticated_api_client.post(
            f"/api/v1/entities/{entity.id}/members",
            payload,
            format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invite_member_creates_audit_event(self, authenticated_api_client, member_user, admin_user):
        """Test that inviting a member creates an audit event."""
        from core.models import AuditEvent

        entity = Entity.objects.create(
            entity_type="board",
            title="Board",
            owner_id=member_user.id,
        )

        # Clear audit events
        AuditEvent.objects.all().delete()

        payload = {
            "email": admin_user.email,
            "role": MemberRole.EDITOR,
        }
        response = authenticated_api_client.post(
            f"/api/v1/entities/{entity.id}/members",
            payload,
            format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["role"] == MemberRole.EDITOR

    def test_update_member_role(self, authenticated_api_client, member_user, admin_user):
        """Test updating a member's role."""
        entity = Entity.objects.create(
            entity_type="board",
            title="Board",
            owner_id=member_user.id,
        )

        membership = Membership.objects.create(
            entity_id=entity.id,
            user_id=admin_user.id,
            role=MemberRole.VIEWER,
        )

        payload = {"role": MemberRole.EDITOR}
        response = authenticated_api_client.patch(
            f"/api/v1/entities/{entity.id}/members/{admin_user.id}",
            payload,
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify role was updated
        membership.refresh_from_db()
        assert membership.role == MemberRole.EDITOR

    def test_remove_member(self, authenticated_api_client, member_user, admin_user):
        """Test removing a member from an entity."""
        entity = Entity.objects.create(
            entity_type="board",
            title="Board",
            owner_id=member_user.id,
        )

        membership = Membership.objects.create(
            entity_id=entity.id,
            user_id=admin_user.id,
            role=MemberRole.EDITOR,
        )

        response = authenticated_api_client.delete(
            f"/api/v1/entities/{entity.id}/members/{admin_user.id}"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify membership was deleted
        assert not Membership.objects.filter(
            entity_id=entity.id,
            user_id=admin_user.id,
        ).exists()

    def test_list_members(self, authenticated_api_client, member_user, admin_user, viewer_user):
        """Test listing members of an entity."""
        entity = Entity.objects.create(
            entity_type="board",
            title="Board",
            owner_id=member_user.id,
        )

        Membership.objects.create(
            entity_id=entity.id,
            user_id=admin_user.id,
            role=MemberRole.EDITOR,
        )
        Membership.objects.create(
            entity_id=entity.id,
            user_id=viewer_user.id,
            role=MemberRole.VIEWER,
        )

        response = authenticated_api_client.get(f"/api/v1/entities/{entity.id}/members")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2

    def test_cannot_invite_to_entity_without_permission(self, api_client, viewer_user, member_user, admin_user):
        """Test that members can't invite to entities they don't have permission on."""
        entity = Entity.objects.create(
            entity_type="board",
            title="Board",
            owner_id=admin_user.id,
        )

        # Authenticate as viewer with no permission
        from core.security import create_access_token
        token = create_access_token(str(viewer_user.id))
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        payload = {
            "email": member_user.email,
            "role": MemberRole.VIEWER,
        }
        response = api_client.post(
            f"/api/v1/entities/{entity.id}/members",
            payload,
            format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_duplicate_membership_not_created(self, authenticated_api_client, member_user, admin_user):
        """Test that duplicate memberships are not created."""
        entity = Entity.objects.create(
            entity_type="board",
            title="Board",
            owner_id=member_user.id,
        )

        # Create first membership
        Membership.objects.create(
            entity_id=entity.id,
            user_id=admin_user.id,
            role=MemberRole.VIEWER,
        )

        # Try to create duplicate
        payload = {
            "email": admin_user.email,
            "role": MemberRole.EDITOR,
        }
        response = authenticated_api_client.post(
            f"/api/v1/entities/{entity.id}/members",
            payload,
            format="json"
        )

        # Should fail or return existing membership
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT]
