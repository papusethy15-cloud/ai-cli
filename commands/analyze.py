from services.analyze_service import run_analysis


def _print_file_report(result):
    issues = result.get("issues", [])
    cache_tag = " (from memory)" if result.get("from_cache") else ""
    print(f"\nFILE: {result['path']}{cache_tag}")

    if not issues:
        print("- No issues found.")
        return

    for issue in issues:
        line = issue.get("line")
        line_text = f" line {line}" if line else ""
        print(
            f"- [{issue['severity']}] {issue['type']}:{line_text} "
            f"{issue['message']} (source: {issue['source']})"
        )


def _print_summary(summary):
    by_severity = summary.get("issues_by_severity", {})
    print("\n=== SUMMARY ===")
    print(f"Files scanned: {summary.get('files_scanned', 0)}")
    print(f"Files with issues: {summary.get('files_with_issues', 0)}")
    print(f"Loaded from memory: {summary.get('from_memory', 0)}")
    print(
        f"Issues by severity: error={by_severity.get('error', 0)}, "
        f"warning={by_severity.get('warning', 0)}, info={by_severity.get('info', 0)}"
    )


def analyze(path, use_llm=True, refresh=False):
    response = run_analysis(path, use_llm=use_llm, refresh=refresh)
    if not response.get("ok"):
        print(response.get("error", "Unknown analysis error"))
        return

    for result in response.get("results", []):
        _print_file_report(result)
    _print_summary(response.get("summary", {}))
