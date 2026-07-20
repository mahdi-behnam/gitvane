from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.db.models import User, UserRefreshToken
from app.main import app

# A simple timezone-aware UTC datetime
UTC = timezone.utc


def _mock_db_with_add() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    return db


async def _noop_db() -> AsyncGenerator[Any, None]:
    db = _mock_db_with_add()
    yield db


def test_csrf_bootstrap_and_cookie() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    assert "csrf_token" in response.cookies


def test_signup_success() -> None:
    class MockExecuteResult:
        def scalars(self) -> Any:
            mock_scalar = MagicMock()
            mock_scalar.first.return_value = None
            return mock_scalar

    async def override_get_db() -> AsyncGenerator[Any, None]:
        db = _mock_db_with_add()
        db.execute.return_value = MockExecuteResult()
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.api.v1.endpoints.auth.hash_password", return_value="hashed_pw"):
            client = TestClient(app)
            response = client.post(
                "/api/v1/auth/signup",
                json={"email": "new@example.com", "password": "securepassword123", "full_name": "New User"},
            )
            assert response.status_code == 201
            assert "access_token" in response.json()
            assert "refresh_token" in response.cookies
            assert "repolens_logged_in" in response.cookies
    finally:
        app.dependency_overrides.clear()


def test_signup_duplicate_email() -> None:
    class MockExecuteResult:
        def scalars(self) -> Any:
            mock_scalar = MagicMock()
            mock_scalar.first.return_value = MagicMock(spec=User)
            return mock_scalar

    async def override_get_db() -> AsyncGenerator[Any, None]:
        db = _mock_db_with_add()
        db.execute.return_value = MockExecuteResult()
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "existing@example.com", "password": "securepassword123", "full_name": "Existing User"},
        )
        assert response.status_code == 400
        assert response.json()["error_type"] == "RepoLensError"
    finally:
        app.dependency_overrides.clear()


def test_login_success() -> None:
    mock_user = MagicMock(spec=User)
    mock_user.id = 42
    mock_user.email = "user@example.com"
    mock_user.hashed_password = "hashed_pw"
    mock_user.is_active = True

    class MockExecuteResult:
        def scalars(self) -> Any:
            mock_scalar = MagicMock()
            mock_scalar.first.return_value = mock_user
            return mock_scalar

    async def override_get_db() -> AsyncGenerator[Any, None]:
        db = _mock_db_with_add()
        db.execute.return_value = MockExecuteResult()
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.api.v1.endpoints.auth.verify_password", return_value=True):
            client = TestClient(app)
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "securepassword123"},
            )
            assert response.status_code == 200
            assert "access_token" in response.json()
            assert "refresh_token" in response.cookies
    finally:
        app.dependency_overrides.clear()


def test_login_invalid_password() -> None:
    mock_user = MagicMock(spec=User)
    mock_user.id = 42
    mock_user.email = "user@example.com"
    mock_user.hashed_password = "hashed_pw"
    mock_user.is_active = True

    class MockExecuteResult:
        def scalars(self) -> Any:
            mock_scalar = MagicMock()
            mock_scalar.first.return_value = mock_user
            return mock_scalar

    async def override_get_db() -> AsyncGenerator[Any, None]:
        db = _mock_db_with_add()
        db.execute.return_value = MockExecuteResult()
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.api.v1.endpoints.auth.verify_password", return_value=False):
            client = TestClient(app)
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "wrongpassword"},
            )
            assert response.status_code == 401
            assert response.json()["error_type"] == "AuthenticationError"
    finally:
        app.dependency_overrides.clear()


