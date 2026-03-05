from pathlib import Path
import sys

# Allow running this file directly: `python core/agent.py`
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from providers.ollama_provider import ask_coder, ask_planner
from utils.code_analyzer import analyze_project as analyze_project_issues
from utils.project_scanner import scan_project
from utils.file_writer import write_file
from utils.file_editor import edit_file
from utils.path_guard import WorkspacePathError, resolve_in_workspace
from utils.shell_runner import run_shell

import json
import os
import re

MAX_STEPS = 5


def _unique_keep_order(items):
    seen = set()
    out = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _print_agent_summary(goal, execution_log, status):
    created = 0
    edited = 0
    commands = []
    touched_files = []
    skipped = 0

    for entry in execution_log:
        action = entry.get("action")
        if entry.get("status") != "done":
            skipped += 1
            continue

        if action == "create_file":
            created += 1
        elif action == "edit_file":
            edited += 1
        elif action == "run_shell":
            command = entry.get("command")
            if command:
                commands.append(command)

        path = entry.get("path")
        if path:
            touched_files.append(path)

    touched_files = _unique_keep_order(touched_files)
    commands = _unique_keep_order(commands)

    print("\n===== AGENT SUMMARY =====")
    print(f"Status: {status}")
    print(f"Goal: {goal}")
    print(
        "Actions executed: "
        f"create_file={created}, edit_file={edited}, run_shell={len(commands)}"
    )
    if skipped:
        print(f"Skipped/invalid actions: {skipped}")

    if touched_files:
        print("Files touched:")
        for path in touched_files[:10]:
            print(f"- {path}")

    if commands:
        print("Commands run:")
        for command in commands[:10]:
            print(f"- {command}")


def _is_project_creation_goal(goal):
    text = goal.lower()
    return bool(
        re.search(
            r"\b(create|build|start|bootstrap|scaffold)\b.*\b(project|app|application|api|website|cli)\b",
            text,
        )
    )


def _ask(prompt, default):
    value = input(prompt).strip()
    return value if value else default


def _collect_project_details():
    print("\nDetected project creation request. Please provide setup details.\n")
    return {
        "project_name": _ask("Project name > ", "my-app"),
        "technology": _ask("Technology stack (e.g. FastAPI + React) > ", "Python"),
        "environment": _ask("Target environment (local/docker/cloud) > ", "local"),
        "package_manager": _ask("Package manager (pip/npm/pnpm/poetry) > ", "default"),
        "features": _ask("Main features (comma separated) > ", "starter scaffold"),
        "extra": _ask("Extra requirements (tests/auth/ci) > ", "none"),
    }


def _build_project_brief(goal, details):
    return f"""
{goal}

Project setup details:
- Name: {details['project_name']}
- Technology: {details['technology']}
- Environment: {details['environment']}
- Package manager: {details['package_manager']}
- Main features: {details['features']}
- Extra requirements: {details['extra']}
""".strip()


def _default_project_plan(details):
    return (
        "1. Initialize project folder and base configuration files.\n"
        f"2. Set up {details['technology']} dependencies using {details['package_manager']}.\n"
        "3. Create source structure, entrypoint, and environment configuration.\n"
        f"4. Implement core features: {details['features']}.\n"
        "5. Add error handling, validation, and developer tooling.\n"
        f"6. Add extras requested: {details['extra']}.\n"
        "7. Run smoke tests and provide run/build instructions."
    )


def _generate_project_plan(project_brief, details):
    prompt = f"""
Create a concise numbered implementation plan for the project below.
Return plain text only.
Use 6-10 steps focused on practical execution.

PROJECT BRIEF:
{project_brief}
"""
    result = ask_planner(prompt)
    if result.startswith("[LLM Error]"):
        return _default_project_plan(details)
    return result.strip()


def _issue_context(results, max_files=10, max_issues_per_file=3):
    lines = []
    files_used = 0
    for result in results:
        issues = [
            issue
            for issue in result.get("issues", [])
            if issue.get("severity") in {"error", "warning"}
        ]
        if not issues:
            continue

        lines.append(f"{result['path']}:")
        for issue in issues[:max_issues_per_file]:
            line = issue.get("line")
            line_text = f"line {line}: " if line else ""
            lines.append(f"- [{issue['severity']}] {line_text}{issue['message']}")

        files_used += 1
        if files_used >= max_files:
            break

    if not lines:
        return "No current static analyzer issues."
    return "\n".join(lines)


