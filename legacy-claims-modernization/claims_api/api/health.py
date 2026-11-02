"""Health check endpoints."""

import signal
from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from claims_api.api.dependencies import CorrelationId
from claims_api.core.config import get_settings
from claims_api.core.logging import get_logger
from claims_api.db.session import get_db_context

logger = get_logger("api.health")

router = APIRouter(prefix="/health", tags=["health"])

# Track shutdown state
_shutdown_requested = False


def request_shutdown() -> None:
    """Mark that shutdown has been requested."""
    global _shutdown_requested
    _shutdown_requested = True


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Service is alive"},
        503: {"description": "Service is shutting down"},
    },
)
def liveness_check(correlation_id: CorrelationId) -> dict[str, str]:
    """
    Liveness probe - indicates if the process is running.
    
    Does not check database connectivity. Returns 503 if shutdown requested.
    No authentication required.
    """
    if _shutdown_requested:
        return Response(
            content='{"status":"shutting_down"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json",
        )
    
    return {"status": "alive"}


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Service is ready to accept requests"},
        503: {"description": "Service is not ready"},
    },
)
def readiness_check(correlation_id: CorrelationId, response: Response) -> dict[str, Any]:
    """
    Readiness probe - indicates if the service can handle requests.
    
    Verifies database connectivity with timeout. No authentication required.
    Returns minimal information publicly to avoid exposing internal details.
    """
    settings = get_settings()
    
    # Check shutdown state
    if _shutdown_requested:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": "shutting_down"}
    
    # Check database connectivity
    try:
        with get_db_context() as session:
            # Simple query with timeout
            stmt = text(f"SELECT 1").execution_options(
                timeout=settings.health_db_timeout
            )
            result = session.execute(stmt)
            result.scalar()
        
        return {"status": "ready", "database": "connected"}
        
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": "database_unavailable"}
    except Exception as e:
        logger.error(f"Unexpected error in health check: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": "internal_error"}
