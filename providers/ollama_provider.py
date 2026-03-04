import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

def ask_llm(prompt, model="qwen2:1.5b"):

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    r = requests.post(OLLAMA_URL, json=payload)

    if r.status_code != 200:
        return "Error contacting Ollama"

    return r.json()["response"]
