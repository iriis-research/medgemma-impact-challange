"""
Authentication and Security Utilities
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.database import get_db
from app.db.models import User

# Bcrypt has a 72-byte limit; truncate to avoid ValueError (matches common practice).
BCRYPT_MAX_BYTES = 72
security = HTTPBearer()


def _prepare_password(password: str) -> bytes:
    """Encode password to bytes and truncate to bcrypt's 72-byte limit."""
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > BCRYPT_MAX_BYTES:
        pw_bytes = pw_bytes[:BCRYPT_MAX_BYTES]
    return pw_bytes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        _prepare_password(plain_password),
        hashed_password.encode("utf-8") if isinstance(hashed_password, str) else hashed_password,
    )


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(_prepare_password(password), bcrypt.gensalt()).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token."""
    import logging
    logger = logging.getLogger(__name__)
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        logger.info(f"🔐 Validating token: {token[:20]}...")
        logger.debug(f"   Using secret key: {settings.secret_key[:20]}...")
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("❌ Token payload missing 'sub' field")
            raise credentials_exception
        logger.info(f"✅ Token validated for email: {email}")
    except JWTError as e:
        logger.error(f"❌ JWT validation failed: {type(e).__name__}: {e}")
        logger.error(f"   Secret key being used: {settings.secret_key[:20]}...")
        logger.error("   Possible causes: Token expired, wrong secret key, or invalid token format")
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"❌ User not found for email: {email}")
        raise credentials_exception
    if not user.is_active:
        logger.warning(f"❌ User {email} is inactive")
        raise HTTPException(status_code=400, detail="Inactive user")
    
    logger.debug(f"✅ User authenticated: {user.email} (ID: {user.id})")
    return user

