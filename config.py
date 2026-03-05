import os

# Model routing used across the project:
# - ANALYSIS_MODEL: lightweight model for understanding/explaining code.
# - OUTPUT_MODEL: stronger coding model for generating/fixing code output.
ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "qwen2:1.5b")
OUTPUT_MODEL = os.getenv("OUTPUT_MODEL", "deepseek-coder:6.7b")
OUTPUT_FALLBACK_MODEL = os.getenv("OUTPUT_FALLBACK_MODEL", ANALYSIS_MODEL)
# - CHAT_MODEL: defaults to the faster analysis model for snappy chat.
CHAT_MODEL = os.getenv("CHAT_MODEL", ANALYSIS_MODEL)
CHAT_NUM_PREDICT = int(os.getenv("CHAT_NUM_PREDICT", "128"))

# Ollama connection settings.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))
# Keep model loaded between requests to reduce repeated cold starts.
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
