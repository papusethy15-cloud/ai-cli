from utils.analysis_memory import MEMORY_FILE, load_memory, save_memory


def _all_entries(memory):
    files = memory.get("files", {})
    entries = []
    for path, entry in files.items():
        issues = entry.get("analysis", {}).get("issues", [])
        entries.append(
            {
                "path": path,
                "updated_at": entry.get("updated_at", "unknown"),
                "use_llm": bool(entry.get("use_llm", False)),
                "issue_count": len(issues),
            }
        )
    entries.sort(key=lambda item: item["updated_at"], reverse=True)
    return entries


def get_memory_stats():
    memory = load_memory()
    entries = _all_entries(memory)
    llm_entries = sum(1 for entry in entries if entry["use_llm"])
    static_entries = len(entries) - llm_entries
    return {
        "memory_file": str(MEMORY_FILE),
        "cached_files": len(entries),
        "llm_analyses": llm_entries,
        "static_analyses": static_entries,
    }


def get_memory_entries(limit=20):
    memory = load_memory()
    return _all_entries(memory)[: max(0, limit)]


def clear_memory(yes=False):
    if not yes:
        return {"ok": False, "error": "Refusing to clear memory without --yes."}
    save_memory({"version": 1, "files": {}})
    return {"ok": True}
