import unittest
import os
import tempfile
from unittest.mock import patch

from services.auth_state_factory import create_auth_state_store
from services.auth_state_store import AuthStateStore


class AuthStateFactoryTests(unittest.TestCase):
    def test_sqlite_backend_returns_sqlite_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = create_auth_state_store(
                "sqlite",
                sqlite_path=os.path.join(tmp, "auth.db"),
            )
        self.assertIsInstance(store, AuthStateStore)

    def test_unknown_backend_raises(self):
        with self.assertRaises(RuntimeError):
            create_auth_state_store("unknown-backend")

    def test_redis_backend_uses_redis_store_class(self):
        class DummyStore:
            def __init__(self, redis_url, key_prefix, lock_ttl_ms):
                self.redis_url = redis_url
                self.key_prefix = key_prefix
                self.lock_ttl_ms = lock_ttl_ms

        with patch("services.auth_state_factory.RedisAuthStateStore", DummyStore):
            store = create_auth_state_store(
                "redis",
                redis_url="redis://example:6379/0",
                redis_prefix="aicli:test",
                redis_lock_ttl_ms=12345,
            )
        self.assertEqual(store.redis_url, "redis://example:6379/0")
        self.assertEqual(store.key_prefix, "aicli:test")
        self.assertEqual(store.lock_ttl_ms, 12345)


if __name__ == "__main__":
    unittest.main()
