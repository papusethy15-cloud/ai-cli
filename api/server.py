import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import time
from typing import Any, Dict, List, Optional

from config import (
    API_HOST,
    API_PORT,
    MAX_CONCURRENT_JOBS,
    MAX_JOB_EVENTS,
    MAX_JOB_HISTORY,
    WORKSPACE_ROOT,
)
from services.auth_service import (
    AuthContext,
    AuthError,
    authenticate_api_key,
    has_scope,
    whoami_payload,
)
from services.agent_service import run_agent_goal
from services.device_auth_service import device_auth_service
from services.analyze_service import run_analysis
from services.fix_service import run_file_fix, run_project_fix
from services.memory_service import clear_memory, get_memory_entries, get_memory_stats
from utils.path_guard import WorkspacePathError, resolve_in_workspace

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Request
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel, Field
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "FastAPI dependencies are not installed. Install with: pip install fastapi uvicorn"
    ) from e


class AnalyzeRequest(BaseModel):
    path: str = Field(..., min_length=1)
    use_llm: bool = True
    refresh: bool = False


class FixFileRequest(BaseModel):
    path: str = Field(..., min_length=1)
    apply: bool = False
    refresh: bool = False


class FixProjectRequest(BaseModel):
    path: str = Field(..., min_length=1)
    apply: bool = False
    use_llm: bool = False
    refresh: bool = False
    max_files: int = 20


class MemoryClearRequest(BaseModel):
    yes: bool = False


class AgentRequest(BaseModel):
    goal: str = Field(..., min_length=1)
    workspace_path: Optional[str] = None
    project_details: Optional[Dict[str, str]] = None
    max_steps: Optional[int] = None
    auto_plan: bool = True
    async_mode: bool = False


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class DeviceStartRequest(BaseModel):
    client_name: str = "aicli"


class DeviceVerifyRequest(BaseModel):
    user_code: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class DeviceTokenRequest(BaseModel):
    device_code: str = Field(..., min_length=1)


