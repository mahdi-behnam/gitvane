from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.logging import logger

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
async def check_health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Health check endpoint confirming database and application state"""
    try:
        # Verify database connectivity
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.critical(f"Health check failed to connect to database: {str(e)}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "detail": "Failed to connect to the database",
        }
