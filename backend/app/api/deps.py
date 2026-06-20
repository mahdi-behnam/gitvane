from app.db.session import get_db

# Export session generator to use across routes
__all__ = ["get_db"]
