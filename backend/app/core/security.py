"""
Security utilities: password hashing, JWT creation/verification.
Passwords are NEVER stored in plaintext.
Uses Argon2 (memory-hard, resistant to GPU brute-force).
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Argon2 is the winner of the Password Hashing Competition (PHC).
# It provides strong resistance to GPU-accelerated brute force attacks.
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,   # 64 MB
    argon2__time_cost=3,          # 3 iterations
    argon2__parallelism=4,        # 4 threads
)


def hash_password(plain_password: str) -> str:
    """Hash a password using Argon2. Never store the plain password."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored Argon2 hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    extra_data: Optional[dict] = None,
) -> str:
    """
    Create a signed JWT access token.
    The token contains the user ID (sub) and expiration time.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra_data:
        payload.update(extra_data)

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: Union[str, Any]) -> str:
    """Create a signed JWT refresh token with longer expiry."""
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "refresh",
        "jti": secrets.token_hex(16),  # JWT ID for revocation support
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT token.
    Raises jwt.InvalidTokenError on failure.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def encrypt_sensitive_data(data: str) -> str:
    """
    Placeholder for OAuth token encryption.
    Phase 6+: Replace with Fernet or AWS KMS encryption.
    """
    # TODO (Phase 6): Implement proper symmetric encryption (e.g. Fernet)
    # For now, this is a no-op placeholder to mark the interface.
    raise NotImplementedError(
        "Sensitive data encryption is not implemented in Phase 1. "
        "This will be implemented when OAuth is added in Phase 6."
    )


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    Placeholder for OAuth token decryption.
    Phase 6+: Replace with Fernet or AWS KMS decryption.
    """
    raise NotImplementedError(
        "Sensitive data decryption is not implemented in Phase 1."
    )
