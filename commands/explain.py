from providers.ollama_provider import ask_llm
from utils.file_reader import read_file

def explain(file):

    code = read_file(file)

    prompt = f"""
Explain this code clearly.

CODE:
{code}
"""

    result = ask_llm(prompt, model="qwen2:1.5b")

    print(result)
