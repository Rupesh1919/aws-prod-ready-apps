"""Main FastAPI application."""

import signal
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from claims_api.api import claims, health
from claims_api.core.config import get_settings
from claims_api.core.logging import get_correlation_id, get_logger, setup_logging
from claims_api.db.session import close_db, init_db
from claims_api.models.schemas import ProblemDetail

# Setup logging first
setup_logging()
logger = get_logger("main")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """
    Application lifespan events.
    
    Handles startup and shutdown:
    - Initialize database connections
    - Register signal handlers
    - Clean up resources on shutdown
    """
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Auth enabled: {settings.auth_enabled}")
    
    # Initialize database
    init_db(settings)
    
    # Register signal handlers for graceful shutdown
    def handle_sigterm(signum: int, frame: Any) -> None:
        logger.info("SIGTERM received, initiating graceful shutdown")
        health.request_shutdown()
    
    def handle_sigint(signum: int, frame: Any) -> None:
        logger.info("SIGINT received, initiating graceful shutdown")
        health.request_shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigint)
    
    logger.info("Application started successfully")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down application")
    close_db()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    openapi_url=settings.openapi_url if settings.openapi_enabled else None,
    docs_url=settings.docs_url if settings.openapi_enabled else None,
    redoc_url=None,  # Disable ReDoc
)

# CORS - disabled by default, configure if needed
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["https://your-frontend.example.com"],
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PATCH"],
#     allow_headers=["Authorization", "X-Correlation-ID"],
# )

# Include routers
app.include_router(health.router)
app.include_router(claims.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors with RFC 7807 Problem Details."""
    correlation_id = get_correlation_id()
    
    logger.warning(
        f"Validation error: {exc.errors()}",
        extra={"extra_fields": {"errors": exc.errors()}},
    )
    
    problem = ProblemDetail(
        type="about:blank",
        title="Validation Error",
        status=status.HTTP_400_BAD_REQUEST,
        detail="Request validation failed",
        instance=str(request.url),
        errors=exc.errors(),
    )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=problem.model_dump(),
        headers={"X-Correlation-ID": correlation_id} if correlation_id else {},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors safely without exposing internals."""
    correlation_id = get_correlation_id()
    
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    problem = ProblemDetail(
        type="about:blank",
        title="Internal Server Error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred",
        instance=str(request.url),
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem.model_dump(),
        headers={"X-Correlation-ID": correlation_id} if correlation_id else {},
    )


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }
