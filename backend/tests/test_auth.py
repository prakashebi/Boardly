import pytest
from rest_framework import status
from core.models import User


@pytest.mark.django_db
class TestAuthentication:
    """Test auth endpoints: register, login."""

    def test_register_success(self, api_client):
        """Test successful user registration."""
        payload = {
            "email": "newuser@test.com",
            "username": "newuser",
            "password": "ValidPass123!",
        }
        response = api_client.post("/api/v1/auth/register", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "newuser@test.com"
        assert response.data["username"] == "newuser"
        assert "id" in response.data

        # Verify user was created in database
        user = User.objects.get(email="newuser@test.com")
        assert user.username == "newuser"
        assert user.role == "member"  # Default role

    def test_register_invalid_password(self, api_client):
        """Test registration with weak password."""
        payload = {
            "email": "newuser@test.com",
            "username": "newuser",
            "password": "weak",  # Too short, missing requirements
        }
        response = api_client.post("/api/v1/auth/register", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in str(response.data).lower()

    def test_register_duplicate_email(self, api_client, member_user):
        """Test registration with already-registered email."""
        payload = {
            "email": member_user.email,
            "username": "different_user",
            "password": "ValidPass123!",
        }
        response = api_client.post("/api/v1/auth/register", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_success(self, api_client, member_user):
        """Test successful login."""
        payload = {
            "email": member_user.email,
            "password": "TestPassword123!",
        }
        response = api_client.post("/api/v1/auth/login", payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data
        assert response.data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, api_client, member_user):
        """Test login with wrong password."""
        payload = {
            "email": member_user.email,
            "password": "WrongPassword123!",
        }
        response = api_client.post("/api/v1/auth/login", payload, format="json")

        # API validates input format before checking credentials, returns 400
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent email."""
        payload = {
            "email": "doesnotexist@test.com",
            "password": "Password123!",
        }
        response = api_client.post("/api/v1/auth/login", payload, format="json")

        # API validates input format before checking credentials, returns 400
        assert response.status_code == status.HTTP_400_BAD_REQUEST
