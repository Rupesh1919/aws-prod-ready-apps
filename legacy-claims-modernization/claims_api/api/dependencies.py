"""FastAPI dependencies for authentication and database access."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from claims_api.core.config import Settings, get_settings
from claims_api.core.logging import get_logger, set_correlation_id
from claims_api.core.security import AuthenticationError, extract_bearer_token, verify_token
from claims_api.db.repository import ClaimRepository
from claims_api.db.session import get_db

logger = get_logger("api.dependencies")


def get_repository(session: Session = Depends(get_db)) -> ClaimRepository:
    """
    Get claim repository dependency.
    
    Args:
        session: Database session
        
    Returns:
        Claim repository
    """
    return ClaimRepository(session)


def verify_auth(
    authorization: Annotated[str | None, Header()] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """
    Verify JWT authentication for protected endpoints.
    
    Args:
        authorization: Authorization header
        x_correlation_id: Optional correlation ID header
        settings: Application settings
        
    Returns:
        Token claims
        
    Raises:
        HTTPException: If authentication fails
    """
    # Set correlation ID
    correlation_id = set_correlation_id(x_correlation_id)
    
    # Skip auth if disabled (local development only)
    if not settings.auth_enabled:
        logger.warning("Authentication is DISABLED - development mode only")
        return {"sub": "anonymous", "aud": "dev", "correlation_id": correlation_id}
    
    try:
        # Extract and verify token
        token = extract_bearer_token(authorization)
        claims = verify_token(token, settings)
        claims["correlation_id"] = correlation_id
        return claims
    except AuthenticationError as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )


def optional_correlation_id(
    x_correlation_id: Annotated[str | None, Header()] = None,
) -> str:
    """
    Extract or generate correlation ID for anonymous endpoints.
    
    Args:
        x_correlation_id: Optional correlation ID header
        
    Returns:
        Correlation ID
    """
    return set_correlation_id(x_correlation_id)


# Type aliases for dependency injection
AuthenticatedUser = Annotated[dict[str, str], Depends(verify_auth)]
Repository = Annotated[ClaimRepository, Depends(get_repository)]
CorrelationId = Annotated[str, Depends(optional_correlation_id)]