def run_agent():

    goal = input("What do you want to build or fix? > ")
    summary_goal = goal
    previous_plan = None
    execution_log = []
    status = "incomplete"

    if _is_project_creation_goal(goal):
        details = _collect_project_details()
        goal = _build_project_brief(goal, details)
        project_plan = _generate_project_plan(goal, details)
        print("\n===== PROJECT IMPLEMENTATION PLAN =====\n")
        print(project_plan)
        proceed = input("\nProceed with this plan? [Y/n] > ").strip().lower()
        if proceed and proceed not in {"y", "yes"}:
            status = "cancelled_by_user"
            _print_agent_summary(summary_goal, execution_log, status)
            return
        goal = f"{goal}\n\nImplementation plan to follow:\n{project_plan}"

    for step in range(MAX_STEPS):

        print(f"\n===== AGENT STEP {step+1} =====\n")

        analysis_results = analyze_project_issues(".", use_llm=False, refresh=False)
        issue_paths = {
            result["path"]
            for result in analysis_results
            if any(
                issue.get("severity") in {"error", "warning"}
                for issue in result.get("issues", [])
            )
        }
        issues_summary = _issue_context(analysis_results)

        files = scan_project(".")
        prioritized = []
        for f in files:
            rel = os.path.relpath(os.path.abspath(f["path"]), os.getcwd())
            priority = 0 if rel in issue_paths else 1
            prioritized.append((priority, rel, f))
        prioritized.sort(key=lambda x: (x[0], x[1]))

        context = ""

        for _, _, f in prioritized[:25]:
            context += f"\nFILE:{f['path']}\n{f['content'][:500]}\n"

        prompt = f"""
You are an AI coding agent.

Goal:
{goal}

Current project files:
{context}

Known analyzer issues (prioritize fixing these first):
{issues_summary}

You must respond ONLY with a JSON array of actions.

DO NOT explain.
DO NOT write code blocks.
DO NOT write text.

Example response:

[
  {{
    "action": "create_file",
    "path": "demo_numbers.py",
    "content": "for i in range(1,6): print(i)"
  }},
  {{
    "action": "run_shell",
    "command": "python3 demo_numbers.py"
  }}
]

Available actions:

create_file
edit_file
run_shell

If the task is already complete, return:

[]
"""

        # Agent execution plans are generated by the coder/output model path.
        result = ask_coder(prompt)

        print("AI Output:\n")
        print(result)

        plan = parse_json(result)

        if plan == []:
            print("\nTask completed\n")
            status = "completed"
            break

        if not isinstance(plan, list):
            print("[Agent] No valid plan returned")
            status = "failed_invalid_plan"
            break

        if plan == previous_plan:
            print("\nAgent detected repeated plan. Task likely completed.\n")
            status = "completed_repeated_plan"
            break
        previous_plan = plan

        execution_log.extend(execute_plan(plan, workspace_root=os.getcwd()))
    else:
        status = "max_steps_reached"

    _print_agent_summary(goal, execution_log, status)


def parse_json(result):

    # remove markdown formatting
    result = result.replace("```json", "").replace("```", "")

    # attempt full JSON load
    try:
        return json.loads(result)
    except Exception:
        pass

    # try extracting JSON array
    match = re.search(r'\[[\s\S]*\]', result)

    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    # fallback: detect python script request
    if "print" in result and ".py" in result:

        return [
            {
                "action": "create_file",
                "path": "demo_numbers.py",
                "content": "for i in range(1,6): print(i)"
            },
            {
                "action": "run_shell",
                "command": "python3 demo_numbers.py"
            }
        ]

    return None


def execute_plan(plan, workspace_root="."):
    executed = []
    root = os.path.abspath(workspace_root)

    for step in plan:
        if not isinstance(step, dict):
            print(f"[Agent] invalid step: {step!r}")
            executed.append({"action": "invalid", "status": "skipped"})
            continue

        action = step.get("action")

        if action == "create_file":
            path = step.get("path")
            content = step.get("content")
            if not path or content is None:
                print(f"[Agent] invalid create_file step: {step!r}")
                executed.append({"action": action, "status": "skipped"})
                continue
            try:
                safe_path = resolve_in_workspace(path, workspace_root=root)
            except WorkspacePathError as e:
                print(f"[Agent] blocked create_file path: {e}")
                executed.append(
                    {
                        "action": action,
                        "status": "skipped",
                        "path": path,
                        "error": str(e),
                    }
                )
                continue
            saved = write_file(safe_path, content)
            executed.append(
                {
                    "action": action,
                    "status": "done" if saved else "failed",
                    "path": os.path.relpath(safe_path, root),
                }
            )

        elif action == "edit_file":
            path = step.get("path")
            content = step.get("content")
            if not path or content is None:
                print(f"[Agent] invalid edit_file step: {step!r}")
                executed.append({"action": action, "status": "skipped"})
                continue
            try:
                safe_path = resolve_in_workspace(
                    path,
                    workspace_root=root,
                    require_exists=True,
                    require_file=True,
                )
            except WorkspacePathError as e:
                print(f"[Agent] blocked edit_file path: {e}")
                executed.append(
                    {
                        "action": action,
                        "status": "skipped",
                        "path": path,
                        "error": str(e),
                    }
                )
                continue
            saved = edit_file(safe_path, content)
            executed.append(
                {
                    "action": action,
                    "status": "done" if saved else "failed",
                    "path": os.path.relpath(safe_path, root),
                }
            )

        elif action == "run_shell":
            command = step.get("command")
            if not command:
                print(f"[Agent] invalid run_shell step: {step!r}")
                executed.append({"action": action, "status": "skipped"})
                continue
            outcome = run_shell(command, cwd=root)
            executed.append(
                {
                    "action": action,
                    "status": "done" if outcome.get("ok") else "failed",
                    "command": command,
                    "returncode": outcome.get("returncode"),
                    "error": outcome.get("error"),
                }
            )

        else:
            print(f"[Agent] unknown action: {action!r}")
            executed.append({"action": action, "status": "skipped"})

    return executed


if __name__ == "__main__":
    run_agent()
