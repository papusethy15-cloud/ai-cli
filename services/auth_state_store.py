import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Tuple


class AuthStateStore:
    def __init__(self, db_path: str):
        self._db_path = os.path.abspath(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        return sqlite3.connect(self._db_path, timeout=10)

    @contextmanager
    def lock(self):
        # SQLite backend is normally single-host. Thread-level locking is handled
        # by service layer, so this is a no-op context for interface consistency.
        yield

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kv_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _dump_json(self, payload) -> str:
        def _default(obj):
            if isinstance(obj, set):
                return sorted(obj)
            raise TypeError(f"Unsupported type for JSON serialization: {type(obj)!r}")

        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), default=_default)

    def _load_json(self, raw: str):
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def load_snapshot(self) -> Tuple[Dict[str, dict], Dict[str, dict], Dict[str, dict]]:
        with self._connect() as conn:
            rows = dict(conn.execute("SELECT key, value FROM kv_state").fetchall())

        access_tokens = self._load_json(rows.get("access_tokens", "{}"))
        refresh_tokens = self._load_json(rows.get("refresh_tokens", "{}"))
        pending_devices = self._load_json(rows.get("pending_devices", "{}"))

        if not isinstance(access_tokens, dict):
            access_tokens = {}
        if not isinstance(refresh_tokens, dict):
            refresh_tokens = {}
        if not isinstance(pending_devices, dict):
            pending_devices = {}

        for record in access_tokens.values():
            if isinstance(record, dict):
                scopes = record.get("scopes")
                if isinstance(scopes, list):
                    record["scopes"] = set(scopes)

        for record in refresh_tokens.values():
            if isinstance(record, dict):
                scopes = record.get("scopes")
                if isinstance(scopes, list):
                    record["scopes"] = set(scopes)

        for record in pending_devices.values():
            if isinstance(record, dict):
                scopes = record.get("approved_scopes")
                if isinstance(scopes, list):
                    record["approved_scopes"] = set(scopes)

        return access_tokens, refresh_tokens, pending_devices

    def save_snapshot(
        self,
        access_tokens: Dict[str, dict],
        refresh_tokens: Dict[str, dict],
        pending_devices: Dict[str, dict],
    ):
        payloads = {
            "access_tokens": self._dump_json(access_tokens),
            "refresh_tokens": self._dump_json(refresh_tokens),
            "pending_devices": self._dump_json(pending_devices),
        }

        with self._connect() as conn:
            for key, value in payloads.items():
                conn.execute(
                    "INSERT INTO kv_state(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )
            conn.commit()
