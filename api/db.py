"""AsyncPG connection pool and schema bootstrap for the CDC API service.

Callers: api/main.py (lifespan), api/auth.py, api/routers/auth.py,
api/routers/alerts.py.
"""

import logging

import asyncpg
from passlib.context import CryptContext

from config import settings

logger = logging.getLogger("cdc-api.db")

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_pool: asyncpg.Pool | None = None

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS api_users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(100) UNIQUE NOT NULL,
  password_hash VARCHAR(200) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'viewer',
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS pipeline_alerts (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  severity VARCHAR(20) NOT NULL,
  details JSONB,
  fired_at TIMESTAMP NOT NULL DEFAULT NOW(),
  acknowledged_at TIMESTAMP,
  acknowledged_by VARCHAR(100)
);
"""


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of a plaintext password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return _pwd_context.verify(plain, hashed)
    except ValueError:
        return False


async def connect() -> None:
    """Create the global connection pool. Idempotent."""
    global _pool
    if _pool is not None:
        return
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=1,
        max_size=10,
        command_timeout=30,
    )
    logger.info("Postgres connection pool established.")


async def disconnect() -> None:
    """Close the global connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Postgres connection pool closed.")


def get_pool() -> asyncpg.Pool:
    """Return the active pool or raise if the API was not initialized."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialized.")
    return _pool


async def init_schema() -> None:
    """Create required tables and seed a default admin user if none exist."""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(_SCHEMA_SQL)
        # ON CONFLICT DO NOTHING makes the seed atomic: safe under concurrent
        # startup (multiple container replicas) and idempotent on restart.
        result = await conn.execute(
            "INSERT INTO api_users (username, password_hash, role) "
            "VALUES ($1, $2, $3) ON CONFLICT (username) DO NOTHING",
            "admin",
            hash_password(settings.admin_password),
            "admin",
        )
        if result.endswith("1"):
            logger.info("Seeded default admin user.")
    logger.info("Database schema ready.")
