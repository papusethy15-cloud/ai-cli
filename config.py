import os


def _env_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name, default_values):
    raw = os.getenv(name)
    if raw is None:
        return list(default_values)
    values = [item.strip() for item in raw.split(",")]
    return [item for item in values if item]


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

# API server settings.
API_HOST = os.getenv("AI_CLI_API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("AI_CLI_API_PORT", "8787"))
API_KEY = os.getenv("AI_CLI_API_KEY", "")
ALLOW_NO_AUTH = _env_bool("AI_CLI_ALLOW_NO_AUTH", False)
AUTH_TOKENS_JSON = os.getenv("AI_CLI_AUTH_TOKENS_JSON", "")
AUTH_USERS_JSON = os.getenv("AI_CLI_AUTH_USERS_JSON", "")
DEVICE_AUTH_ENABLED = _env_bool("AI_CLI_DEVICE_AUTH_ENABLED", True)
AUTH_STATE_PERSIST = _env_bool("AI_CLI_AUTH_STATE_PERSIST", True)
AUTH_STATE_BACKEND = os.getenv("AI_CLI_AUTH_STATE_BACKEND", "sqlite").strip().lower()
AUTH_STATE_DB_PATH = os.path.abspath(os.getenv("AI_CLI_AUTH_DB_PATH", ".ai_cli_auth.db"))
AUTH_STATE_REDIS_URL = os.getenv("AI_CLI_AUTH_REDIS_URL", "redis://127.0.0.1:6379/0").strip()
AUTH_STATE_REDIS_PREFIX = os.getenv("AI_CLI_AUTH_REDIS_PREFIX", "aicli:auth").strip()
AUTH_STATE_REDIS_LOCK_TTL_MS = int(os.getenv("AI_CLI_AUTH_REDIS_LOCK_TTL_MS", "15000"))
ACCESS_TOKEN_TTL_SECONDS = int(os.getenv("AI_CLI_ACCESS_TOKEN_TTL_SECONDS", "3600"))
REFRESH_TOKEN_TTL_SECONDS = int(os.getenv("AI_CLI_REFRESH_TOKEN_TTL_SECONDS", "2592000"))
DEVICE_CODE_TTL_SECONDS = int(os.getenv("AI_CLI_DEVICE_CODE_TTL_SECONDS", "600"))
DEVICE_CODE_POLL_INTERVAL_SECONDS = int(os.getenv("AI_CLI_DEVICE_CODE_POLL_INTERVAL_SECONDS", "3"))
API_REQUEST_TIMEOUT_SECONDS = int(os.getenv("AI_CLI_API_REQUEST_TIMEOUT_SECONDS", "180"))
WORKSPACE_ROOT = os.path.abspath(os.getenv("AI_CLI_WORKSPACE_ROOT", os.getcwd()))
MAX_CONCURRENT_JOBS = int(os.getenv("AI_CLI_MAX_CONCURRENT_JOBS", "2"))
MAX_JOB_HISTORY = int(os.getenv("AI_CLI_MAX_JOB_HISTORY", "200"))
MAX_JOB_EVENTS = int(os.getenv("AI_CLI_MAX_JOB_EVENTS", "1000"))

# Remote CLI client defaults.
REMOTE_API_BASE_URL = os.getenv("AI_CLI_REMOTE_URL", f"http://127.0.0.1:{API_PORT}")
REMOTE_API_KEY = os.getenv("AI_CLI_REMOTE_API_KEY", API_KEY)

# Agent shell safety defaults.
ALLOWED_SHELL_COMMANDS = _env_csv(
    "AI_CLI_ALLOWED_SHELL_COMMANDS",
    [
        "python",
        "python3",
        "pytest",
        "pip",
        "pip3",
        "npm",
        "pnpm",
        "node",
        "git",
        "ls",
        "cat",
        "echo",
        "printf",
        "mkdir",
        "touch",
        "cp",
        "mv",
    ],
)
BLOCKED_SHELL_TOKENS = _env_csv(
    "AI_CLI_BLOCKED_SHELL_TOKENS",
    ["&&", "||", ";", "|", "$(", "`", ">", "<", "rm -rf", "shutdown", "reboot"],
)
