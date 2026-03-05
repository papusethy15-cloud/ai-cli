import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import time
from typing import Any, Dict, List, Optional

from config import API_HOST, API_KEY, API_PORT
from services.agent_service import run_agent_goal
from services.analyze_service import run_analysis
from services.fix_service import run_file_fix, run_project_fix
from services.memory_service import clear_memory, get_memory_entries, get_memory_stats

try:
    from fastapi import Depends, FastAPI, Header, HTTPException
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
    project_details: Optional[Dict[str, str]] = None
    max_steps: Optional[int] = None
    auto_plan: bool = True
    async_mode: bool = False


@dataclass
class JobStore:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _jobs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def create(self, payload: Dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
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


def _auth_guard(x_api_key: Optional[str] = Header(default=None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key.")


def _run_agent_job(job_id: str, request: AgentRequest):
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
        )
        job_store.finish(job_id, result)
    except Exception as e:  # pragma: no cover
        job_store.fail(job_id, str(e))


def create_app():
    app = FastAPI(title="AI CLI API", version="1.0.0")

    @app.get("/health")
    def health(_: None = Depends(_auth_guard)):
        return {"ok": True, "status": "healthy"}

    @app.post("/analyze")
    def analyze(request: AnalyzeRequest, _: None = Depends(_auth_guard)):
        return run_analysis(request.path, use_llm=request.use_llm, refresh=request.refresh)

    @app.post("/fix/file")
    def fix_file(request: FixFileRequest, _: None = Depends(_auth_guard)):
        return run_file_fix(request.path, apply=request.apply, refresh=request.refresh)

    @app.post("/fix/project")
    def fix_project(request: FixProjectRequest, _: None = Depends(_auth_guard)):
        return run_project_fix(
            request.path,
            apply=request.apply,
            use_llm=request.use_llm,
            refresh=request.refresh,
            max_files=request.max_files,
        )

    @app.get("/memory/stats")
    def memory_stats(_: None = Depends(_auth_guard)):
        return {"ok": True, "stats": get_memory_stats()}

    @app.get("/memory/show")
    def memory_show(limit: int = 20, _: None = Depends(_auth_guard)):
        return {"ok": True, "entries": get_memory_entries(limit=limit)}

    @app.delete("/memory")
    def memory_clear(request: MemoryClearRequest, _: None = Depends(_auth_guard)):
        return clear_memory(yes=request.yes)

    @app.post("/agent/run")
    def agent_run(request: AgentRequest, _: None = Depends(_auth_guard)):
        if not request.async_mode:
            return run_agent_goal(
                request.goal,
                project_details=request.project_details,
                max_steps=request.max_steps,
                auto_plan=request.auto_plan,
            )

        job_id = job_store.create(request.model_dump())
        worker = threading.Thread(target=_run_agent_job, args=(job_id, request), daemon=True)
        worker.start()
        return {"ok": True, "job_id": job_id, "status": "queued"}

    @app.get("/jobs/{job_id}")
    def job_status(job_id: str, _: None = Depends(_auth_guard)):
        job = job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        return {"ok": True, "job": job}

    @app.get("/jobs/{job_id}/events")
    def job_events(job_id: str, since: int = 0, max_items: int = 100, _: None = Depends(_auth_guard)):
        events = job_store.get_events(job_id, since=since, max_items=max_items)
        if events is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return {"ok": True, "events": events}

    @app.get("/jobs/{job_id}/stream")
    def job_stream(job_id: str, since: int = 0, _: None = Depends(_auth_guard)):
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
