import pytest
from rest_framework import status
from core.models import Entity, EntityStatus


@pytest.mark.django_db
class TestEntityOperations:
    """Test entity CRUD endpoints."""

    def test_create_entity_authenticated(self, authenticated_api_client, member_user):
        """Test creating an entity as authenticated user."""
        payload = {
            "entity_type": "workspace",
            "title": "My Workspace",
            "description": "A test workspace",
            "status": EntityStatus.ACTIVE,
        }
        response = authenticated_api_client.post("/api/v1/entities", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "My Workspace"
        assert response.data["entity_type"] == "workspace"
        assert response.data["owner_id"] == str(member_user.id)

    def test_create_entity_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot create entities."""
        payload = {
            "entity_type": "workspace",
            "title": "My Workspace",
        }
        response = api_client.post("/api/v1/entities", payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_read_entity(self, authenticated_api_client, member_user):
        """Test reading an entity you own."""
        entity = Entity.objects.create(
            entity_type="board",
            title="My Board",
            owner_id=member_user.id,
            status=EntityStatus.ACTIVE,
        )
        response = authenticated_api_client.get(f"/api/v1/entities/{entity.id}")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(entity.id)
        assert response.data["title"] == entity.title

    def test_read_entity_not_found(self, authenticated_api_client):
        """Test reading non-existent entity."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = authenticated_api_client.get(f"/api/v1/entities/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_read_entity_no_permission(self, authenticated_api_client, db, admin_user):
        """Test that users cannot read entities they're not a member of."""
        # Create an entity owned by admin that member has no access to
        private_entity = Entity.objects.create(
            entity_type="workspace",
            title="Private Workspace",
            owner_id=admin_user.id,
            status=EntityStatus.ACTIVE,
        )

        response = authenticated_api_client.get(f"/api/v1/entities/{private_entity.id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_entity_as_owner(self, authenticated_api_client, member_user):
        """Test updating an entity you own."""
        entity = Entity.objects.create(
            entity_type="workspace",
            title="Original Title",
            owner_id=member_user.id,
            status=EntityStatus.ACTIVE,
        )

        payload = {
            "title": "Updated Title",
            "description": "New description",
        }
        response = authenticated_api_client.patch(
            f"/api/v1/entities/{entity.id}", payload, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Updated Title"
        assert response.data["description"] == "New description"

    def test_update_entity_status(self, authenticated_api_client, member_user):
        """Test updating entity status."""
        entity = Entity.objects.create(
            entity_type="card",
            title="Test Card",
            owner_id=member_user.id,
            status=EntityStatus.ACTIVE,
        )

        payload = {"status": EntityStatus.COMPLETED}
        response = authenticated_api_client.patch(
            f"/api/v1/entities/{entity.id}", payload, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == EntityStatus.COMPLETED

    def test_delete_entity_as_owner(self, authenticated_api_client, member_user):
        """Test soft-delete of entity you own."""
        entity = Entity.objects.create(
            entity_type="workspace",
            title="To Delete",
            owner_id=member_user.id,
            status=EntityStatus.ACTIVE,
        )

        response = authenticated_api_client.delete(f"/api/v1/entities/{entity.id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify entity is soft-deleted (is_deleted=True)
        entity.refresh_from_db()
        assert entity.is_deleted is True

    def test_list_entities_pagination(self, authenticated_api_client, member_user):
        """Test listing entities with pagination."""
        # Create 5 entities
        for i in range(5):
            Entity.objects.create(
                entity_type="workspace",
                title=f"Workspace {i}",
                owner_id=member_user.id,
                status=EntityStatus.ACTIVE,
            )

        response = authenticated_api_client.get("/api/v1/entities?skip=0&limit=3")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total"] == 5
        assert len(response.data["items"]) == 3

    def test_list_entities_filter_by_type(self, authenticated_api_client, member_user):
        """Test filtering entities by type."""
        Entity.objects.create(
            entity_type="workspace",
            title="A Workspace",
            owner_id=member_user.id,
        )
        Entity.objects.create(
            entity_type="board",
            title="A Board",
            owner_id=member_user.id,
        )

        response = authenticated_api_client.get("/api/v1/entities?entity_type=board")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total"] == 1
        assert response.data["items"][0]["entity_type"] == "board"
