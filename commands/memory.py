from services.memory_service import clear_memory, get_memory_entries, get_memory_stats


def memory_command(action="stats", limit=20, yes=False):
    action = action.lower().strip()

    if action == "stats":
        stats = get_memory_stats()
        print(f"Memory file: {stats['memory_file']}")
        print(f"Cached files: {stats['cached_files']}")
        print(f"LLM analyses: {stats['llm_analyses']}")
        print(f"Static-only analyses: {stats['static_analyses']}")
        return

    if action == "show":
        entries = get_memory_entries(limit=limit)
        if not entries:
            print("Memory cache is empty.")
            return
        print(f"Showing up to {limit} cached files:")
        for entry in entries:
            mode = "llm" if entry["use_llm"] else "static"
            print(
                f"- {entry['path']} | issues={entry['issue_count']} "
                f"| mode={mode} | updated={entry['updated_at']}"
            )
        return

    if action == "clear":
        result = clear_memory(yes=yes)
        if result.get("ok"):
            print("Memory cache cleared.")
        else:
            print(result.get("error", "Failed to clear memory."))
        return

    print(f"Unknown action: {action}")
    print("Use one of: stats, show, clear")
