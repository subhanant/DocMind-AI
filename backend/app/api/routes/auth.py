"""Auth routes: register, login, logout, me."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.auth import (
    AuthMeResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.schemas.common import APIResponse

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=APIResponse[TokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    body: UserRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TokenResponse]:
    """
    Register a new user account.
    Password is hashed with Argon2 before storage.
    Returns a JWT access token on success.
    """
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    access_token = create_access_token(subject=str(user.id))
    expire_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # Set HttpOnly cookie for browser clients
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=expire_seconds,
    )

    logger.info("New user registered", user_id=str(user.id), email=user.email)

    return APIResponse.ok(
        TokenResponse(
            access_token=access_token,
            expires_in=expire_seconds,
            user=UserResponse.model_validate(user),
        )
    )


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    summary="Login with email and password",
)
async def login(
    body: UserLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TokenResponse]:
    """
    Authenticate with email and password.
    Returns a JWT access token on success.
    Uses constant-time comparison to prevent timing attacks.
    """
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    # Always verify password to prevent timing oracle attacks
    dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$zjkHgDCm9J6TsjZmLOUcww$r1VJw6a/LyiQFLGMsYzscBLX32iCkg0s1aWabxuv+Hg"
    if user:
        is_valid = verify_password(body.password, user.password_hash)
    else:
        try:
            verify_password(body.password, dummy_hash)
        except Exception:
            pass
        is_valid = False

    if not is_valid or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact support.",
        )

    access_token = create_access_token(subject=str(user.id))
    expire_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=expire_seconds,
    )

    logger.info("User logged in", user_id=str(user.id), email=user.email)

    return APIResponse.ok(
        TokenResponse(
            access_token=access_token,
            expires_in=expire_seconds,
            user=UserResponse.model_validate(user),
        )
    )


@router.post(
    "/logout",
    response_model=APIResponse[dict],
    summary="Logout and clear session",
)
async def logout(
    response: Response,
    current_user: CurrentUser,
) -> APIResponse[dict]:
    """
    Logout the current user.
    Clears the HttpOnly cookie.
    
    Note: For stateless JWTs, the token itself remains valid until expiry.
    Phase 2+: Implement token blacklisting via Redis for immediate revocation.
    """
    response.delete_cookie(key="access_token")
    logger.info("User logged out", user_id=str(current_user.id))
    return APIResponse.ok({"message": "Logged out successfully."})


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get current authenticated user",
)
async def get_me(current_user: CurrentUser) -> APIResponse[UserResponse]:
    """Return the authenticated user's public profile."""
    return APIResponse.ok(UserResponse.model_validate(current_user))
