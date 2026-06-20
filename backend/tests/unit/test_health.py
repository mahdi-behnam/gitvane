from typing import Any, AsyncGenerator

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.main import app


def test_health_check_success() -> None:
    """Tests that the health check endpoint returns 200 and connected status when DB works"""

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
        assert response.json() == {"status": "healthy", "database": "connected"}
    finally:
        app.dependency_overrides.clear()


def test_health_check_failure() -> None:
    """Tests that the health check endpoint handles database exceptions gracefully"""

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
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
    finally:
        app.dependency_overrides.clear()
