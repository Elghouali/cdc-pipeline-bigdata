"""JWT authentication utilities and FastAPI dependencies.

Callers: api/routers/auth.py, api/routers/query.py, api/routers/connector.py.
Tokens are signed with PyJWT using the algorithm from config (HS256).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config import settings
from db import get_pool
from models import User

logger = logging.getLogger("cdc-api.auth")

# tokenUrl is informational for OpenAPI; login is handled by /auth/login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def create_access_token(*, username: str, role: str, user_id: int) -> tuple[str, int]:
    """Create a signed JWT. Returns (token, expires_in_seconds)."""
    expires_in = settings.access_token_expire_minutes * 60
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": username,
        "role": role,
        "uid": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises HTTPException(401) on failure."""
    try:
        return jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> User:
    """FastAPI dependency that resolves the authenticated user from the JWT."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
        )

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, role, created_at FROM api_users WHERE username = $1",
            username,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists.",
        )

    return User(
        id=row["id"],
        username=row["username"],
        role=row["role"],
        created_at=row["created_at"],
    )


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency that enforces the 'admin' role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this action.",
        )
    return user
