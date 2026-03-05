import ast
import json
import os
import re
from pathlib import Path

from config import ANALYSIS_MODEL
from providers.ollama_provider import ask_llm
from utils.analysis_memory import (
    MEMORY_FILE,
    get_cached_analysis,
    get_content_hash,
    load_memory,
    save_memory,
    set_cached_analysis,
)
from utils.file_reader import FileReadError, read_file
from utils.project_scanner import list_project_files

CODE_EXTENSIONS = [".py", ".js", ".ts", ".json", ".html", ".css"]


def _normalize_path(path):
    return os.path.relpath(os.path.abspath(path), os.getcwd())


def _issue(issue_type, severity, message, line=None, source="static"):
    return {
        "type": issue_type,
        "severity": severity,
        "message": message,
        "line": line,
        "source": source,
    }


def _python_static_issues(code):
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        issues.append(
            _issue(
                "syntax_error",
                "error",
                f"{e.msg} (line {e.lineno})",
                line=e.lineno,
                source="python_parser",
            )
        )
        return issues

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(
                _issue(
                    "bug_risk",
                    "warning",
                    "Bare except can hide real runtime failures.",
                    line=node.lineno,
                )
            )

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"eval", "exec"}:
                issues.append(
                    _issue(
                        "security_risk",
                        "warning",
                        f"Use of `{node.func.id}` can be unsafe.",
                        line=node.lineno,
                    )
                )

            if node.func.id == "open":
                has_encoding = any(k.arg == "encoding" for k in node.keywords)
                if not has_encoding:
                    issues.append(
                        _issue(
                            "portability",
                            "info",
                            "open() without encoding may be system-dependent.",
                            line=node.lineno,
                        )
                    )

        if isinstance(node, ast.FunctionDef):
            for default in node.args.defaults:
                if isinstance(default, (ast.Dict, ast.List, ast.Set)):
                    issues.append(
                        _issue(
                            "bug_risk",
                            "warning",
                            f"Mutable default argument in function `{node.name}`.",
                            line=node.lineno,
                        )
                    )

    return issues


def _parse_llm_json_array(text):
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except Exception:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, list) else []
        except Exception:
            return []


def _llm_issues(path, code):
    prompt = f"""
You are a code reviewer.
Return ONLY a JSON array with up to 3 issues.
Each issue must follow this shape:
{{"severity":"error|warning|info","line":number|null,"message":"text"}}
If no issues, return [].

Focus on likely bugs, logic mistakes, and obvious bad patterns.

FILE: {path}
CODE:
{code[:4000]}
"""
    result = ask_llm(prompt, model=ANALYSIS_MODEL)
    if result.startswith("[LLM Error]"):
        return [
            _issue(
                "analyzer_error",
                "info",
                result,
                source="llm",
            )
        ]

    parsed = _parse_llm_json_array(result)
    issues = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity", "info")).lower().strip()
        if severity not in {"error", "warning", "info"}:
            severity = "info"
        line = item.get("line")
        if isinstance(line, str) and line.isdigit():
            line = int(line)
        if not isinstance(line, int):
            line = None
        message = item.get("message", "LLM reported an issue.")
        issues.append(_issue("llm_issue", severity, message, line=line, source="llm"))
    return issues


def analyze_file(path, use_llm=True, refresh=False, memory=None):
    rel_path = _normalize_path(path)
    try:
        code = read_file(path)
    except FileReadError as e:
        return {
            "path": rel_path,
            "issues": [
                _issue(
                    "read_error",
                    "error",
                    f"Failed to read file: {e}",
                    source="io",
                )
            ],
            "from_cache": False,
        }

    content_hash = get_content_hash(code)
    local_memory = memory if memory is not None else load_memory()

    if not refresh:
        cached = get_cached_analysis(local_memory, rel_path, content_hash, use_llm)
        if cached:
            return {
                "path": rel_path,
                "issues": cached.get("issues", []),
                "from_cache": True,
            }

    issues = []
    if Path(path).suffix.lower() == ".py":
        issues.extend(_python_static_issues(code))

    if use_llm:
        try:
            issues.extend(_llm_issues(rel_path, code))
        except Exception as e:
            issues.append(
                _issue(
                    "analyzer_error",
                    "info",
                    f"LLM analyzer failed: {e}",
                    source="llm",
                )
            )

    analysis = {"issues": issues}
    set_cached_analysis(local_memory, rel_path, content_hash, use_llm, analysis)
    if memory is None:
        save_memory(local_memory)

    return {"path": rel_path, "issues": issues, "from_cache": False}


def analyze_project(path, use_llm=True, refresh=False):
    files = list_project_files(path, extensions=CODE_EXTENSIONS)
    memory_path = os.path.abspath(MEMORY_FILE)
    memory = load_memory()
    results = []
    for file_path in files:
        if os.path.abspath(file_path) == memory_path:
            continue
        results.append(
            analyze_file(
                file_path,
                use_llm=use_llm,
                refresh=refresh,
                memory=memory,
            )
        )

    save_memory(memory)
    return results
