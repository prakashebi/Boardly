import pytest
from rest_framework import status
from core.models import Entity, AuditEvent, EntityStatus


@pytest.mark.django_db
class TestAuditEvents:
    """Test audit event logging on entity mutations."""

    def test_audit_event_on_entity_create(self, authenticated_api_client, member_user):
        """Test that creating an entity generates an audit event."""
        payload = {
            "entity_type": "workspace",
            "title": "Test Workspace",
        }
        response = authenticated_api_client.post("/api/v1/entities", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED

        # Verify audit event was created
        entity_id = response.data["id"]
        event = AuditEvent.objects.filter(
            event_type="entity.created",
            actor_id=member_user.id,
        ).first()

        assert event is not None
        assert event.entity_type == "workspace"
        assert event.payload is not None

    def test_audit_event_on_entity_update(self, authenticated_api_client, member_user):
        """Test that updating an entity generates an audit event."""
        entity = Entity.objects.create(
            entity_type="board",
            title="Original Title",
            owner_id=member_user.id,
            status=EntityStatus.ACTIVE,
        )

        # Clear any creation events
        AuditEvent.objects.all().delete()

        payload = {"title": "Updated Title"}
        response = authenticated_api_client.patch(
            f"/api/v1/entities/{entity.id}", payload, format="json"
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify update event was created
        event = AuditEvent.objects.filter(
            event_type="entity.updated",
            entity_id=entity.id,
            actor_id=member_user.id,
        ).first()

        assert event is not None
        assert event.payload is not None

    def test_audit_event_on_entity_delete(self, authenticated_api_client, member_user):
        """Test that deleting an entity generates an audit event."""
        entity = Entity.objects.create(
            entity_type="workspace",
            title="To Delete",
            owner_id=member_user.id,
            status=EntityStatus.ACTIVE,
        )

        # Clear any creation events
        AuditEvent.objects.all().delete()

        response = authenticated_api_client.delete(f"/api/v1/entities/{entity.id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify delete event was created
        event = AuditEvent.objects.filter(
            event_type="entity.deleted",
            entity_id=entity.id,
            actor_id=member_user.id,
        ).first()

        assert event is not None

    def test_list_audit_events(self, admin_api_client, member_user):
        """Test listing audit events (admin only)."""
        entity = Entity.objects.create(
            entity_type="workspace",
            title="Test",
            owner_id=member_user.id,
        )

        response = admin_api_client.get("/api/v1/events")

        assert response.status_code == status.HTTP_200_OK
        assert "total" in response.data
        assert "items" in response.data
        assert isinstance(response.data["items"], list)

    def test_filter_events_by_type(self, admin_api_client, member_user):
        """Test filtering events by event type."""
        entity = Entity.objects.create(
            entity_type="workspace",
            title="Test",
            owner_id=member_user.id,
        )

        response = admin_api_client.get("/api/v1/events?event_type=entity_created")

        assert response.status_code == status.HTTP_200_OK
        # All returned events should be of type 'entity_created'
        for event in response.data["items"]:
            assert event["event_type"] == "entity_created"

    def test_filter_events_by_entity_id(self, admin_api_client, member_user):
        """Test filtering events by entity ID."""
        entity1 = Entity.objects.create(
            entity_type="workspace",
            title="Workspace 1",
            owner_id=member_user.id,
        )
        entity2 = Entity.objects.create(
            entity_type="workspace",
            title="Workspace 2",
            owner_id=member_user.id,
        )

        response = admin_api_client.get(f"/api/v1/events?entity_id={entity1.id}")

        assert response.status_code == status.HTTP_200_OK
        # All returned events should be for entity1
        for event in response.data["items"]:
            assert str(event["entity_id"]) == str(entity1.id)

    def test_filter_events_by_actor_id(self, admin_api_client, authenticated_api_client, member_user, admin_user):
        """Test filtering events by actor ID."""
        entity = Entity.objects.create(
            entity_type="workspace",
            title="Test",
            owner_id=member_user.id,
        )

        response = admin_api_client.get(f"/api/v1/events?actor_id={member_user.id}")

        assert response.status_code == status.HTTP_200_OK
        # All returned events should have member_user as actor
        for event in response.data["items"]:
            assert str(event["actor_id"]) == str(member_user.id)

    def test_audit_events_are_immutable(self, admin_api_client):
        """Test that audit events cannot be modified or deleted."""
        event = AuditEvent.objects.create(
            event_type="test_event",
            actor_id=None,
            entity_id=None,
        )

        # Try to update (should fail)
        response = admin_api_client.patch(
            f"/api/v1/events/{event.id}",
            {"event_type": "modified"},
            format="json"
        )
        assert response.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_404_NOT_FOUND]

        # Try to delete (should fail)
        response = admin_api_client.delete(f"/api/v1/events/{event.id}")
        assert response.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_404_NOT_FOUND]

    def test_authenticated_users_can_view_events(self, authenticated_api_client):
        """Test that authenticated users can view audit events."""
        response = authenticated_api_client.get("/api/v1/events")

        # Any authenticated user can view events
        assert response.status_code == status.HTTP_200_OK
