import uuid
import pytest
from rest_framework.test import APIClient

from core.models import User, Entity, EntityStatus, Membership, MemberRole
from core.security import create_access_token, hash_password


@pytest.fixture
def api_client():
    """DRF API client for making requests."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create a test admin user."""
    return User.objects.create(
        email="admin@test.com",
        username="admin",
        hashed_password=hash_password("TestPassword123!"),
        role="admin"
    )


@pytest.fixture
def member_user(db):
    """Create a test member user."""
    return User.objects.create(
        email="member@test.com",
        username="member",
        hashed_password=hash_password("TestPassword123!"),
        role="member"
    )


@pytest.fixture
def viewer_user(db):
    """Create a test viewer user."""
    return User.objects.create(
        email="viewer@test.com",
        username="viewer",
        hashed_password=hash_password("TestPassword123!"),
        role="viewer"
    )


@pytest.fixture
def authenticated_api_client(api_client, member_user):
    """API client authenticated as member user."""
    token = create_access_token(str(member_user.id))
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    api_client.user = member_user
    return api_client


@pytest.fixture
def admin_api_client(api_client, admin_user):
    """API client authenticated as admin user."""
    token = create_access_token(str(admin_user.id))
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    api_client.user = admin_user
    return api_client


@pytest.fixture
def workspace(db, admin_user):
    """Create a test workspace."""
    return Entity.objects.create(
        id=uuid.uuid4(),
        entity_type="workspace",
        title="Test Workspace",
        description="A test workspace",
        owner_id=admin_user.id,
        status=EntityStatus.ACTIVE,
    )


@pytest.fixture
def board(db, admin_user, workspace):
    """Create a test board."""
    return Entity.objects.create(
        id=uuid.uuid4(),
        entity_type="board",
        title="Test Board",
        description="A test board",
        owner_id=admin_user.id,
        status=EntityStatus.ACTIVE,
        metadata={"workspace_id": str(workspace.id)},
    )


@pytest.fixture
def card(db, admin_user, board):
    """Create a test card."""
    return Entity.objects.create(
        id=uuid.uuid4(),
        entity_type="card",
        title="Test Card",
        description="A test card",
        owner_id=admin_user.id,
        status=EntityStatus.ACTIVE,
        metadata={"board_id": str(board.id)},
    )


@pytest.fixture
def board_membership(db, board, member_user):
    """Create a membership for a member on a board."""
    return Membership.objects.create(
        id=uuid.uuid4(),
        entity_id=board.id,
        user_id=member_user.id,
        role=MemberRole.EDITOR,
    )
