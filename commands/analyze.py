from utils.project_scanner import scan_project
from providers.ollama_provider import ask_llm

def analyze(path):

    files = scan_project(path)

    context = ""

    for f in files:

        context += f"\nFILE:{f['path']}\n{f['content']}\n"

    prompt = f"""
Analyze this software project.

Explain:

1. Project purpose
2. Architecture
3. Improvements

PROJECT:
{context}
"""

    result = ask_llm(prompt, model="qwen2:1.5b")

    print(result)
