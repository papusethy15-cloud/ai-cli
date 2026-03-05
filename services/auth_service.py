import json
from dataclasses import dataclass
from typing import Dict, Iterable, Set

from config import ALLOW_NO_AUTH, API_KEY, AUTH_TOKENS_JSON


class AuthError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    scopes: Set[str]
    token_source: str


def _normalize_scopes(raw) -> Set[str]:
    if raw is None:
        return {"*"}
    if isinstance(raw, str):
        items: Iterable[str] = [item.strip() for item in raw.split(",")]
    elif isinstance(raw, (list, tuple, set)):
        items = [str(item).strip() for item in raw]
    else:
        return {"*"}
    scopes = {item for item in items if item}
    return scopes or {"*"}


def _parse_json_tokens(raw: str) -> Dict[str, AuthContext]:
    if not raw or not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        return {}

    tokens: Dict[str, AuthContext] = {}
    if isinstance(payload, dict):
        for token, value in payload.items():
            token_value = str(token).strip()
            if not token_value:
                continue
            if isinstance(value, str):
                tokens[token_value] = AuthContext(
                    user_id=value.strip() or "user",
                    scopes={"*"},
                    token_source="json",
                )
                continue
            if not isinstance(value, dict):
                continue
            user_id = str(value.get("user_id") or value.get("user") or "user").strip()
            scopes = _normalize_scopes(value.get("scopes"))
            tokens[token_value] = AuthContext(
                user_id=user_id or "user",
                scopes=scopes,
                token_source="json",
            )
    return tokens


def load_token_registry() -> Dict[str, AuthContext]:
    tokens = _parse_json_tokens(AUTH_TOKENS_JSON)
    if API_KEY:
        # The simple shared key remains supported as an admin/full-access token.
        tokens[API_KEY] = AuthContext(
            user_id="admin",
            scopes={"*"},
            token_source="env_api_key",
        )
    return tokens


def authenticate_api_key(token: str | None) -> AuthContext:
    tokens = load_token_registry()
    if tokens:
        if not token:
            raise AuthError(status_code=401, message="API key is required.")
        context = tokens.get(token)
        if not context:
            raise AuthError(status_code=401, message="Invalid API key.")
        return context

    if ALLOW_NO_AUTH:
        return AuthContext(user_id="anonymous", scopes={"*"}, token_source="allow_no_auth")

    raise AuthError(
        status_code=503,
        message=(
            "API authentication is not configured. "
            "Set AI_CLI_API_KEY or AI_CLI_AUTH_TOKENS_JSON "
            "or explicitly enable AI_CLI_ALLOW_NO_AUTH=true for local dev."
        ),
    )


def has_scope(context: AuthContext, required_scope: str) -> bool:
    required = (required_scope or "").strip().lower()
    if not required:
        return True
    scopes = {scope.strip().lower() for scope in context.scopes}
    return "*" in scopes or required in scopes


def whoami_payload(context: AuthContext) -> dict:
    return {
        "ok": True,
        "user": {
            "id": context.user_id,
            "scopes": sorted(context.scopes),
            "token_source": context.token_source,
        },
    }
