import json

import requests

from config import API_REQUEST_TIMEOUT_SECONDS, REMOTE_API_BASE_URL, REMOTE_API_KEY


def _request(method, endpoint, payload=None, base_url=None, api_key=None):
    url = (base_url or REMOTE_API_BASE_URL).rstrip("/") + endpoint
    headers = {"Content-Type": "application/json"}
    token = api_key if api_key is not None else REMOTE_API_KEY
    if token:
        headers["x-api-key"] = token

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


def remote_health(base_url=None, api_key=None):
    result = _request("GET", "/health", base_url=base_url, api_key=api_key)
    if result is not None:
        print(json.dumps(result, indent=2))


def remote_analyze(path, use_llm=True, refresh=False, base_url=None, api_key=None):
    result = _request(
        "POST",
        "/analyze",
        payload={"path": path, "use_llm": use_llm, "refresh": refresh},
        base_url=base_url,
        api_key=api_key,
    )
    if result is not None:
        print(json.dumps(result, indent=2))


def remote_fix_file(path, apply=False, refresh=False, base_url=None, api_key=None):
    result = _request(
        "POST",
        "/fix/file",
        payload={"path": path, "apply": apply, "refresh": refresh},
        base_url=base_url,
        api_key=api_key,
    )
    if result is not None:
        print(json.dumps(result, indent=2))


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
        print(json.dumps(result, indent=2))


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
        print(json.dumps(result, indent=2))


def remote_agent_run(
    goal,
    max_steps=None,
    async_mode=False,
    base_url=None,
    api_key=None,
):
    payload = {"goal": goal, "async_mode": async_mode}
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
        print(json.dumps(result, indent=2))


def remote_job(job_id, base_url=None, api_key=None):
    result = _request("GET", f"/jobs/{job_id}", base_url=base_url, api_key=api_key)
    if result is not None:
        print(json.dumps(result, indent=2))


def remote_job_events(job_id, since=0, max_items=100, base_url=None, api_key=None):
    result = _request(
        "GET",
        f"/jobs/{job_id}/events?since={since}&max_items={max_items}",
        base_url=base_url,
        api_key=api_key,
    )
    if result is not None:
        print(json.dumps(result, indent=2))


def remote_job_stream(job_id, since=0, base_url=None, api_key=None):
    url = (base_url or REMOTE_API_BASE_URL).rstrip("/") + f"/jobs/{job_id}/stream?since={since}"
    headers = {}
    token = api_key if api_key is not None else REMOTE_API_KEY
    if token:
        headers["x-api-key"] = token

    try:
        with requests.get(url, headers=headers, stream=True, timeout=API_REQUEST_TIMEOUT_SECONDS) as response:
            if response.status_code >= 400:
                print(f"[Remote Error] HTTP {response.status_code}: {response.text}")
                return
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                raw = line[6:]
                try:
                    payload = json.loads(raw)
                    print(json.dumps(payload, indent=2))
                except ValueError:
                    print(raw)
    except requests.Timeout:
        print(f"[Remote Error] Stream timed out: {url}")
    except requests.RequestException as e:
        print(f"[Remote Error] Stream failed: {e}")
