import requests

OLLAMA_URL = "http://localhost:11434/api/generate"


def ask_llm(prompt, model="deepseek-coder:6.7b"):

    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    r = requests.post(OLLAMA_URL, json=data)

    return r.json()["response"]


def ask_planner(prompt):

    return ask_llm(prompt, model="qwen2:1.5b")


def ask_coder(prompt):

    return ask_llm(prompt, model="deepseek-coder:6.7b")
