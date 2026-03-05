import json
import os
import tempfile
from pathlib import Path
from typing import Tuple


CLI_HOME = Path(os.getenv("AI_CLI_HOME", Path.home() / ".ai-cli"))
CLI_CONFIG_FILE = CLI_HOME / "config.json"


def _empty_config() -> dict:
    return {
        "version": 1,
        "remote": {
            "base_url": "",
            "api_key": "",
            "access_token": "",
            "refresh_token": "",
            "access_expires_at": 0,
            "auth_user_id": "",
            "auth_scopes": [],
        },
    }


def load_cli_config() -> dict:
    if not CLI_CONFIG_FILE.exists():
        return _empty_config()
    try:
        with CLI_CONFIG_FILE.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return _empty_config()
    if not isinstance(payload, dict):
        return _empty_config()
    payload.setdefault("version", 1)
    payload.setdefault("remote", {})
    if not isinstance(payload["remote"], dict):
        payload["remote"] = {}
    payload["remote"].setdefault("base_url", "")
    payload["remote"].setdefault("api_key", "")
    payload["remote"].setdefault("access_token", "")
    payload["remote"].setdefault("refresh_token", "")
    payload["remote"].setdefault("access_expires_at", 0)
    payload["remote"].setdefault("auth_user_id", "")
    payload["remote"].setdefault("auth_scopes", [])
    return payload


def save_cli_config(config: dict) -> None:
    payload = config if isinstance(config, dict) else _empty_config()
    payload.setdefault("version", 1)
    payload.setdefault("remote", {})
    payload["remote"].setdefault("base_url", "")
    payload["remote"].setdefault("api_key", "")
    payload["remote"].setdefault("access_token", "")
    payload["remote"].setdefault("refresh_token", "")
    payload["remote"].setdefault("access_expires_at", 0)
    payload["remote"].setdefault("auth_user_id", "")
    payload["remote"].setdefault("auth_scopes", [])

    CLI_HOME.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=str(CLI_HOME),
    ) as tmp:
        json.dump(payload, tmp, indent=2, ensure_ascii=True)
        tmp_path = Path(tmp.name)
    tmp_path.replace(CLI_CONFIG_FILE)


def get_saved_remote() -> Tuple[str, str]:
    config = load_cli_config()
    remote = config.get("remote", {})
    return str(remote.get("base_url", "")).strip(), str(remote.get("api_key", "")).strip()


def set_saved_remote(base_url: str | None = None, api_key: str | None = None) -> dict:
    config = load_cli_config()
    remote = config.setdefault("remote", {})
    if base_url is not None:
        remote["base_url"] = str(base_url).strip()
    if api_key is not None:
        remote["api_key"] = str(api_key).strip()
    save_cli_config(config)
    return config


def clear_saved_remote(clear_base_url: bool = False) -> dict:
    config = load_cli_config()
    remote = config.setdefault("remote", {})
    remote["api_key"] = ""
    remote["access_token"] = ""
    remote["refresh_token"] = ""
    remote["access_expires_at"] = 0
    remote["auth_user_id"] = ""
    remote["auth_scopes"] = []
    if clear_base_url:
        remote["base_url"] = ""
    save_cli_config(config)
    return config


def set_saved_remote_tokens(
    *,
    access_token: str,
    refresh_token: str,
    access_expires_at: int,
    auth_user_id: str,
    auth_scopes: list[str],
) -> dict:
    config = load_cli_config()
    remote = config.setdefault("remote", {})
    remote["access_token"] = str(access_token).strip()
    remote["refresh_token"] = str(refresh_token).strip()
    remote["access_expires_at"] = int(access_expires_at or 0)
    remote["auth_user_id"] = str(auth_user_id).strip()
    remote["auth_scopes"] = list(auth_scopes or [])
    save_cli_config(config)
    return config


def clear_saved_remote_tokens() -> dict:
    config = load_cli_config()
    remote = config.setdefault("remote", {})
    remote["access_token"] = ""
    remote["refresh_token"] = ""
    remote["access_expires_at"] = 0
    remote["auth_user_id"] = ""
    remote["auth_scopes"] = []
    save_cli_config(config)
    return config


def masked_secret(value: str) -> str:
    if not value:
        return "(not set)"
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}...{value[-3:]}"
