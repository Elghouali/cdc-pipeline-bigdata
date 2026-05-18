"""Authentication router. Issues JWTs and exposes the current-user endpoint.

Caller: api/main.py. Endpoints: POST /auth/login, POST /auth/logout,
GET /auth/me.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from auth import create_access_token, get_current_user
from db import get_pool, verify_password
from models import LoginRequest, Token, User

logger = logging.getLogger("cdc-api.auth-router")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(body: LoginRequest) -> Token:
    """Validate credentials against api_users and return a signed JWT."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, password_hash, role FROM api_users "
            "WHERE username = $1",
            body.username,
        )

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if row is None or not verify_password(body.password, row["password_hash"]):
        logger.info("Failed login attempt for username '%s'.", body.username)
        raise invalid

    token, expires_in = create_access_token(
        username=row["username"], role=row["role"], user_id=row["id"]
    )
    logger.info("User '%s' authenticated.", row["username"])
    return Token(
        access_token=token,
        expires_in=expires_in,
        role=row["role"],
        username=row["username"],
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout() -> dict[str, str]:
    """Stateless logout. The client is responsible for discarding the token."""
    return {"detail": "Logged out. Discard the access token on the client."}


@router.get("/me", response_model=User)
async def me(user: User = Depends(get_current_user)) -> User:
    """Return the profile of the currently authenticated user."""
    return user
