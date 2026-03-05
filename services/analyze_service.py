import os

from utils.code_analyzer import analyze_file, analyze_project


def build_summary(results):
    by_severity = {"error": 0, "warning": 0, "info": 0}
    for result in results:
        for issue in result.get("issues", []):
            severity = issue.get("severity", "info")
            if severity not in by_severity:
                by_severity[severity] = 0
            by_severity[severity] += 1

    return {
        "files_scanned": len(results),
        "files_with_issues": sum(1 for r in results if r.get("issues")),
        "from_memory": sum(1 for r in results if r.get("from_cache")),
        "issues_by_severity": by_severity,
    }


def run_analysis(path, use_llm=True, refresh=False):
    target = os.path.abspath(path)
    if os.path.isfile(target):
        result = analyze_file(target, use_llm=use_llm, refresh=refresh)
        results = [result]
        return {
            "ok": True,
            "target_type": "file",
            "path": target,
            "results": results,
            "summary": build_summary(results),
        }

    if not os.path.isdir(target):
        return {"ok": False, "error": f"Path not found: {path}", "results": []}

    results = analyze_project(target, use_llm=use_llm, refresh=refresh)
    return {
        "ok": True,
        "target_type": "project",
        "path": target,
        "results": results,
        "summary": build_summary(results),
    }
