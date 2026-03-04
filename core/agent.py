from providers.ollama_provider import ask_llm
from utils.project_scanner import scan_project

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

Project context:
{context}

Explain step-by-step what should be done.
"""

    result = ask_llm(prompt, model="qwen2:1.5b")

    print("\nAgent Plan:\n")

    print(result)
