from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.main import app


@patch("redis.asyncio.from_url")
def test_health_check_success(mock_redis_from_url: Any) -> None:
    """Health check endpoint returns 200 and connected status when DB and Redis work."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()
    mock_redis_from_url.return_value = mock_redis

    class MockAsyncSession:
        async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
            return None

        async def close(self) -> None:
            pass

    async def override_get_db() -> AsyncGenerator[Any, None]:
        yield MockAsyncSession()

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
        }
    finally:
        app.dependency_overrides.clear()


@patch("redis.asyncio.from_url")
def test_health_check_db_failure(mock_redis_from_url: Any) -> None:
    """Tests that the health check endpoint returns 503 on database exceptions."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()
    mock_redis_from_url.return_value = mock_redis

    class MockAsyncSessionError:
        async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
            raise Exception("DB Connection error")

        async def close(self) -> None:
            pass

    async def override_get_db_error() -> AsyncGenerator[Any, None]:
        yield MockAsyncSessionError()

    app.dependency_overrides[get_db] = override_get_db_error
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert data["redis"] == "connected"
    finally:
        app.dependency_overrides.clear()


@patch("redis.asyncio.from_url")
def test_health_check_redis_failure(mock_redis_from_url: Any) -> None:
    """Tests that the health check endpoint returns 503 on redis connection exceptions."""
    mock_redis_from_url.side_effect = Exception("Redis Connection Error")

    class MockAsyncSession:
        async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
            return None

        async def close(self) -> None:
            pass

    async def override_get_db() -> AsyncGenerator[Any, None]:
        yield MockAsyncSession()

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "connected"
        assert data["redis"] == "disconnected"
    finally:
        app.dependency_overrides.clear()
