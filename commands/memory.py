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


def memory_command(action="stats", limit=20, yes=False):
    """
    Manage analyzer memory cache.
    Actions:
    - stats: show memory file + aggregate counts.
    - show: list cached files.
    - clear: remove all cached entries (requires --yes).
    """
    action = action.lower().strip()
    memory = load_memory()
    entries = _all_entries(memory)

    if action == "stats":
        llm_entries = sum(1 for entry in entries if entry["use_llm"])
        static_entries = len(entries) - llm_entries
        print(f"Memory file: {MEMORY_FILE}")
        print(f"Cached files: {len(entries)}")
        print(f"LLM analyses: {llm_entries}")
        print(f"Static-only analyses: {static_entries}")
        return

    if action == "show":
        if not entries:
            print("Memory cache is empty.")
            return
        print(f"Showing up to {limit} cached files:")
        for entry in entries[:limit]:
            mode = "llm" if entry["use_llm"] else "static"
            print(
                f"- {entry['path']} | issues={entry['issue_count']} "
                f"| mode={mode} | updated={entry['updated_at']}"
            )
        return

    if action == "clear":
        if not yes:
            print("Refusing to clear memory without --yes.")
            return
        save_memory({"version": 1, "files": {}})
        print("Memory cache cleared.")
        return

    print(f"Unknown action: {action}")
    print("Use one of: stats, show, clear")
