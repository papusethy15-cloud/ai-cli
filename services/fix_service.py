import re

from config import OUTPUT_MODEL
from providers.ollama_provider import ask_llm
from services.analyze_service import run_analysis
from utils.code_analyzer import analyze_file
from utils.file_reader import FileReadError, read_file
from utils.file_writer import write_file


def _extract_code(text):
    match = re.search(r"```(?:\w+)?\n([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text.strip()


def _python_is_valid(code, path):
    try:
        compile(code, path, "exec")
        return True, None
    except SyntaxError as e:
        return False, f"{e.msg} (line {e.lineno})"


def _issues_text(issues):
    if not issues:
        return "- No static issues found."
    lines = []
    for issue in issues:
        line = issue.get("line")
        line_text = f" line {line}" if line else ""
        lines.append(f"- [{issue['severity']}] {issue['type']}:{line_text} {issue['message']}")
    return "\n".join(lines)


def generate_file_fix(path, refresh=False):
    try:
        code = read_file(path)
    except FileReadError as e:
        return {"ok": False, "error": f"[Fix Error] {e}"}

    analysis = analyze_file(path, use_llm=False, refresh=refresh)
    issues = analysis.get("issues", [])
    prompt = f"""
You are a senior software engineer.
Fix syntax errors, runtime errors, and clear logic bugs.
Keep behavior and structure unless a change is required for correctness.
Return ONLY the full corrected file content.

Known issues:
{_issues_text(issues)}

CODE:
{code}
"""
    result = ask_llm(prompt, model=OUTPUT_MODEL)
    if result.startswith("[LLM Error]"):
        return {"ok": False, "error": result}

    fixed_code = _extract_code(result)
    if path.endswith(".py"):
        valid, err = _python_is_valid(fixed_code, path)
        if not valid:
            return {
                "ok": False,
                "error": f"[Fix Error] Generated code has syntax errors: {err}",
                "generated_code": fixed_code,
            }

    return {
        "ok": True,
        "file": path,
        "original_code": code,
        "fixed_code": fixed_code,
        "issues_before": issues,
    }


def run_file_fix(path, apply=False, refresh=False):
    generated = generate_file_fix(path, refresh=refresh)
    if not generated.get("ok"):
        return generated

    if not apply:
        return {
            "ok": True,
            "status": "preview",
            "file": path,
            "fixed_code": generated["fixed_code"],
            "issues_before": generated.get("issues_before", []),
        }

    saved = write_file(path, generated["fixed_code"])
    if not saved:
        return {"ok": False, "error": f"[Fix Error] Failed to write file: {path}"}

    post = analyze_file(path, use_llm=False, refresh=True)
    return {
        "ok": True,
        "status": "saved",
        "file": path,
        "remaining_issues": len(post.get("issues", [])),
        "issues_before": generated.get("issues_before", []),
    }


def run_project_fix(path, apply=False, use_llm=False, refresh=False, max_files=20):
    analysis = run_analysis(path, use_llm=use_llm, refresh=refresh)
    if not analysis.get("ok"):
        return analysis

    actionable = []
    for result in analysis["results"]:
        issues = result.get("issues", [])
        if any(issue.get("severity") in {"error", "warning"} for issue in issues):
            actionable.append(result)

    if not actionable:
        return {
            "ok": True,
            "status": "no_actionable_issues",
            "selected_files": [],
            "summary": {"selected": 0, "saved": 0, "failed": 0},
        }

    selected = actionable[:max_files]
    if not apply:
        return {
            "ok": True,
            "status": "dry_run_ready",
            "selected_files": [
                {"path": item["path"], "issue_count": len(item.get("issues", []))}
                for item in selected
            ],
            "summary": {
                "selected": len(selected),
                "total_actionable": len(actionable),
                "saved": 0,
                "failed": 0,
            },
        }

    saved = 0
    failed = 0
    file_results = []
    for item in selected:
        fixed = run_file_fix(item["path"], apply=True, refresh=refresh)
        if fixed.get("ok"):
            saved += 1
            file_results.append(fixed)
        else:
            failed += 1
            file_results.append({"ok": False, "file": item["path"], "error": fixed.get("error")})

    return {
        "ok": True,
        "status": "applied",
        "selected_files": file_results,
        "summary": {
            "selected": len(selected),
            "total_actionable": len(actionable),
            "saved": saved,
            "failed": failed,
        },
    }