def test_refresh_token_rotation_success() -> None:
    mock_token = MagicMock(spec=UserRefreshToken)
    mock_token.user_id = 42
    mock_token.token = "old_refresh_token"
    mock_token.expires_at = datetime.now(UTC) + timedelta(days=1)
    mock_token.is_revoked = False

    class MockExecuteResult:
        def scalars(self) -> Any:
            mock_scalar = MagicMock()
            mock_scalar.first.return_value = mock_token
            return mock_scalar

    async def override_get_db() -> AsyncGenerator[Any, None]:
        db = _mock_db_with_add()
        db.execute.return_value = MockExecuteResult()
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        bootstrap_res = client.get("/api/v1/auth/csrf")
        csrf_token = bootstrap_res.cookies.get("csrf_token")
        
        client.cookies.set("refresh_token", "old_refresh_token")
        client.headers.update({"X-CSRF-Token": csrf_token})
        
        response = client.post("/api/v1/auth/refresh")
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.cookies.get("refresh_token") != "old_refresh_token"
    finally:
        app.dependency_overrides.clear()


def test_refresh_token_expired() -> None:
    mock_token = MagicMock(spec=UserRefreshToken)
    mock_token.user_id = 42
    mock_token.token = "expired_refresh_token"
    mock_token.expires_at = datetime.now(UTC) - timedelta(days=1)
    mock_token.is_revoked = False

    class MockExecuteResult:
        def scalars(self) -> Any:
            mock_scalar = MagicMock()
            mock_scalar.first.return_value = mock_token
            return mock_scalar

    async def override_get_db() -> AsyncGenerator[Any, None]:
        db = _mock_db_with_add()
        db.execute.return_value = MockExecuteResult()
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        bootstrap_res = client.get("/api/v1/auth/csrf")
        csrf_token = bootstrap_res.cookies.get("csrf_token")
        
        client.cookies.set("refresh_token", "expired_refresh_token")
        client.headers.update({"X-CSRF-Token": csrf_token})
        
        response = client.post("/api/v1/auth/refresh")
        assert response.status_code == 401
        assert response.json()["error_type"] == "AuthenticationError"
    finally:
        app.dependency_overrides.clear()


def test_logout() -> None:
    mock_token = MagicMock(spec=UserRefreshToken)
    mock_token.user_id = 42
    mock_token.token = "some_refresh_token"
    mock_token.is_revoked = False

    class MockExecuteResult:
        def scalars(self) -> Any:
            mock_scalar = MagicMock()
            mock_scalar.first.return_value = mock_token
            return mock_scalar

    async def override_get_db() -> AsyncGenerator[Any, None]:
        db = _mock_db_with_add()
        db.execute.return_value = MockExecuteResult()
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        bootstrap_res = client.get("/api/v1/auth/csrf")
        csrf_token = bootstrap_res.cookies.get("csrf_token")
        
        client.cookies.set("refresh_token", "some_refresh_token")
        client.cookies.set("repolens_logged_in", "true")
        client.headers.update({"X-CSRF-Token": csrf_token})
        
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.cookies.get("refresh_token") == "" or "refresh_token" not in response.cookies
        assert response.cookies.get("repolens_logged_in") == "" or "repolens_logged_in" not in response.cookies
    finally:
        app.dependency_overrides.clear()


def test_get_me_success() -> None:
    mock_user = MagicMock(spec=User)
    mock_user.id = 42
    mock_user.email = "me@example.com"
    mock_user.full_name = "Me"
    mock_user.is_active = True
    mock_user.oauth_provider = None
    mock_user.created_at = datetime.now(UTC)
    mock_user.updated_at = datetime.now(UTC)

    class MockExecuteResult:
        def scalars(self) -> Any:
            mock_scalar = MagicMock()
            mock_scalar.first.return_value = mock_user
            return mock_scalar

    async def override_get_db() -> AsyncGenerator[Any, None]:
        db = _mock_db_with_add()
        db.execute.return_value = MockExecuteResult()
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.api.deps.decode_access_token", return_value={"sub": "42"}):
            client = TestClient(app)
            client.headers.update({"Authorization": "Bearer some_access_token"})
            response = client.get("/api/v1/auth/me")
            assert response.status_code == 200
            assert response.json()["email"] == "me@example.com"
            assert response.json()["full_name"] == "Me"
    finally:
        app.dependency_overrides.clear()
