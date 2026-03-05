import getpass
import json
import os
import time

import requests

from config import API_REQUEST_TIMEOUT_SECONDS, REMOTE_API_BASE_URL, REMOTE_API_KEY
from utils.cli_config import (
    CLI_CONFIG_FILE,
    clear_saved_remote,
    clear_saved_remote_tokens,
    load_cli_config,
    masked_secret,
    set_saved_remote,
    set_saved_remote_tokens,
)


def _print_json(payload):
    print(json.dumps(payload, indent=2))


def _mask_token(token):
    return masked_secret(token)


def _effective_remote(base_url=None, api_key=None):
    config = load_cli_config()
    remote = config.get("remote", {})

    saved_url = str(remote.get("base_url", "")).strip()
    saved_key = str(remote.get("api_key", "")).strip()
    saved_access = str(remote.get("access_token", "")).strip()
    saved_refresh = str(remote.get("refresh_token", "")).strip()
    saved_expires = int(remote.get("access_expires_at", 0) or 0)
    saved_user_id = str(remote.get("auth_user_id", "")).strip()
    saved_scopes = list(remote.get("auth_scopes", []))

    env_url = os.getenv("AI_CLI_REMOTE_URL", "").strip()
    env_key = os.getenv("AI_CLI_REMOTE_API_KEY", "").strip()

    final_url = str(base_url or env_url or saved_url or REMOTE_API_BASE_URL).strip()
    if api_key is not None:
        final_api_key = str(api_key).strip()
    else:
        final_api_key = str(env_key or saved_key or REMOTE_API_KEY).strip()

    return {
        "base_url": final_url,
        "api_key": final_api_key,
        "access_token": saved_access,
        "refresh_token": saved_refresh,
        "access_expires_at": saved_expires,
        "auth_user_id": saved_user_id,
        "auth_scopes": saved_scopes,
    }


def _build_headers(auth, include_content_type=True):
    headers = {}
    if include_content_type:
        headers["Content-Type"] = "application/json"
    access_token = auth.get("access_token")
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    elif auth.get("api_key"):
        headers["x-api-key"] = auth["api_key"]
    return headers


def _save_token_payload(payload, base_url=None):
    access_token = str(payload.get("access_token", "")).strip()
    refresh_token = str(payload.get("refresh_token", "")).strip()
    access_expires_at = int(payload.get("access_expires_at", 0) or 0)
    expires_in = int(payload.get("expires_in", 0) or 0)
    if access_expires_at <= 0 and expires_in > 0:
        access_expires_at = int(time.time()) + expires_in
    user = payload.get("user") or {}
    set_saved_remote_tokens(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_expires_at,
        auth_user_id=str(user.get("id", "")).strip(),
        auth_scopes=list(user.get("scopes", [])),
    )
    if base_url:
        set_saved_remote(base_url=base_url, api_key=None)


