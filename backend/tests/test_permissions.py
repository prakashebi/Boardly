import pytest
from rest_framework import status
from core.models import Entity, EntityStatus, Membership, MemberRole


@pytest.mark.django_db
class TestPermissions:
    """Test role-based access control and permissions."""

    def test_admin_can_view_all_entities(self, admin_api_client, member_user):
        """Test that admins can view all entities."""
        entity = Entity.objects.create(
            entity_type="workspace",
            title="Private Workspace",
            owner_id=member_user.id,
            status=EntityStatus.ACTIVE,
        )

        response = admin_api_client.get(f"/api/v1/entities/{entity.id}")

        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_update_any_entity(self, admin_api_client, member_user):
        """Test that admins can update any entity."""
        entity = Entity.objects.create(
            entity_type="workspace",
            title="Original",
            owner_id=member_user.id,
            status=EntityStatus.ACTIVE,
        )

        payload = {"title": "Admin Updated"}
        response = admin_api_client.patch(
            f"/api/v1/entities/{entity.id}", payload, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Admin Updated"

    def test_member_can_view_owned_entity(self, authenticated_api_client, member_user):
        """Test that members can view entities they own."""
        entity = Entity.objects.create(
            entity_type="board",
            title="My Board",
            owner_id=member_user.id,
            status=EntityStatus.ACTIVE,
        )

        response = authenticated_api_client.get(f"/api/v1/entities/{entity.id}")

        assert response.status_code == status.HTTP_200_OK

    def test_member_cannot_view_unrelated_entity(self, authenticated_api_client, admin_user):
        """Test that members cannot view entities they're not part of."""
        entity = Entity.objects.create(
            entity_type="board",
            title="Admin Board",
            owner_id=admin_user.id,
            status=EntityStatus.ACTIVE,
        )

        response = authenticated_api_client.get(f"/api/v1/entities/{entity.id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_member_with_membership_can_view_entity(self, authenticated_api_client, member_user, admin_user):
        """Test that members can view entities they're members of."""
        entity = Entity.objects.create(
            entity_type="board",
            title="Shared Board",
            owner_id=admin_user.id,
            status=EntityStatus.ACTIVE,
        )

        # Add member to entity
        Membership.objects.create(
            entity_id=entity.id,
            user_id=member_user.id,
            role=MemberRole.VIEWER,
        )

        response = authenticated_api_client.get(f"/api/v1/entities/{entity.id}")

        assert response.status_code == status.HTTP_200_OK

    def test_viewer_cannot_edit_entity(self, api_client, viewer_user, admin_user):
        """Test that viewers can read but not write."""
        entity = Entity.objects.create(
            entity_type="board",
            title="Board",
            owner_id=admin_user.id,
            status=EntityStatus.ACTIVE,
        )

        # Add viewer to entity
        Membership.objects.create(
            entity_id=entity.id,
            user_id=viewer_user.id,
            role=MemberRole.VIEWER,
        )

        # Authenticate as viewer
        from core.security import create_access_token
        token = create_access_token(str(viewer_user.id))
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Viewer should be able to read
        response = api_client.get(f"/api/v1/entities/{entity.id}")
        assert response.status_code == status.HTTP_200_OK

        # Viewer should NOT be able to edit
        payload = {"title": "Edited"}
        response = api_client.patch(
            f"/api/v1/entities/{entity.id}", payload, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_editor_can_edit_entity(self, api_client, member_user, admin_user):
        """Test that editors can read and write."""
        entity = Entity.objects.create(
            entity_type="board",
            title="Board",
            owner_id=admin_user.id,
            status=EntityStatus.ACTIVE,
        )

        # Add editor to entity
        Membership.objects.create(
            entity_id=entity.id,
            user_id=member_user.id,
            role=MemberRole.EDITOR,
        )

        # Authenticate as editor
        from core.security import create_access_token
        token = create_access_token(str(member_user.id))
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Editor should be able to edit
        payload = {"title": "Edited"}
        response = api_client.patch(
            f"/api/v1/entities/{entity.id}", payload, format="json"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_delete_any_entity(self, admin_api_client, member_user):
        """Test that admins can delete any entity."""
        entity = Entity.objects.create(
            entity_type="workspace",
            title="To Delete",
            owner_id=member_user.id,
            status=EntityStatus.ACTIVE,
        )

        response = admin_api_client.delete(f"/api/v1/entities/{entity.id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        entity.refresh_from_db()
        assert entity.is_deleted is True

    def test_member_cannot_delete_unowned_entity(self, authenticated_api_client, admin_user):
        """Test that members cannot delete entities they don't own."""
        entity = Entity.objects.create(
            entity_type="workspace",
            title="Admin Entity",
            owner_id=admin_user.id,
            status=EntityStatus.ACTIVE,
        )

        response = authenticated_api_client.delete(f"/api/v1/entities/{entity.id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN
