from services.fix_service import run_project_fix


def fix_project(path, apply=False, use_llm=False, refresh=False, max_files=20):
    response = run_project_fix(
        path,
        apply=apply,
        use_llm=use_llm,
        refresh=refresh,
        max_files=max_files,
    )
    if not response.get("ok"):
        print(response.get("error", "Unknown project fix error"))
        return

    status = response.get("status")
    if status == "no_actionable_issues":
        print("No actionable issues found.")
        return

    if status == "dry_run_ready":
        print("Dry-run mode (no file writes).")
        for item in response.get("selected_files", []):
            print(f"- Would fix: {item['path']} ({item['issue_count']} issues)")
        summary = response.get("summary", {})
        print(f"Selected files: {summary.get('selected', 0)} of {summary.get('total_actionable', 0)}")
        print("Re-run with --apply to save fixes.")
        return

    for item in response.get("selected_files", []):
        if item.get("ok"):
            print(
                f"[Saved] {item['file']} | Remaining issues: "
                f"{item.get('remaining_issues', 0)}"
            )
        else:
            print(f"[Failed] {item['file']} | {item.get('error', 'unknown error')}")

    summary = response.get("summary", {})
    print("\n=== FIX PROJECT SUMMARY ===")
    print(f"Selected files: {summary.get('selected', 0)}")
    print(f"Saved: {summary.get('saved', 0)}")
    print(f"Failed: {summary.get('failed', 0)}")
