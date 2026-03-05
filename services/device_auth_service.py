import hashlib
import json
import secrets
import string
import threading
import time
from contextlib import contextmanager
from typing import Dict, Optional, Set

from config import (
    ACCESS_TOKEN_TTL_SECONDS,
    AUTH_STATE_BACKEND,
    AUTH_STATE_DB_PATH,
    AUTH_STATE_PERSIST,
    AUTH_STATE_REDIS_LOCK_TTL_MS,
    AUTH_STATE_REDIS_PREFIX,
    AUTH_STATE_REDIS_URL,
    AUTH_USERS_JSON,
    DEVICE_AUTH_ENABLED,
    DEVICE_CODE_POLL_INTERVAL_SECONDS,
    DEVICE_CODE_TTL_SECONDS,
    REFRESH_TOKEN_TTL_SECONDS,
)
from services.auth_service import AuthContext, AuthError
from services.auth_state_factory import create_auth_state_store


def _now_epoch() -> int:
    return int(time.time())


def _normalize_scopes(raw) -> Set[str]:
    if raw is None:
        return {"read", "write", "agent"}
    if isinstance(raw, str):
        values = [item.strip() for item in raw.split(",")]
    elif isinstance(raw, (list, tuple, set)):
        values = [str(item).strip() for item in raw]
    else:
        return {"read", "write", "agent"}
    scopes = {item for item in values if item}
    return scopes or {"read", "write", "agent"}


def _parse_users(raw_json: str) -> Dict[str, dict]:
    if not raw_json or not raw_json.strip():
        return {}
    try:
        payload = json.loads(raw_json)
    except Exception:
        return {}

    users: Dict[str, dict] = {}
    if not isinstance(payload, dict):
        return users

    for username, value in payload.items():
        name = str(username).strip()
        if not name or not isinstance(value, dict):
            continue
        user_id = str(value.get("user_id") or name).strip() or name
        scopes = _normalize_scopes(value.get("scopes"))
        password = value.get("password")
        password_sha256 = value.get("password_sha256")
        if password is None and password_sha256 is None:
            continue
        users[name] = {
            "user_id": user_id,
            "scopes": scopes,
            "password": None if password is None else str(password),
            "password_sha256": None if password_sha256 is None else str(password_sha256).lower(),
        }
    return users


def _random_token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def _user_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    part1 = "".join(secrets.choice(alphabet) for _ in range(4))
    part2 = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"{part1}-{part2}"


