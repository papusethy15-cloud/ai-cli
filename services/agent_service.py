import os

from core.agent import (
    MAX_STEPS,
    _build_project_brief,
    _generate_project_plan,
    _issue_context,
    execute_plan,
    parse_json,
)
from providers.ollama_provider import ask_coder
from utils.code_analyzer import analyze_project as analyze_project_issues
from utils.project_scanner import scan_project


def _emit(on_event, event):
    if not on_event:
        return
    try:
        on_event(event)
    except Exception:
        pass


def _project_goal_with_plan(goal, project_details=None, auto_plan=True):
    if not auto_plan:
        return goal, None
    if not project_details:
        return goal, None

    brief = _build_project_brief(goal, project_details)
    plan = _generate_project_plan(brief, project_details)
    return f"{brief}\n\nImplementation plan to follow:\n{plan}", plan


def run_agent_goal(goal, project_details=None, max_steps=None, auto_plan=True, on_event=None):
    if not goal or not goal.strip():
        return {"ok": False, "error": "Goal is required."}

    effective_steps = max_steps if isinstance(max_steps, int) and max_steps > 0 else MAX_STEPS
    prompt_goal, plan_text = _project_goal_with_plan(
        goal.strip(),
        project_details=project_details,
        auto_plan=auto_plan,
    )

    previous_plan = None
    execution_log = []
    status = "incomplete"
    _emit(
        on_event,
        {
            "type": "agent_started",
            "goal": goal,
            "max_steps": effective_steps,
            "project_plan": plan_text,
        },
    )

    for step_index in range(effective_steps):
        step_number = step_index + 1
        _emit(on_event, {"type": "step_started", "step": step_number, "max_steps": effective_steps})

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
        _emit(
            on_event,
            {
                "type": "analysis_ready",
                "step": step_number,
                "files_scanned": len(analysis_results),
                "files_with_issues": len(issue_paths),
            },
        )

        files = scan_project(".")
        prioritized = []
        for file_info in files:
            rel = os.path.relpath(os.path.abspath(file_info["path"]), os.getcwd())
            priority = 0 if rel in issue_paths else 1
            prioritized.append((priority, rel, file_info))
        prioritized.sort(key=lambda x: (x[0], x[1]))

        context = ""
        for _, _, file_info in prioritized[:25]:
            context += f"\nFILE:{file_info['path']}\n{file_info['content'][:500]}\n"

        prompt = f"""
You are an AI coding agent.

Goal:
{prompt_goal}

Current project files:
{context}

Known analyzer issues (prioritize fixing these first):
{issues_summary}

You must respond ONLY with a JSON array of actions.

DO NOT explain.
DO NOT write code blocks.
DO NOT write text.

Available actions:
create_file
edit_file
run_shell

If the task is already complete, return:
[]
"""
        result = ask_coder(prompt)
        _emit(
            on_event,
            {
                "type": "model_output_received",
                "step": step_number,
                "preview": result[:400],
                "length": len(result),
            },
        )
        plan = parse_json(result)

        if plan == []:
            status = "completed"
            _emit(on_event, {"type": "step_completed", "step": step_number, "status": status})
            break

        if not isinstance(plan, list):
            status = "failed_invalid_plan"
            _emit(
                on_event,
                {
                    "type": "agent_failed",
                    "step": step_number,
                    "status": status,
                    "error": "No valid plan returned by model.",
                },
            )
            return {
                "ok": False,
                "status": status,
                "error": "No valid plan returned by model.",
                "model_output": result,
                "execution_log": execution_log,
                "project_plan": plan_text,
            }

        if plan == previous_plan:
            status = "completed_repeated_plan"
            _emit(
                on_event,
                {
                    "type": "step_completed",
                    "step": step_number,
                    "status": status,
                },
            )
            break
        previous_plan = plan

        _emit(on_event, {"type": "plan_received", "step": step_number, "actions": len(plan)})
        executed = execute_plan(plan)
        execution_log.extend(executed)
        _emit(
            on_event,
            {
                "type": "actions_executed",
                "step": step_number,
                "executed_count": len(executed),
                "executed": executed,
            },
        )
    else:
        status = "max_steps_reached"
        _emit(on_event, {"type": "agent_warning", "status": status})

    _emit(
        on_event,
        {
            "type": "agent_finished",
            "status": status,
            "ok": status.startswith("completed"),
            "actions_total": len(execution_log),
        },
    )

    return {
        "ok": status.startswith("completed"),
        "status": status,
        "goal": goal,
        "project_plan": plan_text,
        "execution_log": execution_log,
    }
