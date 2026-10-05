# Testing Setup for Boardly Backend

## What Was Set Up

A complete pytest-based testing infrastructure for the Django REST API backend with focus on **integration tests**. This validates API contracts, permissions, and audit logging in a realistic environment.

## Files Created

```
backend/
├── pytest.ini                    # Pytest configuration
├── TESTING.md                    # This guide
├── requirements.txt              # Updated with test dependencies
└── tests/
    ├── __init__.py
    ├── README.md                 # Detailed testing guide
    ├── conftest.py               # Test fixtures and setup
    ├── test_auth.py              # Login/register tests
    ├── test_entities.py          # Entity CRUD tests
    ├── test_permissions.py       # RBAC and permission tests
    ├── test_memberships.py       # Member invite/role tests
    └── test_audit_events.py      # Event logging tests
```

## Quick Start

### 1. Install Test Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run All Tests

```bash
pytest
```

### 3. Run Tests with Coverage

```bash
pytest --cov=core --cov-report=html
# Open htmlcov/index.html in browser
```

### 4. Run Specific Test

```bash
pytest tests/test_auth.py::TestAuthentication::test_register_success -v
```

## Test Coverage

### Authentication (test_auth.py)
- ✅ User registration with validation
- ✅ Login with valid/invalid credentials
- ✅ Duplicate email handling
- ✅ Password strength validation

### Entities (test_entities.py)
- ✅ Create, read, update, delete operations
- ✅ List with pagination and filtering
- ✅ Permission checks on all operations
- ✅ Soft-delete verification

### Permissions (test_permissions.py)
- ✅ Admin can access/modify all entities
- ✅ Members can only access owned/shared entities
- ✅ Viewers have read-only access
- ✅ Editors can modify while viewers cannot

### Memberships (test_memberships.py)
- ✅ Invite members to entities
- ✅ Update member roles
- ✅ Remove members
- ✅ List entity members
- ✅ Duplicate membership prevention

### Audit Events (test_audit_events.py)
- ✅ Events logged on create/update/delete
- ✅ Event filtering by type/entity/actor
- ✅ Events are immutable (read-only)
- ✅ Admin-only access to event logs

## Test Fixtures

Reusable fixtures defined in `conftest.py`:

```python
# Users
- admin_user          # Admin role
- member_user         # Member role
- viewer_user         # Viewer role

# Clients
- api_client                  # Unauthenticated
- authenticated_api_client    # Authenticated as member
- admin_api_client            # Authenticated as admin

# Entities
- workspace           # Test workspace (owned by admin)
- board              # Test board (owned by admin)
- card               # Test card (owned by admin)
- board_membership   # Membership of member_user on board
```

## Example Test

```python
@pytest.mark.django_db
def test_create_entity(authenticated_api_client, member_user):
    """Test that authenticated users can create entities."""
    payload = {
        "entity_type": "workspace",
        "title": "My Workspace",
    }
    response = authenticated_api_client.post("/api/v1/entities", payload)
    
    assert response.status_code == 201
    assert response.data["title"] == "My Workspace"
    assert response.data["owner_id"] == str(member_user.id)
```

## Running Tests in CI/CD

Add to GitHub Actions workflow:

```yaml
- name: Run backend tests
  run: |
    cd backend
    pip install -r requirements.txt
    pytest --cov=core --cov-report=xml
```

## Key Patterns Used

### 1. Class-Based Tests
Tests organized by feature in test classes:
```python
class TestAuthentication:
    def test_register_success(self, api_client):
        ...
    
    def test_login_invalid(self, api_client):
        ...
```

### 2. DRF API Client
Uses Django REST Framework's test client:
```python
response = api_client.post("/api/v1/entities", payload, format="json")
```

### 3. JWT Bearer Tokens
Fixtures create tokens for authenticated clients:
```python
authenticated_api_client  # Auto-authenticated as member_user
```

### 4. Database Access
Use `@pytest.mark.django_db` decorator:
```python
@pytest.mark.django_db
class TestSomething:
    def test_query_database(self, db):
        user = User.objects.create(...)
```

## Next Steps

1. **Run tests locally** to verify setup: `pytest`
2. **Review coverage**: `pytest --cov=core --cov-report=html`
3. **Add more tests** for:
   - File upload/download endpoints
   - Search functionality (PostgreSQL FTS + OpenSearch)
   - Entity versioning (when implemented)
4. **Configure CI/CD** to run tests on every PR (GitHub Actions, etc.)

## Debugging Failed Tests

### Verbose output
```bash
pytest -v
```

### Show print statements
```bash
pytest -s
```

### Stop on first failure
```bash
pytest -x
```

### Drop into debugger on failure
```bash
pytest --pdb
```

### Run specific test
```bash
pytest tests/test_auth.py::TestAuthentication::test_register_success
```

## Architecture

Tests follow Django + DRF best practices:
- **Integration tests focus** — Test API contracts, not implementation
- **Database per test** — Each test gets isolated database via pytest-django
- **Fixtures for setup** — Reusable test data reduces duplication
- **Clear naming** — Test names describe what they validate
- **Coverage tracking** — Monitor which code paths are tested

This approach catches real-world bugs (permission leaks, API contract breaks, audit logging failures) that unit tests might miss.
