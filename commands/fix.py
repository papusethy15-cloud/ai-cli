import os
import re

from config import OUTPUT_MODEL
from providers.ollama_provider import ask_llm
from utils.code_analyzer import analyze_file
from utils.file_writer import write_file


def _read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


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


def _generate_fix(file, refresh=False):
    if not os.path.exists(file):
        return {"ok": False, "error": f"File not found: {file}"}

    code = _read_text(file)
    analysis = analyze_file(file, use_llm=False, refresh=refresh)
    issues = analysis.get("issues", [])
    issues_text = _issues_text(issues)

    prompt = f"""
You are a senior software engineer.
Fix syntax errors, runtime errors, and clear logic bugs.
Keep behavior and structure unless a change is required for correctness.
Return ONLY the full corrected file content.

Known issues:
{issues_text}

CODE:
{code}
"""

    result = ask_llm(prompt, model=OUTPUT_MODEL)
    if result.startswith("[LLM Error]"):
        return {"ok": False, "error": result}

    fixed_code = _extract_code(result)
    if file.endswith(".py"):
        valid, err = _python_is_valid(fixed_code, file)
        if not valid:
            return {
                "ok": False,
                "error": f"[Fix Error] Generated code has syntax errors: {err}",
                "generated_code": fixed_code,
            }

    return {
        "ok": True,
        "file": file,
        "original_code": code,
        "fixed_code": fixed_code,
        "issues_before": issues,
    }


def _issues_text(issues):
    if not issues:
        return "- No static issues found."
    lines = []
    for issue in issues:
        line = issue.get("line")
        line_text = f" line {line}" if line else ""
        lines.append(f"- [{issue['severity']}] {issue['type']}:{line_text} {issue['message']}")
    return "\n".join(lines)


def fix(file, apply=False, refresh=False):
    generated = _generate_fix(file, refresh=refresh)
    if not generated.get("ok"):
        print(generated.get("error", "[Fix Error] Unknown error"))
        if generated.get("generated_code"):
            print("Generated output:\n")
            print(generated["generated_code"])
        return

    if apply:
        write_file(file, generated["fixed_code"])
        # Refresh file memory after write so analyze reuses new state.
        post = analyze_file(file, use_llm=False, refresh=True)
        print(
            f"[Fix] Saved: {file} | Remaining static issues: {len(post.get('issues', []))}"
        )
    else:
        print(generated["fixed_code"])


def fix_file_for_project(file, apply=False, refresh=False):
    generated = _generate_fix(file, refresh=refresh)
    if not generated.get("ok"):
        return {"file": file, "status": "failed", "error": generated.get("error")}

    if not apply:
        return {"file": file, "status": "dry_run_ready"}

    write_file(file, generated["fixed_code"])
    post = analyze_file(file, use_llm=False, refresh=True)
    return {
        "file": file,
        "status": "saved",
        "remaining_issues": len(post.get("issues", [])),
    }
