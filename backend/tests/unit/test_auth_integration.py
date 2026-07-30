import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.db.models import User, UserRefreshToken, Repository
from app.main import app
from app.core.security_utils import create_access_token
from app.core.errors import GitOperationError

# A simple timezone-aware UTC datetime
UTC = timezone.utc


# Mock DB classes for different test scenarios

class InMemoryRefreshDb:
    def __init__(self, tokens: list[UserRefreshToken]) -> None:
        self.tokens = tokens
        self.added = []
        self.committed = False

    def add(self, obj: Any) -> None:
        self.added.append(obj)
        self.tokens.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def execute(self, statement: Any) -> Any:
        stmt_str = str(statement).lower()
        params = statement.compile().params

        if "select" in stmt_str:
            # Find the token value in parameters
            token_val = None
            for k, v in params.items():
                if "token" in k and isinstance(v, str):
                    token_val = v
                    break
            
            # Find token in our in-memory list
            matched_token = None
            if token_val:
                for t in self.tokens:
                    if t.token == token_val:
                        matched_token = t
                        break

            class MockResult:
                def scalars(self):
                    class MockScalars:
                        def first(self):
                            return matched_token
                        def all(self):
                            return [matched_token] if matched_token else []
                    return MockScalars()
            return MockResult()

        elif "update" in stmt_str:
            user_id = None
            for k, v in params.items():
                if "user_id" in k and isinstance(v, int):
                    user_id = v
                    break
            
            if user_id is not None:
                for t in self.tokens:
                    if t.user_id == user_id:
                        t.is_revoked = True

            class MockUpdateResult:
                pass
            return MockUpdateResult()

        class EmptyResult:
            def scalars(self):
                class EmptyScalars:
                    def first(self):
                        return None
                    def all(self):
                        return []
                return EmptyScalars()
        return EmptyResult()


class MultiTenancyDb:
    def __init__(self, users: list[User], repositories: list[Repository]) -> None:
        self.users = {u.id: u for u in users}
        self.repositories = repositories
        self.committed = False
        self.added = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def flush(self) -> None:
        pass

    async def execute(self, statement: Any) -> Any:
        stmt_str = str(statement).lower()
        params = statement.compile().params
        
        # User lookup
        if "from users" in stmt_str or "users.id =" in stmt_str:
            user_id = params.get("id_1")
            user = self.users.get(user_id)
            
            class MockResult:
                def scalars(self):
                    class MockScalars:
                        def first(self):
                            return user
                    return MockScalars()
            return MockResult()
            
        # Repository lookup
        elif "from repositories" in stmt_str or "repositories.id =" in stmt_str:
            repo_id = params.get("id_1")
            owner_id = params.get("owner_id_1")
            
            # Find matching repository
            matched_repo = None
            for r in self.repositories:
                if r.id == repo_id and r.owner_id == owner_id:
                    matched_repo = r
                    break
            
            class MockResult:
                def scalars(self):
                    class MockScalars:
                        def first(self):
                            return matched_repo
                        def all(self):
                            return [matched_repo] if matched_repo else []
                    return MockScalars()
            return MockResult()
            
        class EmptyResult:
            def scalars(self):
                class EmptyScalars:
                    def first(self):
                        return None
                    def all(self):
                        return []
                return EmptyScalars()
        return EmptyResult()


# 1. CSRF Validation Tests

def test_csrf_validation_endpoints() -> None:
    """Verify CSRF validation blocks requests with missing/mismatched tokens and allows matching tokens."""
    client = TestClient(app)

    # Missing header and cookie
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 403
    assert response.json()["error_type"] == "CSRFError"

    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 403
    assert response.json()["error_type"] == "CSRFError"

    # Cookie present, header missing
    client.cookies.set("csrf_token", "some_csrf_value")
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 403

    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 403

    # Header present, cookie missing
    client.cookies.clear()
    response = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "some_csrf_value"})
    assert response.status_code == 403

    response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "some_csrf_value"})
    assert response.status_code == 403

    # Present but not matching
    client.cookies.set("csrf_token", "csrf_cookie_val")
    response = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "csrf_header_different"})
    assert response.status_code == 403

    response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "csrf_header_different"})
    assert response.status_code == 403

    # Matching but refresh token invalid/missing (hits endpoint route handler)
    # Since refresh token is missing, the route handler returns 401 (AuthenticationError), not 403.
    # This proves CSRF validation succeeded and reached the endpoint.
    client.cookies.set("csrf_token", "matching_csrf")
    response = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "matching_csrf"})
    assert response.status_code == 401
    assert response.json()["error_type"] == "AuthenticationError"

    # For logout with matching CSRF, it should succeed (return 200) since no token is required to try logging out.
    client.cookies.set("csrf_token", "matching_csrf")
    response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "matching_csrf"})
    assert response.status_code == 200


