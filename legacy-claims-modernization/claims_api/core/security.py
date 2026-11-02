"""Security utilities for JWT authentication."""

import time
from typing import Any

import httpx
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

from claims_api.core.config import Settings
from claims_api.core.logging import get_logger

logger = get_logger("security")

# Global JWKS cache
_jwks_cache: dict[str, Any] = {}
_jwks_cache_time: float = 0


class AuthenticationError(Exception):
    """Authentication failed."""

    pass


def get_jwks(settings: Settings, force_refresh: bool = False) -> dict[str, Any]:
    """
    Fetch JWKS from the issuer with caching.
    
    Args:
        settings: Application settings
        force_refresh: Force refresh of cached keys
        
    Returns:
        JWKS dictionary
        
    Raises:
        AuthenticationError: If JWKS cannot be fetched
    """
    global _jwks_cache, _jwks_cache_time

    current_time = time.time()
    cache_age = current_time - _jwks_cache_time

    # Return cached keys if still valid
    if not force_refresh and _jwks_cache and cache_age < settings.jwks_cache_ttl:
        return _jwks_cache

    # Fetch fresh keys
    try:
        logger.info(f"Fetching JWKS from {settings.jwks_url}")
        response = httpx.get(settings.jwks_url, timeout=10.0, follow_redirects=False)
        response.raise_for_status()
        
        jwks_data = response.json()
        _jwks_cache = jwks_data
        _jwks_cache_time = current_time
        
        logger.info(f"JWKS cached with {len(jwks_data.get('keys', []))} keys")
        return jwks_data
        
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        # If we have stale cache, use it as fallback
        if _jwks_cache:
            logger.warning("Using stale JWKS cache")
            return _jwks_cache
        raise AuthenticationError(f"Failed to fetch JWKS: {e}")


def verify_token(token: str, settings: Settings) -> dict[str, Any]:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token string
        settings: Application settings
        
    Returns:
        Decoded token claims
        
    Raises:
        AuthenticationError: If token is invalid
    """
    try:
        # Decode header without verification to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        alg = unverified_header.get("alg")
        
        if not kid:
            raise AuthenticationError("Token missing 'kid' header")
        
        if not alg:
            raise AuthenticationError("Token missing 'alg' header")
            
        # Validate algorithm
        if alg not in settings.jwt_algorithms_list:
            raise AuthenticationError(
                f"Algorithm '{alg}' not allowed. Permitted: {settings.jwt_algorithms_list}"
            )
        
        # Get JWKS
        jwks = get_jwks(settings)
        
        # Find matching key
        signing_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                signing_key = key
                break
        
        if not signing_key:
            # Try refreshing JWKS in case of key rotation
            logger.info(f"Key ID '{kid}' not found, refreshing JWKS")
            jwks = get_jwks(settings, force_refresh=True)
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    signing_key = key
                    break
        
        if not signing_key:
            raise AuthenticationError(f"No signing key found for kid '{kid}'")
        
        # Verify and decode token
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=settings.jwt_algorithms_list,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
        
        return claims
        
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise AuthenticationError(f"Invalid token: {e}")
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise AuthenticationError(f"Token verification failed: {e}")


def extract_bearer_token(authorization: str | None) -> str:
    """
    Extract token from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Bearer token
        
    Raises:
        AuthenticationError: If header is invalid
    """
    if not authorization:
        raise AuthenticationError("Missing Authorization header")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid Authorization header format. Expected 'Bearer <token>'")
    
    return parts[1]
