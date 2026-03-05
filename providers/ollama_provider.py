import requests
import os

from config import (
    ANALYSIS_MODEL,
    OUTPUT_MODEL,
    OUTPUT_FALLBACK_MODEL,
    OLLAMA_URL,
    REQUEST_TIMEOUT_SECONDS,
    OLLAMA_KEEP_ALIVE,
)


def ask_llm(prompt, model="deepseek-coder:6.7b", options=None):

    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
    }
    if options:
        data["options"] = options

    try:
        r = requests.post(OLLAMA_URL, json=data, timeout=REQUEST_TIMEOUT_SECONDS)
        r.raise_for_status()
    except requests.Timeout:
        return "[LLM Error] Request to Ollama timed out. Check if the model is running."
    except requests.ConnectionError:
        return "[LLM Error] Could not connect to Ollama at http://localhost:11434."
    except requests.RequestException as e:
        return f"[LLM Error] Request failed: {e}"

    try:
        payload = r.json()
    except ValueError:
        return "[LLM Error] Ollama returned non-JSON output."

    if "response" in payload:
        return payload["response"]

    if "error" in payload:
        return f"[LLM Error] {payload['error']}"

    return "[LLM Error] Ollama returned an unexpected response format."


def ask_planner(prompt):

    # Planner/analyzer path uses the lightweight analysis model.
    return ask_llm(prompt, model=ANALYSIS_MODEL)


def ask_coder(prompt):
    # Coder/output path uses DeepSeek by default, with Qwen fallback.
    primary_model = os.getenv("OLLAMA_CODER_MODEL", OUTPUT_MODEL)
    fallback_model = os.getenv("OLLAMA_CODER_FALLBACK_MODEL", OUTPUT_FALLBACK_MODEL)

    models = [primary_model, fallback_model]
    last_error = "[LLM Error] Coder model request failed."

    for model in models:
        result = ask_llm(prompt, model=model)
        if not result.startswith("[LLM Error]"):
            return result
        last_error = result

    return last_error
