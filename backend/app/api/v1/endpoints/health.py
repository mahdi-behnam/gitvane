from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.api.deps import get_db
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


@router.get("")
async def check_health(
    response: Response, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """Health check endpoint confirming database and redis connectivity state."""
    db_ok = True
    try:
        # Verify database connectivity
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.critical(f"Health check failed to connect to database: {str(e)}")
        db_ok = False

    redis_ok = True
    try:
        r = redis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        await r.ping()
        await r.aclose()
    except Exception as e:
        logger.critical(f"Health check failed to connect to redis: {str(e)}")
        redis_ok = False

    if not db_ok or not redis_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "database": "connected" if db_ok else "disconnected",
            "redis": "connected" if redis_ok else "disconnected",
            "detail": "Failed to connect to required service dependencies",
        }

    response.status_code = status.HTTP_200_OK
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
    }
