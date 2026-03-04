from providers.ollama_provider import ask_coder
from utils.project_scanner import scan_project
from utils.file_writer import write_file
from utils.file_editor import edit_file
from utils.shell_runner import run_shell

import json
import re


MAX_STEPS = 5


def run_agent():

    goal = input("What do you want to build or fix? > ")

    for step in range(MAX_STEPS):

        print(f"\n===== AGENT STEP {step+1} =====\n")

        files = scan_project(".")

        context = ""

        for f in files:
            context += f"\nFILE:{f['path']}\n{f['content'][:500]}\n"

        prompt = f"""
You are an AI coding agent.

Goal:
{goal}

Current project files:
{context}

Return ONLY valid JSON.

Example:

[
 {{
  "action":"create_file",
  "path":"numbers.py",
  "content":"for i in range(1,6): print(i)"
 }},
 {{
  "action":"run_shell",
  "command":"python numbers.py"
 }}
]

Available actions:

create_file
edit_file
run_shell

Return JSON only.
No explanation.
No markdown.
"""

        result = ask_coder(prompt)

        print("AI Output:\n")
        print(result)

        plan = parse_json(result)

        if not plan:
            print("[Agent] No valid plan returned")
            return

        execute_plan(plan)

        print("\nStep finished\n")


def parse_json(result):

    try:
        return json.loads(result)

    except:

        match = re.search(r'\[.*\]', result, re.S)

        if match:
            try:
                return json.loads(match.group())
            except:
                return None

        return None


def execute_plan(plan):

    for step in plan:

        action = step.get("action")

        if action == "create_file":

            write_file(step["path"], step["content"])

        elif action == "edit_file":

            edit_file(step["path"], step["content"])

        elif action == "run_shell":

            run_shell(step["command"])
