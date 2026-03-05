import os

from commands.fix import fix_file_for_project
from utils.code_analyzer import analyze_project


def _has_actionable_issues(result):
    issues = result.get("issues", [])
    return any(issue.get("severity") in {"error", "warning"} for issue in issues)


def fix_project(path, apply=False, use_llm=False, refresh=False, max_files=20):
    target = os.path.abspath(path)
    if not os.path.isdir(target):
        print(f"Path not found: {path}")
        return

    analysis = analyze_project(target, use_llm=use_llm, refresh=refresh)
    candidates = [r for r in analysis if _has_actionable_issues(r)]

    if not candidates:
        print("No actionable issues found.")
        return

    selected = candidates[:max_files]
    if not apply:
        print("Dry-run mode (no file writes).")
        for result in selected:
            print(f"- Would fix: {result['path']} ({len(result.get('issues', []))} issues)")
        print(f"Selected files: {len(selected)} of {len(candidates)}")
        print("Re-run with --apply to save fixes.")
        return

    saved = 0
    failed = 0
    for result in selected:
        response = fix_file_for_project(
            result["path"],
            apply=True,
            refresh=refresh,
        )
        if response["status"] == "saved":
            saved += 1
            print(
                f"[Saved] {response['file']} | Remaining issues: "
                f"{response['remaining_issues']}"
            )
        else:
            failed += 1
            print(f"[Failed] {response['file']} | {response.get('error', 'unknown error')}")

    print("\n=== FIX PROJECT SUMMARY ===")
    print(f"Selected files: {len(selected)}")
    print(f"Saved: {saved}")
    print(f"Failed: {failed}")
