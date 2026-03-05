from config import (
    AUTH_STATE_BACKEND,
    AUTH_STATE_DB_PATH,
    AUTH_STATE_REDIS_LOCK_TTL_MS,
    AUTH_STATE_REDIS_PREFIX,
    AUTH_STATE_REDIS_URL,
)
from services.auth_state_store import AuthStateStore
from services.auth_state_store_redis import RedisAuthStateStore


def create_auth_state_store(
    backend: str = AUTH_STATE_BACKEND,
    *,
    sqlite_path: str = AUTH_STATE_DB_PATH,
    redis_url: str = AUTH_STATE_REDIS_URL,
    redis_prefix: str = AUTH_STATE_REDIS_PREFIX,
    redis_lock_ttl_ms: int = AUTH_STATE_REDIS_LOCK_TTL_MS,
):
    name = (backend or "sqlite").strip().lower()
    if name == "sqlite":
        return AuthStateStore(sqlite_path)
    if name == "redis":
        return RedisAuthStateStore(
            redis_url=redis_url,
            key_prefix=redis_prefix,
            lock_ttl_ms=redis_lock_ttl_ms,
        )
    raise RuntimeError(
        f"Unsupported auth state backend: {backend}. "
        "Use one of: sqlite, redis."
    )
