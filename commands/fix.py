from providers.ollama_provider import ask_llm
from utils.file_reader import read_file

def fix(file):

    code = read_file(file)

    prompt = f"""
You are a senior developer.

Fix all syntax or logical errors.

Return only corrected code.

CODE:
{code}
"""

    result = ask_llm(prompt, model="deepseek-coder:6.7b")

    print(result)
