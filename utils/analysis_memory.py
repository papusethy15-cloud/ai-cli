import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

MEMORY_FILE = Path(".ai_cli_memory.json")


def _empty_memory():
    return {"version": 1, "files": {}}


def load_memory():
    if not MEMORY_FILE.exists():
        return _empty_memory()

    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return _empty_memory()

    if not isinstance(data, dict) or "files" not in data:
        return _empty_memory()
    if not isinstance(data.get("files"), dict):
        return _empty_memory()
    return data


def save_memory(memory):
    payload = memory if isinstance(memory, dict) else _empty_memory()
    payload.setdefault("version", 1)
    payload.setdefault("files", {})
    if not isinstance(payload["files"], dict):
        payload["files"] = {}

    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=str(MEMORY_FILE.parent),
    ) as tmp:
        json.dump(payload, tmp, indent=2, ensure_ascii=True)
        tmp_path = Path(tmp.name)

    tmp_path.replace(MEMORY_FILE)


def get_content_hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_cached_analysis(memory, path, content_hash, use_llm):
    file_entry = memory.get("files", {}).get(path)
    if not file_entry:
        return None
    if file_entry.get("hash") != content_hash:
        return None
    if file_entry.get("use_llm") != use_llm:
        return None
    return file_entry.get("analysis")


def set_cached_analysis(memory, path, content_hash, use_llm, analysis):
    memory.setdefault("files", {})[path] = {
        "hash": content_hash,
        "use_llm": use_llm,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "analysis": analysis,
    }
