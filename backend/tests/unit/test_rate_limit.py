from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware

from app.core.errors import setup_error_handlers
from app.core.rate_limit import create_limiter, get_client_ip, get_rate_limit_key
from app.core.security_utils import create_access_token


class MockClient:
    def __init__(self, host: str):
        self.host = host


class MockRequest:
    def __init__(
        self,
        headers: dict[str, str] | None = None,
        client_host: str | None = None,
        user: object | None = None,
    ):
        self.headers = headers or {}
        self.client = MockClient(client_host) if client_host else None
        self.state = type("State", (), {})()
        if user:
            self.state.user = user


def test_get_client_ip_headers():
    # 1. X-Real-IP precedence
    req1 = MockRequest(headers={"X-Real-IP": "203.0.113.19", "X-Forwarded-For": "198.51.100.5"})
    assert get_client_ip(req1) == "203.0.113.19"

    # 2. X-Forwarded-For first IP
    req2 = MockRequest(headers={"X-Forwarded-For": "198.51.100.5, 10.0.0.1"})
    assert get_client_ip(req2) == "198.51.100.5"

    # 3. Direct client host
    req3 = MockRequest(client_host="192.168.1.50")
    assert get_client_ip(req3) == "192.168.1.50"

    # 4. Fallback default
    req4 = MockRequest()
    assert get_client_ip(req4) == "127.0.0.1"


def test_get_rate_limit_key_priority():
    # 1. request.state.user
    mock_user = type("User", (), {"id": 42})()
    req_user = MockRequest(user=mock_user, client_host="1.1.1.1")
    assert get_rate_limit_key(req_user) == "user:42"

    # 2. Authorization Bearer token
    token = create_access_token(subject=100)
    req_token = MockRequest(
        headers={"Authorization": f"Bearer {token}"},
        client_host="1.1.1.1",
    )
    assert get_rate_limit_key(req_token) == "user:100"

    # 3. API Key / MCP Client
    req_mcp = MockRequest(
        headers={"X-MCP-Client": "antigravity-mcp-v1"},
        client_host="1.1.1.1",
    )
    key = get_rate_limit_key(req_mcp)
    assert key.startswith("mcp:")

    # 4. IP fallback
    req_ip = MockRequest(client_host="10.20.30.40")
    assert get_rate_limit_key(req_ip) == "ip:10.20.30.40"


def test_rate_limiting_enforcement_and_429():
    test_limiter = Limiter(
        key_func=get_rate_limit_key,
        storage_uri="memory://",
        strategy="moving-window",
        headers_enabled=False,
    )

    test_app = FastAPI()
    test_app.state.limiter = test_limiter
    test_app.add_middleware(SlowAPIMiddleware)
    setup_error_handlers(test_app)

    @test_app.get("/limited")
    @test_limiter.limit("2/minute")
    def limited_endpoint(request: Request):
        return {"status": "ok"}

    client = TestClient(test_app)

    # First request -> OK
    res1 = client.get("/limited")
    assert res1.status_code == 200
    assert res1.json() == {"status": "ok"}

    # Second request -> OK
    res2 = client.get("/limited")
    assert res2.status_code == 200

    # Third request -> 429 Too Many Requests
    res3 = client.get("/limited")
    assert res3.status_code == 429
    data = res3.json()
    assert "Rate limit exceeded" in data["detail"]
    assert data["error_type"] == "RateLimitExceeded"
    assert "retry-after" in res3.headers


def test_rate_limiting_disabled():
    test_limiter = Limiter(
        key_func=get_rate_limit_key,
        storage_uri="memory://",
        strategy="moving-window",
        enabled=False,
        headers_enabled=False,
    )

    test_app = FastAPI()
    test_app.state.limiter = test_limiter
    test_app.add_middleware(SlowAPIMiddleware)
    setup_error_handlers(test_app)

    @test_app.get("/unlimited")
    @test_limiter.limit("1/minute")
    def unlimited_endpoint(request: Request):
        return {"status": "ok"}

    client = TestClient(test_app)

    # All requests should succeed because limiter is disabled
    for _ in range(5):
        res = client.get("/unlimited")
        assert res.status_code == 200


def test_mcp_client_quota_isolation():
    test_limiter = Limiter(
        key_func=get_rate_limit_key,
        storage_uri="memory://",
        strategy="moving-window",
    )

    test_app = FastAPI()
    test_app.state.limiter = test_limiter
    test_app.add_middleware(SlowAPIMiddleware)
    setup_error_handlers(test_app)

    @test_app.get("/mcp-test")
    @test_limiter.limit("1/minute")
    def mcp_test_endpoint(request: Request):
        return {"status": "ok"}

    client = TestClient(test_app)

    # Agent A call 1 -> OK
    res_a1 = client.get("/mcp-test", headers={"X-MCP-Client": "agent-alpha"})
    assert res_a1.status_code == 200

    # Agent A call 2 -> 429
    res_a2 = client.get("/mcp-test", headers={"X-MCP-Client": "agent-alpha"})
    assert res_a2.status_code == 429

    # Agent B call 1 -> OK (separate quota from Agent A)
    res_b1 = client.get("/mcp-test", headers={"X-MCP-Client": "agent-beta"})
    assert res_b1.status_code == 200


def test_rate_limiter_creation_fallback():
    # Verify limiter creation works and returns a Limiter instance
    lim = create_limiter()
    assert isinstance(lim, Limiter)
    assert lim.enabled is True