def _request_no_auth(method, endpoint, payload=None, base_url=None):
    resolved_base_url = (base_url or REMOTE_API_BASE_URL).strip()
    if not resolved_base_url:
        print("[Remote Error] Remote base URL is not configured.")
        return None

    url = resolved_base_url.rstrip("/") + endpoint
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.request(
            method=method,
            url=url,
            json=payload,
            headers=headers,
            timeout=API_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        print(f"[Remote Error] Request timed out: {url}")
        return None
    except requests.RequestException as e:
        print(f"[Remote Error] Request failed: {e}")
        return None

    try:
        body = response.json()
    except ValueError:
        print(f"[Remote Error] Non-JSON response ({response.status_code}): {response.text}")
        return None

    if response.status_code >= 400:
        print(f"[Remote Error] HTTP {response.status_code}: {body}")
        return None
    return body


def _refresh_if_possible(base_url, refresh_token):
    if not refresh_token:
        return False
    result = _request_no_auth(
        "POST",
        "/auth/refresh",
        payload={"refresh_token": refresh_token},
        base_url=base_url,
    )
    if not result or not result.get("access_token"):
        clear_saved_remote_tokens()
        return False
    _save_token_payload(result, base_url=base_url)
    return True


def _request(method, endpoint, payload=None, base_url=None, api_key=None, _retry_on_401=True):
    auth = _effective_remote(base_url=base_url, api_key=api_key)
    if api_key is not None:
        # Explicit API key should take precedence over saved bearer session.
        auth["access_token"] = ""
        auth["refresh_token"] = ""
    resolved_base_url = auth["base_url"]
    if not resolved_base_url:
        print("[Remote Error] Remote base URL is not configured.")
        return None

    url = resolved_base_url.rstrip("/") + endpoint
    headers = _build_headers(auth)
    try:
        response = requests.request(
            method=method,
            url=url,
            json=payload,
            headers=headers,
            timeout=API_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        print(f"[Remote Error] Request timed out: {url}")
        return None
    except requests.RequestException as e:
        print(f"[Remote Error] Request failed: {e}")
        return None

    try:
        body = response.json()
    except ValueError:
        print(f"[Remote Error] Non-JSON response ({response.status_code}): {response.text}")
        return None

    if response.status_code == 401 and _retry_on_401:
        refreshed = _refresh_if_possible(
            base_url=resolved_base_url,
            refresh_token=auth.get("refresh_token"),
        )
        if refreshed:
            return _request(
                method,
                endpoint,
                payload=payload,
                base_url=resolved_base_url,
                api_key=api_key,
                _retry_on_401=False,
            )

    if response.status_code >= 400:
        print(f"[Remote Error] HTTP {response.status_code}: {body}")
        return None
    return body


def remote_config_show(base_url=None, api_key=None):
    active = _effective_remote(base_url=base_url, api_key=api_key)
    config = load_cli_config()
    remote = config.get("remote", {})
    _print_json(
        {
            "ok": True,
            "config_file": str(CLI_CONFIG_FILE),
            "saved": {
                "base_url": remote.get("base_url", "") or "(not set)",
                "api_key": _mask_token(str(remote.get("api_key", ""))),
                "access_token": _mask_token(str(remote.get("access_token", ""))),
                "refresh_token": _mask_token(str(remote.get("refresh_token", ""))),
                "access_expires_at": int(remote.get("access_expires_at", 0) or 0),
                "auth_user_id": str(remote.get("auth_user_id", "")),
                "auth_scopes": list(remote.get("auth_scopes", [])),
            },
            "active": {
                "base_url": active.get("base_url") or "(not set)",
                "api_key": _mask_token(active.get("api_key", "")),
                "access_token": _mask_token(active.get("access_token", "")),
                "refresh_token": _mask_token(active.get("refresh_token", "")),
                "auth_user_id": active.get("auth_user_id", ""),
                "auth_scopes": list(active.get("auth_scopes", [])),
            },
        }
    )


def remote_login(base_url=None, api_key=None, save=True):
    candidate_url = (base_url or "").strip() or input("Remote base URL > ").strip()
    candidate_key = (api_key or "").strip() or getpass.getpass("Remote API key > ").strip()
    if not candidate_url:
        print("[Remote Error] Base URL is required.")
        return
    if not candidate_key:
        print("[Remote Error] API key is required.")
        return

    result = _request(
        "GET",
        "/auth/whoami",
        base_url=candidate_url,
        api_key=candidate_key,
    )
    if result is None:
        print("Login failed. Check URL and API key.")
        return

    if save:
        set_saved_remote(base_url=candidate_url, api_key=candidate_key)
        print(f"Saved remote config to {CLI_CONFIG_FILE}")
    print("Login successful.")
    _print_json(result)


def remote_password_login(base_url=None, username=None, password=None, save=True):
    candidate_url = (base_url or "").strip() or input("Remote base URL > ").strip()
    candidate_user = (username or "").strip() or input("Username > ").strip()
    candidate_password = (password or "").strip() or getpass.getpass("Password > ").strip()

    result = _request_no_auth(
        "POST",
        "/auth/login",
        payload={"username": candidate_user, "password": candidate_password},
        base_url=candidate_url,
    )
    if result is None:
        print("Password login failed.")
        return
    if not result.get("access_token"):
        print("Password login failed: no access token returned.")
        return

    if save:
        set_saved_remote(base_url=candidate_url, api_key=None)
        _save_token_payload(result, base_url=candidate_url)
        print(f"Saved token session to {CLI_CONFIG_FILE}")
    print("Password login successful.")
    _print_json({"ok": True, "user": result.get("user", {}), "expires_in": result.get("expires_in")})


def remote_device_login(
    base_url=None,
    client_name="aicli",
    username=None,
    password=None,
    poll_timeout=180,
    save=True,
):
    candidate_url = (base_url or "").strip() or input("Remote base URL > ").strip()
    start = _request_no_auth(
        "POST",
        "/auth/device/start",
        payload={"client_name": client_name},
        base_url=candidate_url,
    )
    if start is None:
        print("Device login start failed.")
        return

    user_code = start.get("user_code")
    device_code = start.get("device_code")
    interval = int(start.get("interval", 3) or 3)
    if not user_code or not device_code:
        print("Device login failed: invalid response from server.")
        return

    print("Device authorization started.")
    print(f"User code: {user_code}")
    print(f"Verify at: {start.get('verification_uri')}")

    candidate_user = (username or "").strip() or input("Username > ").strip()
    candidate_password = (password or "").strip() or getpass.getpass("Password > ").strip()
    verify = _request_no_auth(
        "POST",
        "/auth/device/verify",
        payload={
            "user_code": user_code,
            "username": candidate_user,
            "password": candidate_password,
        },
        base_url=candidate_url,
    )
    if verify is None:
        print("Device verification failed.")
        return

    started = int(time.time())
    while True:
        token_result = _request_no_auth(
            "POST",
            "/auth/device/token",
            payload={"device_code": device_code},
            base_url=candidate_url,
        )
        if token_result is None:
            print("Device token polling failed.")
            return

        if token_result.get("ok") and token_result.get("access_token"):
            if save:
                set_saved_remote(base_url=candidate_url, api_key=None)
                _save_token_payload(token_result, base_url=candidate_url)
                print(f"Saved token session to {CLI_CONFIG_FILE}")
            print("Device login successful.")
            _print_json(
                {
                    "ok": True,
                    "user": token_result.get("user", {}),
                    "expires_in": token_result.get("expires_in"),
                }
            )
            return

        status = str(token_result.get("status", "authorization_pending"))
        if status in {"authorization_pending", "slow_down"}:
            if int(time.time()) - started > max(30, int(poll_timeout)):
                print("Device login timed out.")
                return
            sleep_for = interval + (1 if status == "slow_down" else 0)
            time.sleep(max(1, sleep_for))
            continue

        print(f"Device login failed: {token_result}")
        return


def remote_token_refresh(base_url=None):
    auth = _effective_remote(base_url=base_url, api_key=None)
    if not auth.get("refresh_token"):
        print("No refresh token saved. Run remote-device-login or remote-password-login.")
        return
    refreshed = _refresh_if_possible(
        base_url=auth["base_url"],
        refresh_token=auth["refresh_token"],
    )
    if not refreshed:
        print("Token refresh failed.")
        return
    print("Token refresh successful.")


def remote_logout(clear_base_url=False):
    config = load_cli_config()
    refresh_token = str(config.get("remote", {}).get("refresh_token", "")).strip()
    base_url = str(config.get("remote", {}).get("base_url", "")).strip()
    if refresh_token and base_url:
        _request_no_auth(
            "POST",
            "/auth/logout",
            payload={"refresh_token": refresh_token},
            base_url=base_url,
        )
    clear_saved_remote(clear_base_url=clear_base_url)
    print(f"Cleared saved remote credentials in {CLI_CONFIG_FILE}")


def remote_whoami(base_url=None, api_key=None):
    result = _request("GET", "/auth/whoami", base_url=base_url, api_key=api_key)
    if result is not None:
        _print_json(result)


def remote_health(base_url=None, api_key=None):
    result = _request("GET", "/health", base_url=base_url, api_key=api_key)
    if result is not None:
        _print_json(result)


def remote_analyze(path, use_llm=True, refresh=False, base_url=None, api_key=None):
    result = _request(
        "POST",
        "/analyze",
        payload={"path": path, "use_llm": use_llm, "refresh": refresh},
        base_url=base_url,
        api_key=api_key,
    )
    if result is not None:
        _print_json(result)


def remote_fix_file(path, apply=False, refresh=False, base_url=None, api_key=None):
    result = _request(
        "POST",
        "/fix/file",
        payload={"path": path, "apply": apply, "refresh": refresh},
        base_url=base_url,
        api_key=api_key,
    )
    if result is not None:
        _print_json(result)


def remote_fix_project(
    path,
    apply=False,
    use_llm=False,
    refresh=False,
    max_files=20,
    base_url=None,
    api_key=None,
):
    result = _request(
        "POST",
        "/fix/project",
        payload={
            "path": path,
            "apply": apply,
            "use_llm": use_llm,
            "refresh": refresh,
            "max_files": max_files,
        },
        base_url=base_url,
        api_key=api_key,
    )
    if result is not None:
        _print_json(result)


def remote_memory(action="stats", limit=20, yes=False, base_url=None, api_key=None):
    action = action.lower().strip()
    if action == "stats":
        result = _request("GET", "/memory/stats", base_url=base_url, api_key=api_key)
    elif action == "show":
        result = _request(
            "GET",
            f"/memory/show?limit={limit}",
            base_url=base_url,
            api_key=api_key,
        )
    elif action == "clear":
        result = _request(
            "DELETE",
            "/memory",
            payload={"yes": yes},
            base_url=base_url,
            api_key=api_key,
        )
    else:
        print("Unknown action. Use: stats, show, clear")
        return

    if result is not None:
        _print_json(result)


def remote_agent_run(
    goal,
    max_steps=None,
    async_mode=False,
    workspace_path=".",
    base_url=None,
    api_key=None,
):
    payload = {"goal": goal, "async_mode": async_mode, "workspace_path": workspace_path}
    if max_steps is not None:
        payload["max_steps"] = max_steps

    result = _request(
        "POST",
        "/agent/run",
        payload=payload,
        base_url=base_url,
        api_key=api_key,
    )
    if result is not None:
        _print_json(result)


def remote_job(job_id, base_url=None, api_key=None):
    result = _request("GET", f"/jobs/{job_id}", base_url=base_url, api_key=api_key)
    if result is not None:
        _print_json(result)


def remote_job_events(job_id, since=0, max_items=100, base_url=None, api_key=None):
    result = _request(
        "GET",
        f"/jobs/{job_id}/events?since={since}&max_items={max_items}",
        base_url=base_url,
        api_key=api_key,
    )
    if result is not None:
        _print_json(result)


def remote_job_stream(job_id, since=0, base_url=None, api_key=None):
    auth = _effective_remote(base_url=base_url, api_key=api_key)
    if not auth["base_url"]:
        print("[Remote Error] Remote base URL is not configured.")
        return

    def _stream_with_auth(auth_values):
        url = auth_values["base_url"].rstrip("/") + f"/jobs/{job_id}/stream?since={since}"
        headers = _build_headers(auth_values, include_content_type=False)
        with requests.get(url, headers=headers, stream=True, timeout=API_REQUEST_TIMEOUT_SECONDS) as response:
            if response.status_code >= 400:
                return response.status_code, response.text
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                raw = line[6:]
                try:
                    payload = json.loads(raw)
                    _print_json(payload)
                except ValueError:
                    print(raw)
            return 200, ""

    try:
        status, message = _stream_with_auth(auth)
        if status == 401 and auth.get("refresh_token"):
            refreshed = _refresh_if_possible(
                base_url=auth["base_url"],
                refresh_token=auth["refresh_token"],
            )
            if refreshed:
                auth = _effective_remote(base_url=auth["base_url"], api_key=api_key)
                status, message = _stream_with_auth(auth)
        if status >= 400:
            print(f"[Remote Error] HTTP {status}: {message}")
    except requests.Timeout:
        print("[Remote Error] Stream timed out.")
    except requests.RequestException as e:
        print(f"[Remote Error] Stream failed: {e}")
