"""Progress Stream Publisher for Redis Streams (Subsystem 5).

- Emits progress events to Redis Streams `gitvane:progress:{generation_id}` via XADD MAXLEN ~ 1000.
- Sets 24h (86400s) TTL on terminal states (`completed`, `failed`, `cancelled`, `superseded`).
- Handles Redis outages gracefully without crashing worker tasks (Invariant 10).
- Supports both async and sync execution contexts.
"""

import asyncio
import json
import logging
from typing import Any, Optional
from uuid import UUID

import redis
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

TERMINAL_STATES = {"completed", "failed", "cancelled", "superseded"}
TERMINAL_TTL_SECONDS = 86400  # 24 hours


class ProgressStreamPublisher:
    """Service to publish and stream progress events via Redis Streams."""

    _async_redis_client: Optional[aioredis.Redis] = None
    _async_client_loop: Optional[asyncio.AbstractEventLoop] = None
    _sync_redis_client: Optional[redis.Redis] = None

    def __init__(
        self,
        async_client: Optional[aioredis.Redis] = None,
        sync_client: Optional[redis.Redis] = None,
        redis_url: Optional[str] = None,
    ) -> None:
        self._custom_async_client = async_client
        self._custom_sync_client = sync_client
        self.redis_url = redis_url or settings.REDIS_URL

    def get_async_client(self) -> aioredis.Redis:
        """Get or initialize the async Redis client for the current running loop."""
        if self._custom_async_client is not None:
            return self._custom_async_client

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if (
            ProgressStreamPublisher._async_redis_client is not None
            and ProgressStreamPublisher._async_client_loop is not None
            and (
                ProgressStreamPublisher._async_client_loop.is_closed()
                or (current_loop is not None and ProgressStreamPublisher._async_client_loop is not current_loop)
            )
        ):
            ProgressStreamPublisher._async_redis_client = None
            ProgressStreamPublisher._async_client_loop = None

        if ProgressStreamPublisher._async_redis_client is None:
            ProgressStreamPublisher._async_redis_client = aioredis.from_url(
                self.redis_url, decode_responses=True
            )
            ProgressStreamPublisher._async_client_loop = current_loop

        return ProgressStreamPublisher._async_redis_client

    def get_sync_client(self) -> redis.Redis:
        """Get or initialize the sync Redis client."""
        if self._custom_sync_client is not None:
            return self._custom_sync_client
        if ProgressStreamPublisher._sync_redis_client is None:
            ProgressStreamPublisher._sync_redis_client = redis.from_url(
                self.redis_url, decode_responses=True
            )
        return ProgressStreamPublisher._sync_redis_client

    @staticmethod
    def get_stream_key(generation_id: UUID | str) -> str:
        """Format the Redis stream key for a generation."""
        return f"gitvane:progress:{generation_id}"

    async def publish_progress(
        self,
        generation_id: UUID | str,
        payload: dict[str, Any],
        is_terminal: bool = False,
    ) -> Optional[str]:
        """Publish progress event to Redis stream asynchronously.
        
        Uses XADD MAXLEN ~ 1000. Sets 24h EXPIRE on terminal states.
        Enforces Invariant 10: Redis failure tolerance (never raises).
        """
        gen_str = str(generation_id)
        stream_key = self.get_stream_key(gen_str)
        status = payload.get("status")

        if status in TERMINAL_STATES:
            is_terminal = True

        enriched_payload = {
            "generation_id": gen_str,
            **payload,
        }

        try:
            client = self.get_async_client()
            msg_id = await client.xadd(
                name=stream_key,
                fields={"data": json.dumps(enriched_payload)},
                maxlen=1000,
                approximate=True,
            )

            if is_terminal:
                await client.expire(stream_key, TERMINAL_TTL_SECONDS)

            return msg_id
        except Exception as exc:
            logger.warning(
                "Failed to publish progress to Redis stream for generation %s: %s",
                gen_str,
                exc,
            )
            return None

    def publish_progress_sync(
        self,
        generation_id: UUID | str,
        payload: dict[str, Any],
        is_terminal: bool = False,
    ) -> Optional[str]:
        """Publish progress event to Redis stream synchronously.
        
        Uses XADD MAXLEN ~ 1000. Sets 24h EXPIRE on terminal states.
        Enforces Invariant 10: Redis failure tolerance (never raises).
        """
        gen_str = str(generation_id)
        stream_key = self.get_stream_key(gen_str)
        status = payload.get("status")

        if status in TERMINAL_STATES:
            is_terminal = True

        enriched_payload = {
            "generation_id": gen_str,
            **payload,
        }

        try:
            client = self.get_sync_client()
            msg_id = client.xadd(
                name=stream_key,
                fields={"data": json.dumps(enriched_payload)},
                maxlen=1000,
                approximate=True,
            )

            if is_terminal:
                client.expire(stream_key, TERMINAL_TTL_SECONDS)

            return msg_id
        except Exception as exc:
            logger.warning(
                "Failed to publish progress (sync) to Redis stream for generation %s: %s",
                gen_str,
                exc,
            )
            return None

    async def get_tail_id(self, generation_id: UUID | str) -> str:
        """Capture current Redis stream tail ID using XREVRANGE.
        
        Returns stream ID string (e.g. '1720000000000-0') or '0-0' if empty/error.
        """
        gen_str = str(generation_id)
        stream_key = self.get_stream_key(gen_str)
        try:
            client = self.get_async_client()
            res = await client.xrevrange(name=stream_key, count=1)
            if res and len(res) > 0:
                return str(res[0][0])
            return "0-0"
        except Exception as exc:
            logger.warning(
                "Failed to capture Redis stream tail ID for generation %s: %s",
                gen_str,
                exc,
            )
            return "0-0"

    async def read_stream(
        self,
        generation_id: UUID | str,
        last_id: str = "0-0",
        block_ms: int = 15000,
        count: int = 100,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Read pending stream entries using XREAD BLOCK."""
        gen_str = str(generation_id)
        stream_key = self.get_stream_key(gen_str)
        results: list[tuple[str, dict[str, Any]]] = []

        try:
            client = self.get_async_client()
            res = await client.xread(
                streams={stream_key: last_id},
                block=block_ms,
                count=count,
            )
            if res:
                for _s_name, stream_entries in res:
                    for entry_id, fields in stream_entries:
                        data_val = fields.get("data")
                        if isinstance(data_val, str):
                            try:
                                payload = json.loads(data_val)
                            except Exception:
                                payload = fields
                        else:
                            payload = fields
                        results.append((str(entry_id), payload))
        except Exception as exc:
            logger.warning(
                "Failed to read from Redis stream for generation %s: %s",
                gen_str,
                exc,
            )

        return results

    @classmethod
    async def close(cls) -> None:
        """Close shared Redis connection pools."""
        if cls._async_redis_client is not None:
            try:
                await cls._async_redis_client.aclose()
            except Exception:
                pass
            cls._async_redis_client = None

        if cls._sync_redis_client is not None:
            try:
                cls._sync_redis_client.close()
            except Exception:
                pass
            cls._sync_redis_client = None


def get_progress_publisher() -> ProgressStreamPublisher:
    """Dependency provider for ProgressStreamPublisher."""
    return ProgressStreamPublisher()
