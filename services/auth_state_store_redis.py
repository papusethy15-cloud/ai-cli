import json
from contextlib import contextmanager
from typing import Dict, Tuple


class RedisAuthStateStore:
    def __init__(self, redis_url: str, key_prefix: str, lock_ttl_ms: int = 15000):
        try:
            import redis
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "Redis backend requested but redis package is not installed. "
                "Install with: pip install redis"
            ) from e

        self._redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = (key_prefix or "aicli:auth").strip().rstrip(":")
        self._lock_name = f"{self._key_prefix}:state_lock"
        self._lock_ttl_s = max(1.0, int(lock_ttl_ms) / 1000.0)
        self._redis_client.ping()

    def _key(self, suffix: str) -> str:
        return f"{self._key_prefix}:{suffix}"

    def _dump_json(self, payload) -> str:
        def _default(obj):
            if isinstance(obj, set):
                return sorted(obj)
            raise TypeError(f"Unsupported type for JSON serialization: {type(obj)!r}")

        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), default=_default)

    def _load_json(self, raw: str):
        if raw is None:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    @contextmanager
    def lock(self):
        lock = self._redis_client.lock(
            self._lock_name,
            timeout=self._lock_ttl_s,
            blocking=True,
            blocking_timeout=10,
        )
        acquired = lock.acquire()
        if not acquired:
            raise RuntimeError("Failed to acquire Redis auth state lock.")
        try:
            yield
        finally:
            try:
                lock.release()
            except Exception:
                pass

    def load_snapshot(self) -> Tuple[Dict[str, dict], Dict[str, dict], Dict[str, dict]]:
        keys = [
            self._key("access_tokens"),
            self._key("refresh_tokens"),
            self._key("pending_devices"),
        ]
        access_raw, refresh_raw, pending_raw = self._redis_client.mget(keys)

        access_tokens = self._load_json(access_raw)
        refresh_tokens = self._load_json(refresh_raw)
        pending_devices = self._load_json(pending_raw)

        if not isinstance(access_tokens, dict):
            access_tokens = {}
        if not isinstance(refresh_tokens, dict):
            refresh_tokens = {}
        if not isinstance(pending_devices, dict):
            pending_devices = {}

        for record in access_tokens.values():
            if isinstance(record, dict) and isinstance(record.get("scopes"), list):
                record["scopes"] = set(record["scopes"])

        for record in refresh_tokens.values():
            if isinstance(record, dict) and isinstance(record.get("scopes"), list):
                record["scopes"] = set(record["scopes"])

        for record in pending_devices.values():
            if isinstance(record, dict) and isinstance(record.get("approved_scopes"), list):
                record["approved_scopes"] = set(record["approved_scopes"])

        return access_tokens, refresh_tokens, pending_devices

    def save_snapshot(
        self,
        access_tokens: Dict[str, dict],
        refresh_tokens: Dict[str, dict],
        pending_devices: Dict[str, dict],
    ):
        pipe = self._redis_client.pipeline()
        pipe.set(self._key("access_tokens"), self._dump_json(access_tokens))
        pipe.set(self._key("refresh_tokens"), self._dump_json(refresh_tokens))
        pipe.set(self._key("pending_devices"), self._dump_json(pending_devices))
        pipe.execute()
