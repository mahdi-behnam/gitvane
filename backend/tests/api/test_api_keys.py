import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.core.security_utils import create_access_token, generate_api_key, hash_api_key
from app.db.base import Base
from app.db.models import ApiKey, User
from app.main import app


@pytest.fixture
async def async_db():
    """Create in-memory SQLite database and return sessionmaker."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Seed initial test users
    async with session_factory() as session:
        user1 = User(
            id=1,
            email="user1@example.com",
            full_name="User One",
            hashed_password="hashed_pw_1",
            is_active=True,
        )
        user2 = User(
            id=2,
            email="user2@example.com",
            full_name="User Two",
            hashed_password="hashed_pw_2",
            is_active=True,
        )
        inactive_user = User(
            id=3,
            email="inactive@example.com",
            full_name="Inactive User",
            hashed_password="hashed_pw_3",
            is_active=False,
        )
        session.add_all([user1, user2, inactive_user])
        await session.commit()

    yield session_factory
    await engine.dispose()


@pytest.fixture
def override_db(async_db):
    """Override FastAPI get_db dependency to point to the in-memory SQLite database."""
    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_db() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_create_api_key_success(override_db, async_db):
    """Test generating a new personal API key returns 201 and exposes raw_key once."""
    user1_jwt = create_access_token(1)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/api-keys",
            json={"name": "CLI Token"},
            headers={"Authorization": f"Bearer {user1_jwt}"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "CLI Token"
    assert "id" in data
    assert "key_prefix" in data
    assert data["raw_key"].startswith("gv_live_")
    assert data["key_prefix"] == data["raw_key"][:12]
    assert data["is_revoked"] is False
    assert data["expires_at"] is None

    # Verify hashed_key stored in DB matches hash of raw_key
    async with async_db() as session:
        result = await session.execute(
            select(ApiKey).where(ApiKey.id == uuid.UUID(data["id"]))
        )
        stored_key = result.scalars().first()
        assert stored_key is not None
        assert stored_key.hashed_key == hash_api_key(data["raw_key"])
        assert stored_key.user_id == 1


@pytest.mark.asyncio
async def test_create_api_key_with_expiration(override_db, async_db):
    """Test generating an API key with expires_in_days sets expires_at correctly."""
    user1_jwt = create_access_token(1)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/api-keys",
            json={"name": "Expiring Key", "expires_in_days": 30},
            headers={"Authorization": f"Bearer {user1_jwt}"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["expires_at"] is not None


@pytest.mark.asyncio
async def test_create_api_key_validation_errors(override_db):
    """Test input validation on name and expires_in_days."""
    user1_jwt = create_access_token(1)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Empty name
        res1 = await client.post(
            "/api/v1/api-keys",
            json={"name": ""},
            headers={"Authorization": f"Bearer {user1_jwt}"},
        )
        assert res1.status_code == 422

        # Invalid expires_in_days (< 1)
        res2 = await client.post(
            "/api/v1/api-keys",
            json={"name": "Test", "expires_in_days": 0},
            headers={"Authorization": f"Bearer {user1_jwt}"},
        )
        assert res2.status_code == 422

        # Invalid expires_in_days (> 365)
        res3 = await client.post(
            "/api/v1/api-keys",
            json={"name": "Test", "expires_in_days": 366},
            headers={"Authorization": f"Bearer {user1_jwt}"},
        )
        assert res3.status_code == 422


@pytest.mark.asyncio
async def test_list_api_keys_isolation(override_db, async_db):
    """Test listing API keys returns only the caller's keys without raw_key."""
    # Seed keys for User 1 and User 2
    raw1, prefix1, hash1 = generate_api_key()
    raw2, prefix2, hash2 = generate_api_key()
    raw3, prefix3, hash3 = generate_api_key()

    async with async_db() as session:
        k1 = ApiKey(user_id=1, name="U1 Key 1", key_prefix=prefix1, hashed_key=hash1)
        k2 = ApiKey(user_id=1, name="U1 Key 2", key_prefix=prefix2, hashed_key=hash2)
        k3 = ApiKey(user_id=2, name="U2 Key 1", key_prefix=prefix3, hashed_key=hash3)
        session.add_all([k1, k2, k3])
        await session.commit()

    user1_jwt = create_access_token(1)
    user2_jwt = create_access_token(2)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # User 1 listing
        res1 = await client.get(
            "/api/v1/api-keys",
            headers={"Authorization": f"Bearer {user1_jwt}"},
        )
        assert res1.status_code == 200
        keys_u1 = res1.json()
        assert len(keys_u1) == 2
        assert {k["name"] for k in keys_u1} == {"U1 Key 1", "U1 Key 2"}
        for k in keys_u1:
            assert "raw_key" not in k

        # User 2 listing
        res2 = await client.get(
            "/api/v1/api-keys",
            headers={"Authorization": f"Bearer {user2_jwt}"},
        )
        assert res2.status_code == 200
        keys_u2 = res2.json()
        assert len(keys_u2) == 1
        assert keys_u2[0]["name"] == "U2 Key 1"


