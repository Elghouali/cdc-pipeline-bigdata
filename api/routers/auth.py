"""Authentication router. Issues JWTs and exposes the current-user endpoint.

Caller: api/main.py. Endpoints: POST /auth/login, POST /auth/logout,
GET /auth/me.
"""

import logging
import time
from collections import OrderedDict

from auth import create_access_token, get_current_user
from db import get_pool, verify_password
from fastapi import APIRouter, Depends, HTTPException, Request, status
from models import LoginRequest, Token, User

logger = logging.getLogger("cdc-api.auth-router")

router = APIRouter(prefix="/auth", tags=["auth"])

# Per-process fixed-window guard; a shared gateway is required across replicas.
_ATTEMPTS: OrderedDict[str, tuple[float, int]] = OrderedDict()
_MAX_CLIENTS = 4096
_WINDOW_SECONDS = 60
_MAX_ATTEMPTS = 10


def check_login_rate(client: str) -> None:
    now = time.monotonic()
    while _ATTEMPTS:
        oldest = next(iter(_ATTEMPTS))
        if now - _ATTEMPTS[oldest][0] < _WINDOW_SECONDS:
            break
        _ATTEMPTS.popitem(last=False)
    started, count = _ATTEMPTS.get(client, (now, 0))
    if count >= _MAX_ATTEMPTS or (
        client not in _ATTEMPTS and len(_ATTEMPTS) >= _MAX_CLIENTS
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": "60"},
        )
    _ATTEMPTS[client] = (started, count + 1)


@router.post("/login", response_model=Token)
async def login(body: LoginRequest, request: Request) -> Token:
    """Validate credentials against api_users and return a signed JWT."""
    check_login_rate(request.client.host if request.client else "unknown")
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
