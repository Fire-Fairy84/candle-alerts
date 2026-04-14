"""API key authentication dependency for FastAPI routes."""

import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from candle.config import settings

_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_header_scheme)) -> str:
    """Validate the X-API-Key request header.

    When settings.api_key is empty (local dev), authentication is skipped and
    all requests are allowed through. In production, the header must match exactly.

    Args:
        api_key: Value from the X-API-Key header, or None if absent.

    Returns:
        The validated API key string.

    Raises:
        HTTPException 401: When a key is configured and the header does not match.
    """
    if not settings.api_key:
        return ""
    if not secrets.compare_digest(api_key or "", settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key
