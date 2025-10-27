from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
import redis
from app.core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check(db: Session = Depends(get_db)) -> dict:
    """Health check endpoint.

    Args:
        db (Session): Database session dependency.

    Returns:
        dict: Health status.
    """
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown"
    }
    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: unable to connect to database - {str(e)}"
        health_status["status"] = "unhealthy"

    # Check Redis connection
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        health_status["redis"] = f"error: unable to connect to redis - {str(e)}"
        health_status["status"] = "unhealthy"

    return health_status