# 2. Refresh Token Rotation (RTR) Tests

def test_rtr_active_token_rotation() -> None:
    """Verify that using an active refresh token rotates it and generates a new access token."""
    user_id = 42
    old_token_val = "active_refresh_token"
    expires_at = datetime.now(UTC) + timedelta(days=7)
    old_token = UserRefreshToken(
        user_id=user_id,
        token=old_token_val,
        expires_at=expires_at,
        is_revoked=False
    )

    db = InMemoryRefreshDb([old_token])

    async def override_get_db() -> AsyncGenerator[Any, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        client.cookies.set("csrf_token", "matching_csrf")
        client.headers.update({"X-CSRF-Token": "matching_csrf"})
        client.cookies.set("refresh_token", old_token_val)

        response = client.post("/api/v1/auth/refresh")
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data

        # Verify old token was revoked
        assert old_token.is_revoked is True

        # Verify new refresh token was set in cookie and stored in DB
        new_cookie_token = response.cookies.get("refresh_token")
        assert new_cookie_token is not None
        assert new_cookie_token != old_token_val

        new_db_tokens = [t for t in db.tokens if t.token == new_cookie_token]
        assert len(new_db_tokens) == 1
        assert new_db_tokens[0].is_revoked is False
        assert new_db_tokens[0].user_id == user_id
        assert db.committed is True

    finally:
        app.dependency_overrides.clear()


def test_rtr_reuse_revoked_token_invalidates_all() -> None:
    """Verify that attempting to reuse a revoked token revokes all active tokens for that user."""
    user_id = 42
    
    # Revoked refresh token being reused
    reused_token_val = "reused_revoked_token"
    reused_token = UserRefreshToken(
        user_id=user_id,
        token=reused_token_val,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        is_revoked=True
    )
    
    # Active refresh tokens for the same user
    active_token_1 = UserRefreshToken(
        user_id=user_id,
        token="active_token_1",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        is_revoked=False
    )
    active_token_2 = UserRefreshToken(
        user_id=user_id,
        token="active_token_2",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        is_revoked=False
    )
    
    # Active refresh token for a different user (should NOT be invalidated)
    other_user_active_token = UserRefreshToken(
        user_id=999,
        token="other_active_token",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        is_revoked=False
    )

    db = InMemoryRefreshDb([reused_token, active_token_1, active_token_2, other_user_active_token])

    async def override_get_db() -> AsyncGenerator[Any, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        client.cookies.set("csrf_token", "matching_csrf")
        client.headers.update({"X-CSRF-Token": "matching_csrf"})
        client.cookies.set("refresh_token", reused_token_val)

        response = client.post("/api/v1/auth/refresh")
        
        # Verify attempt was rejected
        assert response.status_code == 401
        assert response.json()["error_type"] == "AuthenticationError"

        # Verify all user's active tokens are now revoked
        assert active_token_1.is_revoked is True
        assert active_token_2.is_revoked is True
        
        # Verify other user's active token is NOT revoked
        assert other_user_active_token.is_revoked is False
        assert db.committed is True

    finally:
        app.dependency_overrides.clear()


from uuid import UUID

TEST_UUID = UUID("11111111-1111-1111-1111-111111111111")


# 3. Database Multi-Tenancy Isolation Tests

def test_database_multi_tenancy_isolation() -> None:
    """Verify that User B cannot access or index User A's repository."""
    user_a = User(
        id=1,
        email="usera@example.com",
        full_name="User A",
        hashed_password="hashed_password",
        is_active=True
    )
    user_b = User(
        id=2,
        email="userb@example.com",
        full_name="User B",
        hashed_password="hashed_password",
        is_active=True
    )
    
    repo_a = Repository(
        id=TEST_UUID,
        name="usera-repo",
        clone_url="https://github.com/usera/repo.git",
        status="ready",
        owner_id=1
    )

    db = MultiTenancyDb([user_a, user_b], [repo_a])

    async def override_get_db() -> AsyncGenerator[Any, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        # Generate Bearer token for User B
        user_b_token = create_access_token(subject=2)
        
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {user_b_token}"})

        # GET /api/v1/repositories/{TEST_UUID}
        response = client.get(f"/api/v1/repositories/{TEST_UUID}")
        assert response.status_code == 404

        # DELETE /api/v1/repositories/{TEST_UUID}
        response = client.delete(f"/api/v1/repositories/{TEST_UUID}")
        assert response.status_code == 404

        # POST /api/v1/repositories/{TEST_UUID}/index
        response = client.post(f"/api/v1/repositories/{TEST_UUID}/index", json={"ref": "main"})
        assert response.status_code == 404
        
    finally:
        app.dependency_overrides.clear()


# 4. PAT Encryption & Sanitization Tests

def test_git_service_pat_sanitization_on_failure() -> None:
    """Verify direct GitService functions scrub the PAT on failure."""
    from app.services.git_service import GitService
    import git

    git_service = GitService()
    pat = "secret_pat_12345"
    clone_url = "https://github.com/example/repo.git"

    # Mock git.cmd.Git to raise GitCommandError
    mock_git_cmd = MagicMock()
    error_stderr = f"fatal: Repository not found at 'https://{pat}@github.com/example/repo.git/'"
    mock_git_cmd.ls_remote.side_effect = git.exc.GitCommandError(
        command=["git", "ls-remote"],
        status=128,
        stderr=error_stderr
    )

    with patch("git.cmd.Git", return_value=mock_git_cmd):
        with pytest.raises(Exception) as exc_info:
            git_service.verify_public_accessibility(clone_url, pat=pat)
        
        err_msg = str(exc_info.value)
        assert pat not in err_msg
        assert "****" in err_msg
        assert f"https://{pat}@" not in err_msg
        assert "https://****@" in err_msg

    with patch("git.Repo.clone_from") as mock_clone:
        error_stderr = f"fatal: repository 'https://{pat}@github.com/example/repo.git/' not found"
        mock_clone.side_effect = git.exc.GitCommandError(
            command=["git", "clone"],
            status=128,
            stderr=error_stderr
        )
        
        with pytest.raises(GitOperationError) as exc_info:
            git_service.clone_repository(clone_url, "/tmp/some-path", pat=pat)
            
        err_msg = str(exc_info.value)
        assert pat not in err_msg
        assert "****" in err_msg


def test_api_pat_sanitization_on_clone_failure() -> None:
    """Verify that cloning failure exceptions/errors returned to the client are fully scrubbed."""
    import git
    user = User(
        id=1,
        email="user@example.com",
        full_name="User",
        hashed_password="hashed_password",
        is_active=True
    )
    
    class SimpleUserDb:
        def __init__(self, user: User) -> None:
            self.user = user
        async def execute(self, statement: Any) -> Any:
            class MockResult:
                def scalars(self):
                    class MockScalars:
                        def first(self):
                            return user
                    return MockScalars()
            return MockResult()
        def add(self, obj: Any) -> None:
            obj.id = 100
        async def flush(self) -> None:
            pass
        async def rollback(self) -> None:
            pass

    db = SimpleUserDb(user)
    app.dependency_overrides[get_db] = lambda: db
    
    pat = "super_secret_pat_999"
    clone_url = "https://github.com/example/repo.git"
    
    mock_git_cmd = MagicMock()
    error_stderr = f"fatal: Repository not found at 'https://{pat}@github.com/example/repo.git/'"
    mock_git_cmd.ls_remote.side_effect = git.exc.GitCommandError(
        command=["git", "ls-remote"],
        status=128,
        stderr=error_stderr
    )

    try:
        user_token = create_access_token(subject=1)
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {user_token}"})
        
        with patch("git.cmd.Git", return_value=mock_git_cmd):
            response = client.post(
                "/api/v1/repositories",
                json={
                    "name": "failed-repo",
                    "clone_url": clone_url,
                    "pat": pat
                }
            )
            
            assert response.status_code in (400, 422)
            response_detail = response.json()["detail"]
            assert pat not in response_detail
            assert "****" in response_detail
    finally:
        app.dependency_overrides.clear()
