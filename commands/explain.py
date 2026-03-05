from providers.ollama_provider import ask_llm
from utils.file_reader import read_file
from config import ANALYSIS_MODEL

def explain(file):

    code = read_file(file)

    prompt = f"""
Explain this code clearly.

CODE:
{code}
"""

    # Explanation is an analysis task, so use the analysis model.
    result = ask_llm(prompt, model=ANALYSIS_MODEL)

    print(result)
