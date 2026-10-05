# Boardly Backend Tests

This directory contains pytest-based integration tests for the Boardly backend API.

## Test Structure

Tests are organized by feature/endpoint:

- **test_auth.py** — Authentication endpoints (register, login)
- **test_entities.py** — Entity CRUD operations
- **test_permissions.py** — Role-based access control (RBAC) and permissions
- **test_memberships.py** — Member invitations and role management
- **test_audit_events.py** — Audit event logging and retrieval

## Running Tests

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure Django is configured (settings available in `config.settings`)

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_auth.py
```

### Run Specific Test Class

```bash
pytest tests/test_auth.py::TestAuthentication
```

### Run Specific Test

```bash
pytest tests/test_auth.py::TestAuthentication::test_register_success
```

### Run with Coverage Report

```bash
pytest --cov=core --cov-report=html
```

This generates an HTML report in `htmlcov/index.html`

### Run in Verbose Mode

```bash
pytest -v
```

### Run with Print Statements

```bash
pytest -s
```

## Test Patterns

### 1. Using Fixtures

Fixtures are defined in `conftest.py` and provide test data:

```python
def test_something(authenticated_api_client, member_user):
    """authenticated_api_client and member_user are fixtures."""
    response = authenticated_api_client.get("/api/v1/entities")
    assert response.status_code == 200
```

### 2. API Client Authentication

Three pre-configured clients are available:

- **api_client** — Unauthenticated client
- **authenticated_api_client** — Client authenticated as `member_user`
- **admin_api_client** — Client authenticated as `admin_user`

```python
def test_auth(authenticated_api_client):
    # This client has a valid Bearer token
    response = authenticated_api_client.get("/api/v1/entities")
```

### 3. Database Fixtures

Use `@pytest.mark.django_db` to enable database access:

```python
@pytest.mark.django_db
class TestSomething:
    def test_create_user(self, db):
        # db fixture gives access to database
        user = User.objects.create(...)
```

### 4. Test Entities

Use fixture entities in tests:

```python
def test_read_board(authenticated_api_client, board):
    # 'board' fixture creates a test board owned by admin
    response = authenticated_api_client.get(f"/api/v1/entities/{board.id}")
```

Available fixtures:
- `admin_user` — Admin with full permissions
- `member_user` — Regular member user
- `viewer_user` — Viewer-only user
- `workspace` — Test workspace
- `board` — Test board
- `card` — Test card
- `board_membership` — Membership of `member_user` on `board`

### 5. Assertion Patterns

```python
# Check status code
assert response.status_code == status.HTTP_201_CREATED

# Check response data
assert response.data["title"] == "Expected Title"

# Check database state
user = User.objects.get(email="test@example.com")
assert user.role == "admin"

# Check error handling
assert response.status_code == status.HTTP_400_BAD_REQUEST
assert "error" in response.data
```

## Best Practices

1. **Use fixtures for setup** — Don't repeat user/entity creation
2. **Test both success and failure** — Include tests for edge cases and errors
3. **Clear audit events** — When testing audit events, clear pre-existing events:
   ```python
   AuditEvent.objects.all().delete()
   ```
4. **Use descriptive names** — Test names should explain what they test
5. **One assertion per test** — Tests are clearer when focused on one behavior
6. **Test permissions** — Every API endpoint should have permission tests
7. **Test audit logging** — Verify events are created on mutations

## Debugging Tests

### Print Debug Info

```python
def test_something(authenticated_api_client):
    response = authenticated_api_client.get("/api/v1/entities")
    print(response.data)  # Run with: pytest -s
```

### Use pytest breakpoint

```python
def test_something(authenticated_api_client):
    response = authenticated_api_client.get("/api/v1/entities")
    breakpoint()  # Execution pauses here (use 'c' to continue)
```

### Check Database State

```python
from core.models import Entity

def test_create_entity(authenticated_api_client):
    response = authenticated_api_client.post("/api/v1/entities", {...})
    
    # Query database to verify
    entity = Entity.objects.get(id=response.data["id"])
    assert entity.title == "Expected"
```

## Continuous Integration

Tests should be run in CI/CD before merging. Example GitHub Actions setup:

```yaml
- name: Run tests
  run: |
    cd backend
    pip install -r requirements.txt
    pytest --cov=core
```

See `../../.github/workflows/` for CI configuration.
