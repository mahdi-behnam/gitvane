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
                json={"email": "new@example.com", "password": "SecureP@ssword123", "full_name": "New User"},
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
            json={"email": "existing@example.com", "password": "SecureP@ssword123", "full_name": "Existing User"},
        )
        assert response.status_code == 400
        assert response.json()["error_type"] == "RepoLensError"
    finally:
        app.dependency_overrides.clear()


def test_signup_password_complexity_failure() -> None:
    client = TestClient(app)
    invalid_passwords = [
        "short1!",        # < 8 chars
        "alllowercase1!", # No uppercase
        "ALLUPPERCASE1!", # No lowercase
        "NoDigitsHere!",  # No digit
        "NoSpecial1234",  # No special char
    ]
    for invalid_pw in invalid_passwords:
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "test@example.com", "password": invalid_pw, "full_name": "Test User"},
        )
        assert response.status_code == 422


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


def test_jwt_secret_key_validation_in_non_local_environment() -> None:
    import pytest
    from app.core.config import Settings

    with pytest.raises(ValueError, match="JWT_SECRET_KEY environment variable is required in non-local environments"):
        Settings(ENVIRONMENT="production", JWT_SECRET_KEY="")


def test_jwt_secret_key_generation_in_local_environment() -> None:
    from app.core.config import Settings

    s = Settings(ENVIRONMENT="local", JWT_SECRET_KEY="")
    assert s.JWT_SECRET_KEY != ""


def test_oauth2_callback_google_redirect_secure() -> None:
    mock_user = MagicMock(spec=User)
    mock_user.id = 42
    mock_user.email = "oauth@example.com"
    mock_user.full_name = "OAuth User"

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
        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {"access_token": "google_tok"}

        mock_profile_resp = MagicMock()
        mock_profile_resp.status_code = 200
        mock_profile_resp.json.return_value = {
            "email": "oauth@example.com",
            "sub": "google123",
            "name": "OAuth User",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_token_resp
        mock_client.get.return_value = mock_profile_resp

        with patch("httpx.AsyncClient") as mock_httpx_cls:
            mock_httpx_cls.return_value.__aenter__.return_value = mock_client
            client = TestClient(app, follow_redirects=False)
            client.cookies.set("oauth_state", "validstate")
            response = client.get("/api/v1/auth/oauth2/callback/google?code=validcode&state=validstate")

            assert response.status_code == 307
            location = response.headers["location"]
            from app.core.config import settings
            assert location.startswith(settings.FRONTEND_URL)
            assert "#access_token=" in location
            assert "?access_token=" not in location
    finally:
        app.dependency_overrides.clear()


def test_forgot_password_dev_simulation() -> None:
    mock_user = MagicMock(spec=User)
    mock_user.id = 42
    mock_user.email = "reset@example.com"

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
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "reset@example.com"},
        )
        assert response.status_code == 200
        assert "reset_url" in response.json()
        assert "dev mode" in response.json()["message"]
    finally:
        app.dependency_overrides.clear()


def test_reset_password_success() -> None:
    from app.core.security_utils import create_password_reset_token
    token = create_password_reset_token("reset@example.com")

    mock_user = MagicMock(spec=User)
    mock_user.id = 42
    mock_user.email = "reset@example.com"
    mock_user.hashed_password = "old_hashed_password"

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
                "/api/v1/auth/reset-password",
                json={"token": token, "new_password": "NewSecureP@ssword123"},
            )
            assert response.status_code == 200
            assert response.json() == {"status": "success", "message": "Password reset successfully"}
    finally:
        app.dependency_overrides.clear()


def test_reset_password_same_as_old_password_fails() -> None:
    from app.core.security_utils import create_password_reset_token
    token = create_password_reset_token("reset@example.com")

    mock_user = MagicMock(spec=User)
    mock_user.id = 42
    mock_user.email = "reset@example.com"
    mock_user.hashed_password = "old_hashed_password"

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
                "/api/v1/auth/reset-password",
                json={"token": token, "new_password": "OldSecureP@ssword123"},
            )
            assert response.status_code == 400
            assert response.json()["detail"] == "New password cannot be the same as your old password"
    finally:
        app.dependency_overrides.clear()


def test_update_me_success() -> None:
    mock_user = MagicMock(spec=User)
    mock_user.id = 42
    mock_user.email = "update@example.com"
    mock_user.full_name = "Original Name"
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
            response = client.put(
                "/api/v1/auth/me",
                json={"full_name": "Updated Name", "password": "NewSecureP@ssword123"},
            )
            assert response.status_code == 200
            assert response.json()["full_name"] == "Updated Name"
    finally:
        app.dependency_overrides.clear()

