import os

from utils.code_analyzer import analyze_file, analyze_project


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


def _summarize(results):
    total = len(results)
    with_issues = sum(1 for r in results if r.get("issues"))
    cached = sum(1 for r in results if r.get("from_cache"))
    by_severity = {"error": 0, "warning": 0, "info": 0}
    for result in results:
        for issue in result.get("issues", []):
            sev = issue.get("severity", "info")
            if sev not in by_severity:
                by_severity[sev] = 0
            by_severity[sev] += 1
    print("\n=== SUMMARY ===")
    print(f"Files scanned: {total}")
    print(f"Files with issues: {with_issues}")
    print(f"Loaded from memory: {cached}")
    print(
        f"Issues by severity: error={by_severity.get('error', 0)}, "
        f"warning={by_severity.get('warning', 0)}, "
        f"info={by_severity.get('info', 0)}"
    )


def analyze(path, use_llm=True, refresh=False):
    """
    Advanced analyzer:
    - File path -> analyze one file.
    - Directory path -> analyze each code file and cache results in memory.
    """
    target = os.path.abspath(path)

    if os.path.isfile(target):
        result = analyze_file(target, use_llm=use_llm, refresh=refresh)
        _print_file_report(result)
        _summarize([result])
        return

    if not os.path.isdir(target):
        print(f"Path not found: {path}")
        return

    results = analyze_project(target, use_llm=use_llm, refresh=refresh)
    for result in results:
        _print_file_report(result)
    _summarize(results)