@pytest.mark.asyncio
async def test_revoke_api_key(override_db, async_db):
    """Test revoking an API key marks is_revoked and invalidates auth."""
    raw_key, prefix, hashed = generate_api_key()
    key_id = uuid.uuid4()

    async with async_db() as session:
        k = ApiKey(
            id=key_id,
            user_id=1,
            name="To Revoke",
            key_prefix=prefix,
            hashed_key=hashed,
        )
        session.add(k)
        await session.commit()

    user1_jwt = create_access_token(1)
    user2_jwt = create_access_token(2)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # User 2 cannot revoke User 1's key -> 404
        res_forbidden = await client.delete(
            f"/api/v1/api-keys/{key_id}",
            headers={"Authorization": f"Bearer {user2_jwt}"},
        )
        assert res_forbidden.status_code == 404

        # User 1 successfully revokes -> 204
        res_revoke = await client.delete(
            f"/api/v1/api-keys/{key_id}",
            headers={"Authorization": f"Bearer {user1_jwt}"},
        )
        assert res_revoke.status_code == 204

        # Subsequent request using the revoked API key -> 401
        res_use_revoked = await client.get(
            "/api/v1/api-keys",
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert res_use_revoked.status_code == 401


@pytest.mark.asyncio
async def test_dual_auth_with_api_key_and_last_used_tracking(override_db, async_db):
    """Test authenticating with personal API key on endpoints and updating last_used_at."""
    raw_key, prefix, hashed = generate_api_key()
    key_id = uuid.uuid4()

    async with async_db() as session:
        k = ApiKey(
            id=key_id,
            user_id=1,
            name="Automation Key",
            key_prefix=prefix,
            hashed_key=hashed,
            last_used_at=None,
        )
        session.add(k)
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/api-keys",
            headers={"Authorization": f"Bearer {raw_key}"},
        )

    assert response.status_code == 200
    assert len(response.json()) == 1

    # Verify last_used_at was updated in DB
    async with async_db() as session:
        result = await session.execute(
            select(ApiKey).where(ApiKey.id == key_id)
        )
        updated_k = result.scalars().first()
        assert updated_k.last_used_at is not None


@pytest.mark.asyncio
async def test_dual_auth_invalid_and_expired_keys(override_db, async_db):
    """Test 401 rejection for invalid, expired, and inactive user API keys."""
    # 1. Expired key
    raw_exp, prefix_exp, hashed_exp = generate_api_key()
    expired_time = datetime.now(timezone.utc) - timedelta(days=1)

    # 2. Inactive user key
    raw_inact, prefix_inact, hashed_inact = generate_api_key()

    async with async_db() as session:
        k_exp = ApiKey(
            user_id=1,
            name="Expired Key",
            key_prefix=prefix_exp,
            hashed_key=hashed_exp,
            expires_at=expired_time,
        )
        k_inact = ApiKey(
            user_id=3,  # Inactive user
            name="Inactive User Key",
            key_prefix=prefix_inact,
            hashed_key=hashed_inact,
        )
        session.add_all([k_exp, k_inact])
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Invalid key string
        res_invalid = await client.get(
            "/api/v1/api-keys",
            headers={"Authorization": "Bearer gv_live_non_existent_key_12345"},
        )
        assert res_invalid.status_code == 401

        # Expired key
        res_expired = await client.get(
            "/api/v1/api-keys",
            headers={"Authorization": f"Bearer {raw_exp}"},
        )
        assert res_expired.status_code == 401

        # Inactive user key
        res_inactive = await client.get(
            "/api/v1/api-keys",
            headers={"Authorization": f"Bearer {raw_inact}"},
        )
        assert res_inactive.status_code == 401

        # Missing token
        res_no_auth = await client.get("/api/v1/api-keys")
        assert res_no_auth.status_code == 401