class DeviceAuthService:
    def __init__(
        self,
        *,
        persist_enabled: bool = AUTH_STATE_PERSIST,
        state_backend: str = AUTH_STATE_BACKEND,
        state_db_path: str = AUTH_STATE_DB_PATH,
        redis_url: str = AUTH_STATE_REDIS_URL,
        redis_prefix: str = AUTH_STATE_REDIS_PREFIX,
        redis_lock_ttl_ms: int = AUTH_STATE_REDIS_LOCK_TTL_MS,
    ):
        self._lock = threading.Lock()
        self._pending_devices: Dict[str, dict] = {}
        self._user_code_index: Dict[str, str] = {}
        self._access_tokens: Dict[str, dict] = {}
        self._refresh_tokens: Dict[str, dict] = {}
        self._persist_enabled = bool(persist_enabled)
        self._store = None

        if self._persist_enabled:
            try:
                self._store = create_auth_state_store(
                    state_backend,
                    sqlite_path=state_db_path,
                    redis_url=redis_url,
                    redis_prefix=redis_prefix,
                    redis_lock_ttl_ms=redis_lock_ttl_ms,
                )
                self._reload_from_store_locked()
            except Exception:
                self._store = None
                self._persist_enabled = False

    def _reload_from_store_locked(self):
        if not self._store:
            return
        access, refresh, pending = self._store.load_snapshot()
        self._access_tokens = access if isinstance(access, dict) else {}
        self._refresh_tokens = refresh if isinstance(refresh, dict) else {}
        self._pending_devices = pending if isinstance(pending, dict) else {}
        self._user_code_index = {}
        for device_code, record in self._pending_devices.items():
            if not isinstance(record, dict):
                continue
            user_code = str(record.get("user_code", "")).strip()
            if user_code:
                self._user_code_index[user_code] = device_code

    def _persist_locked(self):
        if not self._persist_enabled or not self._store:
            return
        self._store.save_snapshot(
            self._access_tokens,
            self._refresh_tokens,
            self._pending_devices,
        )

    @contextmanager
    def _state_lock(self):
        with self._lock:
            if self._persist_enabled and self._store:
                with self._store.lock():
                    self._reload_from_store_locked()
                    yield
            else:
                yield

    def _users(self) -> Dict[str, dict]:
        return _parse_users(AUTH_USERS_JSON)

    def _cleanup_locked(self) -> bool:
        now = _now_epoch()
        changed = False

        expired_devices = [
            device_code
            for device_code, record in self._pending_devices.items()
            if record.get("expires_at", 0) <= now
        ]
        for device_code in expired_devices:
            user_code = self._pending_devices[device_code].get("user_code")
            if user_code:
                self._user_code_index.pop(user_code, None)
            self._pending_devices.pop(device_code, None)
            changed = True

        expired_access = [
            token
            for token, record in self._access_tokens.items()
            if record.get("expires_at", 0) <= now
        ]
        for token in expired_access:
            self._access_tokens.pop(token, None)
            changed = True

        expired_refresh = [
            token
            for token, record in self._refresh_tokens.items()
            if record.get("expires_at", 0) <= now
        ]
        for token in expired_refresh:
            self._refresh_tokens.pop(token, None)
            changed = True

        return changed

    def _verify_user_credentials(self, username: str, password: str) -> Optional[dict]:
        users = self._users()
        user = users.get(username)
        if not user:
            return None
        raw_password = user.get("password")
        hashed = user.get("password_sha256")
        if raw_password is not None and str(raw_password) == password:
            return user
        if hashed:
            digest = hashlib.sha256(password.encode("utf-8")).hexdigest().lower()
            if digest == hashed:
                return user
        return None

    def is_enabled(self) -> bool:
        return bool(DEVICE_AUTH_ENABLED and self._users())

    def _require_enabled(self):
        if not DEVICE_AUTH_ENABLED:
            raise AuthError(status_code=403, message="Device authentication is disabled.")
        if not self._users():
            raise AuthError(
                status_code=503,
                message=(
                    "No auth users configured. Set AI_CLI_AUTH_USERS_JSON "
                    "to enable device/password login."
                ),
            )

    def issue_tokens(self, user_id: str, scopes: Set[str]) -> dict:
        now = _now_epoch()
        access_token = _random_token("atk")
        refresh_token = _random_token("rtk")
        access_expires_at = now + max(60, ACCESS_TOKEN_TTL_SECONDS)
        refresh_expires_at = now + max(300, REFRESH_TOKEN_TTL_SECONDS)

        with self._state_lock():
            self._cleanup_locked()
            self._access_tokens[access_token] = {
                "user_id": user_id,
                "scopes": set(scopes),
                "expires_at": access_expires_at,
                "refresh_token": refresh_token,
                "issued_at": now,
            }
            self._refresh_tokens[refresh_token] = {
                "user_id": user_id,
                "scopes": set(scopes),
                "expires_at": refresh_expires_at,
                "issued_at": now,
            }
            self._persist_locked()

        return {
            "ok": True,
            "token_type": "bearer",
            "access_token": access_token,
            "expires_in": max(1, access_expires_at - now),
            "access_expires_at": access_expires_at,
            "refresh_token": refresh_token,
            "refresh_expires_at": refresh_expires_at,
            "user": {"id": user_id, "scopes": sorted(scopes)},
        }

    def login_password(self, username: str, password: str) -> dict:
        self._require_enabled()
        user = self._verify_user_credentials(username.strip(), password)
        if not user:
            raise AuthError(status_code=401, message="Invalid username or password.")
        return self.issue_tokens(user_id=user["user_id"], scopes=set(user["scopes"]))

    def start_device_authorization(self, client_name: str, base_url: str) -> dict:
        self._require_enabled()
        now = _now_epoch()
        expires_at = now + max(60, DEVICE_CODE_TTL_SECONDS)
        interval = max(1, DEVICE_CODE_POLL_INTERVAL_SECONDS)
        device_code = _random_token("dev")
        user_code = _user_code()

        with self._state_lock():
            self._cleanup_locked()
            self._pending_devices[device_code] = {
                "device_code": device_code,
                "user_code": user_code,
                "client_name": client_name or "aicli",
                "created_at": now,
                "expires_at": expires_at,
                "interval": interval,
                "last_poll_at": 0,
                "approved_user_id": None,
                "approved_scopes": None,
                "consumed": False,
            }
            self._user_code_index[user_code] = device_code
            self._persist_locked()

        root = (base_url or "").rstrip("/")
        verification_uri = f"{root}/auth/device/verify" if root else "/auth/device/verify"
        return {
            "ok": True,
            "device_code": device_code,
            "user_code": user_code,
            "verification_uri": verification_uri,
            "verification_uri_complete": f"{verification_uri}?user_code={user_code}",
            "expires_in": max(1, expires_at - now),
            "interval": interval,
        }

    def approve_device_code(self, user_code: str, username: str, password: str) -> dict:
        self._require_enabled()
        normalized_code = (user_code or "").strip().upper()
        if not normalized_code:
            raise AuthError(status_code=400, message="user_code is required.")

        user = self._verify_user_credentials((username or "").strip(), password)
        if not user:
            raise AuthError(status_code=401, message="Invalid username or password.")

        with self._state_lock():
            changed = self._cleanup_locked()
            device_code = self._user_code_index.get(normalized_code)
            if not device_code:
                if changed:
                    self._persist_locked()
                raise AuthError(status_code=400, message="Invalid or expired user_code.")
            record = self._pending_devices.get(device_code)
            if not record:
                if changed:
                    self._persist_locked()
                raise AuthError(status_code=400, message="Invalid or expired user_code.")
            if record.get("consumed"):
                if changed:
                    self._persist_locked()
                raise AuthError(status_code=400, message="Device code already consumed.")
            record["approved_user_id"] = user["user_id"]
            record["approved_scopes"] = set(user["scopes"])
            self._persist_locked()

        return {"ok": True, "status": "approved", "user_code": normalized_code}

    def poll_device_token(self, device_code: str) -> dict:
        self._require_enabled()
        now = _now_epoch()
        code = (device_code or "").strip()
        if not code:
            raise AuthError(status_code=400, message="device_code is required.")

        with self._state_lock():
            changed = self._cleanup_locked()
            record = self._pending_devices.get(code)
            if not record:
                if changed:
                    self._persist_locked()
                raise AuthError(status_code=400, message="Invalid or expired device_code.")

            interval = int(record.get("interval", 1))
            last_poll = int(record.get("last_poll_at", 0))
            if last_poll and now - last_poll < interval:
                if changed:
                    self._persist_locked()
                return {
                    "ok": False,
                    "status": "slow_down",
                    "interval": interval,
                    "error": "slow_down",
                }
            record["last_poll_at"] = now

            if not record.get("approved_user_id"):
                self._persist_locked()
                return {
                    "ok": False,
                    "status": "authorization_pending",
                    "interval": interval,
                    "error": "authorization_pending",
                }

            if record.get("consumed"):
                self._persist_locked()
                raise AuthError(status_code=400, message="Device code already consumed.")

            user_id = str(record["approved_user_id"])
            scopes = set(record.get("approved_scopes") or {"read"})
            record["consumed"] = True
            user_code = record.get("user_code")
            if user_code:
                self._user_code_index.pop(user_code, None)
            self._pending_devices.pop(code, None)
            self._persist_locked()

        return self.issue_tokens(user_id=user_id, scopes=scopes)

    def authenticate_access_token(self, token: str) -> AuthContext:
        value = (token or "").strip()
        if not value:
            raise AuthError(status_code=401, message="Missing bearer token.")

        with self._state_lock():
            changed = self._cleanup_locked()
            if changed:
                self._persist_locked()
            record = self._access_tokens.get(value)
            if not record:
                raise AuthError(status_code=401, message="Invalid or expired bearer token.")
            return AuthContext(
                user_id=str(record["user_id"]),
                scopes=set(record.get("scopes") or {"read"}),
                token_source="bearer_access_token",
            )

    def refresh_access_token(self, refresh_token: str) -> dict:
        token = (refresh_token or "").strip()
        if not token:
            raise AuthError(status_code=400, message="refresh_token is required.")

        with self._state_lock():
            changed = self._cleanup_locked()
            record = self._refresh_tokens.get(token)
            if not record:
                if changed:
                    self._persist_locked()
                raise AuthError(status_code=401, message="Invalid or expired refresh token.")
            user_id = str(record["user_id"])
            scopes = set(record.get("scopes") or {"read"})
            self._refresh_tokens.pop(token, None)
            self._persist_locked()

        return self.issue_tokens(user_id=user_id, scopes=scopes)

    def revoke_refresh_token(self, refresh_token: str) -> dict:
        token = (refresh_token or "").strip()
        if not token:
            raise AuthError(status_code=400, message="refresh_token is required.")
        with self._state_lock():
            changed = self._cleanup_locked()
            removed = self._refresh_tokens.pop(token, None)
            if removed is not None:
                changed = True
            linked = [
                access
                for access, record in self._access_tokens.items()
                if record.get("refresh_token") == token
            ]
            for access in linked:
                self._access_tokens.pop(access, None)
                changed = True
            if changed:
                self._persist_locked()
        return {"ok": True}


device_auth_service = DeviceAuthService()
