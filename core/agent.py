from providers.ollama_provider import ask_llm
from utils.project_scanner import scan_project
from utils.file_writer import write_file

import json
import re

def run_agent():

    goal = input("What do you want to build or fix? > ")

    files = scan_project(".")

    context = ""

    for f in files:
        context += f"\nFILE:{f['path']}\n{f['content']}\n"

    prompt = f"""
You are an autonomous software engineer.

User goal:
{goal}

Return ONLY JSON like this:

[
  {{
    "action": "create_file",
    "path": "hello.py",
    "content": "print('hello world')"
  }}
]

Do not explain anything.
Return only JSON.
"""

    result = ask_llm(prompt)

    print("\nAI Output:\n")
    print(result)

    # Try normal JSON parsing first
    try:

        plan = json.loads(result)

    except:

        # Try extracting JSON block if model added extra text
        match = re.search(r'\[.*\]', result, re.S)

        if match:
            try:
                plan = json.loads(match.group())
            except:
                print("\n[Agent] Could not parse JSON")
                return
        else:
            print("\n[Agent] No JSON found in response")
            return

    for step in plan:

        if step["action"] == "create_file":

            write_file(step["path"], step["content"])
