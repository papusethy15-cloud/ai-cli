from providers.ollama_provider import ask_llm
from utils.project_scanner import scan_project
from utils.file_writer import write_file
from utils.file_editor import edit_file
from utils.shell_runner import run_shell

import json
import re


def run_agent():

    goal = input("What do you want to build or fix? > ")

    files = scan_project(".")

    context = ""

    for f in files:
        context += f"\nFILE:{f['path']}\n{f['content']}\n"

    prompt = f"""
You are an autonomous coding agent.

User goal:
{goal}

Project files:
{context}

You must return a JSON array of actions.

Available actions:

create_file(path,content)
edit_file(path,content)
run_shell(command)

Example:

[
  {{
    "action":"create_file",
    "path":"hello.py",
    "content":"print('hello world')"
  }},
  {{
    "action":"run_shell",
    "command":"python hello.py"
  }}
]

Return ONLY JSON.
No explanation.
No markdown.
"""

    result = ask_llm(prompt)

    print("\nAI Output:\n")
    print(result)

    try:

        plan = json.loads(result)

    except:

        # Try extracting JSON if the model added extra text
        match = re.search(r'\[.*\]', result, re.S)

        if match:
            try:
                plan = json.loads(match.group())
            except:
                print("[Agent] JSON parsing failed")
                fallback(goal)
                return
        else:
            fallback(goal)
            return

    for step in plan:

        action = step.get("action")

        if action == "create_file":
            write_file(step["path"], step["content"])

        elif action == "edit_file":
            edit_file(step["path"], step["content"])

        elif action == "run_shell":
            run_shell(step["command"])


def fallback(goal):

    print("[Agent] Using fallback planner")

    goal = goal.lower()

    if "create" in goal and ".py" in goal:

        words = goal.split()

        for w in words:
            if ".py" in w:

                filename = w

                write_file(filename, "print('hello world')")
                return