@dataclass
class JobStore:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _jobs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def create(self, payload: Dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            while len(self._jobs) >= max(1, MAX_JOB_HISTORY):
                oldest_job_id = next(iter(self._jobs))
                del self._jobs[oldest_job_id]
            self._jobs[job_id] = {
                "id": job_id,
                "status": "queued",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "payload": payload,
                "result": None,
                "error": None,
                "events": [],
                "next_seq": 1,
            }
            self._append_event_locked(job_id, {"type": "job_queued"})
        return job_id

    def start(self, job_id: str):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "running"
                self._append_event_locked(job_id, {"type": "job_started"})

    def finish(self, job_id: str, result: Dict[str, Any]):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "done"
                self._jobs[job_id]["result"] = result
                self._append_event_locked(job_id, {"type": "job_finished", "ok": result.get("ok", False)})

    def fail(self, job_id: str, error: str):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["error"] = error
                self._append_event_locked(job_id, {"type": "job_failed", "error": error})

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._jobs.get(job_id)

    def _append_event_locked(self, job_id: str, event: Dict[str, Any]):
        job = self._jobs.get(job_id)
        if not job:
            return
        seq = job["next_seq"]
        job["next_seq"] += 1
        job["events"].append(
            {
                "seq": seq,
                "time": datetime.now(timezone.utc).isoformat(),
                "event": event,
            }
        )
        if len(job["events"]) > max(1, MAX_JOB_EVENTS):
            overflow = len(job["events"]) - max(1, MAX_JOB_EVENTS)
            if overflow > 0:
                job["events"] = job["events"][overflow:]

    def add_event(self, job_id: str, event: Dict[str, Any]):
        with self._lock:
            self._append_event_locked(job_id, event)

    def get_events(self, job_id: str, since: int = 0, max_items: int = 100) -> Optional[List[Dict[str, Any]]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            events = [event for event in job["events"] if event["seq"] > since]
            return events[: max(1, max_items)]


job_store = JobStore()
job_semaphore = threading.Semaphore(max(1, MAX_CONCURRENT_JOBS))


def _auth_guard(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> AuthContext:
    auth_header = authorization if isinstance(authorization, str) else None
    api_key_header = x_api_key if isinstance(x_api_key, str) else None
    bearer_token = None
    if auth_header and auth_header.lower().startswith("bearer "):
        bearer_token = auth_header[7:].strip()
    if bearer_token:
        try:
            return device_auth_service.authenticate_access_token(bearer_token)
        except AuthError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message) from None

    try:
        return authenticate_api_key(api_key_header)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from None


def _require_scope(scope: str):
    def _inner(context: AuthContext = Depends(_auth_guard)) -> AuthContext:
        if not has_scope(context, scope):
            raise HTTPException(
                status_code=403,
                detail=f"Missing required scope '{scope}'.",
            )
        return context

    return _inner


def _safe_path(
    path: str,
    *,
    require_exists=False,
    require_file=False,
    require_dir=False,
) -> str:
    return resolve_in_workspace(
        path,
        workspace_root=WORKSPACE_ROOT,
        require_exists=require_exists,
        require_file=require_file,
        require_dir=require_dir,
    )


def _run_agent_job(job_id: str, request: AgentRequest):
    acquired = job_semaphore.acquire(blocking=False)
    if not acquired:
        job_store.add_event(job_id, {"type": "job_waiting_for_slot"})
        job_semaphore.acquire()

    job_store.start(job_id)
    try:
        def on_event(event: Dict[str, Any]):
            job_store.add_event(job_id, event)

        result = run_agent_goal(
            request.goal,
            project_details=request.project_details,
            max_steps=request.max_steps,
            auto_plan=request.auto_plan,
            on_event=on_event,
            workspace_path=request.workspace_path or ".",
        )
        job_store.finish(job_id, result)
    except Exception as e:  # pragma: no cover
        job_store.fail(job_id, str(e))
    finally:
        job_semaphore.release()


def _can_access_job(job: Dict[str, Any], context: AuthContext) -> bool:
    payload = job.get("payload", {})
    if not isinstance(payload, dict):
        return True
    meta = payload.get("_meta", {})
    if not isinstance(meta, dict):
        return True
    owner = str(meta.get("owner_user_id", "")).strip()
    if not owner:
        return True
    if has_scope(context, "*"):
        return True
    return owner == context.user_id


def create_app():
    app = FastAPI(title="AI CLI API", version="1.0.0")

    @app.post("/auth/login")
    def auth_login(request: LoginRequest):
        try:
            return device_auth_service.login_password(
                username=request.username,
                password=request.password,
            )
        except AuthError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message) from None

    @app.post("/auth/device/start")
    def auth_device_start(request: DeviceStartRequest, raw_request: Request):
        base_url = str(raw_request.base_url).rstrip("/")
        try:
            return device_auth_service.start_device_authorization(
                client_name=request.client_name,
                base_url=base_url,
            )
        except AuthError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message) from None

    @app.post("/auth/device/verify")
    def auth_device_verify(request: DeviceVerifyRequest):
        try:
            return device_auth_service.approve_device_code(
                user_code=request.user_code,
                username=request.username,
                password=request.password,
            )
        except AuthError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message) from None

    @app.post("/auth/device/token")
    def auth_device_token(request: DeviceTokenRequest):
        try:
            return device_auth_service.poll_device_token(
                device_code=request.device_code,
            )
        except AuthError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message) from None

    @app.post("/auth/refresh")
    def auth_refresh(request: RefreshRequest):
        try:
            return device_auth_service.refresh_access_token(
                refresh_token=request.refresh_token,
            )
        except AuthError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message) from None

    @app.post("/auth/logout")
    def auth_logout(request: LogoutRequest):
        try:
            return device_auth_service.revoke_refresh_token(
                refresh_token=request.refresh_token,
            )
        except AuthError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message) from None

    @app.get("/health")
    def health(_: AuthContext = Depends(_require_scope("read"))):
        return {"ok": True, "status": "healthy", "workspace_root": WORKSPACE_ROOT}

    @app.get("/auth/whoami")
    def whoami(context: AuthContext = Depends(_auth_guard)):
        return whoami_payload(context)

    @app.post("/analyze")
    def analyze(request: AnalyzeRequest, _: AuthContext = Depends(_require_scope("read"))):
        try:
            safe_path = _safe_path(request.path, require_exists=True)
        except WorkspacePathError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        return run_analysis(safe_path, use_llm=request.use_llm, refresh=request.refresh)

    @app.post("/fix/file")
    def fix_file(request: FixFileRequest, _: AuthContext = Depends(_require_scope("write"))):
        try:
            safe_path = _safe_path(request.path, require_exists=True, require_file=True)
        except WorkspacePathError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        return run_file_fix(safe_path, apply=request.apply, refresh=request.refresh)

    @app.post("/fix/project")
    def fix_project(request: FixProjectRequest, _: AuthContext = Depends(_require_scope("write"))):
        try:
            safe_path = _safe_path(request.path, require_exists=True, require_dir=True)
        except WorkspacePathError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        return run_project_fix(
            safe_path,
            apply=request.apply,
            use_llm=request.use_llm,
            refresh=request.refresh,
            max_files=request.max_files,
        )

    @app.get("/memory/stats")
    def memory_stats(_: AuthContext = Depends(_require_scope("read"))):
        return {"ok": True, "stats": get_memory_stats()}

    @app.get("/memory/show")
    def memory_show(limit: int = 20, _: AuthContext = Depends(_require_scope("read"))):
        return {"ok": True, "entries": get_memory_entries(limit=limit)}

    @app.delete("/memory")
    def memory_clear(request: MemoryClearRequest, _: AuthContext = Depends(_require_scope("write"))):
        return clear_memory(yes=request.yes)

    @app.post("/agent/run")
    def agent_run(request: AgentRequest, context: AuthContext = Depends(_require_scope("agent"))):
        try:
            safe_workspace = _safe_path(
                request.workspace_path or ".",
                require_exists=True,
                require_dir=True,
            )
        except WorkspacePathError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

        if not request.async_mode:
            return run_agent_goal(
                request.goal,
                project_details=request.project_details,
                max_steps=request.max_steps,
                auto_plan=request.auto_plan,
                workspace_path=safe_workspace,
            )

        request.workspace_path = safe_workspace
        payload = request.model_dump()
        payload["_meta"] = {"owner_user_id": context.user_id}
        job_id = job_store.create(payload)
        worker = threading.Thread(target=_run_agent_job, args=(job_id, request), daemon=True)
        worker.start()
        return {"ok": True, "job_id": job_id, "status": "queued"}

    @app.get("/jobs/{job_id}")
    def job_status(job_id: str, context: AuthContext = Depends(_require_scope("read"))):
        job = job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        if not _can_access_job(job, context):
            raise HTTPException(status_code=403, detail="You do not have access to this job.")
        return {"ok": True, "job": job}

    @app.get("/jobs/{job_id}/events")
    def job_events(
        job_id: str,
        since: int = 0,
        max_items: int = 100,
        context: AuthContext = Depends(_require_scope("read")),
    ):
        job = job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        if not _can_access_job(job, context):
            raise HTTPException(status_code=403, detail="You do not have access to this job.")
        events = job_store.get_events(job_id, since=since, max_items=max_items)
        if events is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return {"ok": True, "events": events}

    @app.get("/jobs/{job_id}/stream")
    def job_stream(job_id: str, since: int = 0, context: AuthContext = Depends(_require_scope("read"))):
        job = job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        if not _can_access_job(job, context):
            raise HTTPException(status_code=403, detail="You do not have access to this job.")

        def event_generator():
            last_seq = since
            idle_rounds = 0
            while True:
                job = job_store.get(job_id)
                if not job:
                    payload = {"type": "stream_error", "message": "Job not found."}
                    yield f"data: {json.dumps(payload)}\n\n"
                    break

                events = job_store.get_events(job_id, since=last_seq, max_items=200) or []
                if events:
                    idle_rounds = 0
                    for item in events:
                        last_seq = item["seq"]
                        yield f"data: {json.dumps(item)}\n\n"
                else:
                    idle_rounds += 1

                if job["status"] in {"done", "failed"} and not events:
                    payload = {"type": "stream_end", "status": job["status"], "last_seq": last_seq}
                    yield f"data: {json.dumps(payload)}\n\n"
                    break

                if idle_rounds > 240:
                    payload = {"type": "stream_timeout", "last_seq": last_seq}
                    yield f"data: {json.dumps(payload)}\n\n"
                    break

                time.sleep(0.25)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    return app


def run_server():
    try:
        import uvicorn
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Uvicorn is not installed. Install with: pip install uvicorn"
        ) from e

    uvicorn.run(create_app(), host=API_HOST, port=API_PORT)
