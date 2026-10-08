"""
Authentication dependency for FastAPI routes.
Provides get_current_user dependency for protected endpoints.
"""
import uuid
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException, Header, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import decode_token
from app.db.database import get_db
from app.db.models.user import User

settings = get_settings()
logger = get_logger(__name__)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None),
    access_token: str = Cookie(None),
    token_query: str = Query(None, alias="token"),
) -> User:
    """
    FastAPI dependency that extracts and validates the current user.
    
    Supports three token delivery mechanisms:
    1. Authorization: Bearer <token> header (standard API clients)
    2. HttpOnly access_token cookie (browser clients — more secure)
    3. ?token=<token> query parameter (for direct iframe / media embedding)
    
    Raises HTTP 401 if token is missing, invalid, or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token: str | None = None

    # Try Authorization header first
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    # Fall back to cookie
    elif access_token:
        token = access_token
    # Fall back to URL query token
    elif token_query:
        token = token_query

    if not token:
        raise credentials_exception

    try:
        payload = decode_token(token)
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise credentials_exception
        token_type: str = payload.get("type", "access")
        if token_type != "access":
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise credentials_exception

    # Load user from DB
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return user


# Convenient type alias
CurrentUser = Annotated[User, Depends(get_current_user)]
