# AI CLI

AI CLI is a local/remote coding assistant with:
- Project analysis
- File and project fixing
- Interactive agent mode
- Memory cache
- HTTP API for remote usage
- Remote CLI commands for API access

## Ollama Requirement (Important)

- If you run CLI commands directly on a machine (`chat-ai`, `agent`, `fix-code`), that same machine needs Ollama.
- If you run remote commands (`remote-*`) against a VM API server, only the VM needs Ollama.
- Local client machine does **not** need Ollama in remote-only usage.

## 1) Quick Start (Local)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Start Ollama in another terminal (only for local execution mode):

```bash
ollama serve
```

Run CLI:

```bash
python main.py --help
python main.py analyze-project . --no-use-llm
python main.py chat-ai
```

## 2) API Server

Start API server:

```bash
export AI_CLI_API_KEY="CHANGE_ME_STRONG_KEY"
export AI_CLI_API_HOST="0.0.0.0"
export AI_CLI_API_PORT="8787"
python main.py serve-api-server
```

Health check:

```bash
curl -H "x-api-key: $AI_CLI_API_KEY" http://127.0.0.1:8787/health
```

## 3) Remote CLI Commands

```bash
python main.py remote-health-check --base-url http://127.0.0.1:8787 --api-key "$AI_CLI_API_KEY"
python main.py remote-analyze-project /path/on/server --base-url http://127.0.0.1:8787 --api-key "$AI_CLI_API_KEY"
python main.py remote-agent "build todo api" --async-mode --base-url http://127.0.0.1:8787 --api-key "$AI_CLI_API_KEY"
python main.py remote-job-stream-logs <JOB_ID> --base-url http://127.0.0.1:8787 --api-key "$AI_CLI_API_KEY"
```

## 4) Important Notes

- Remote `path` values are resolved on the server machine, not your local machine.
- Keep API key secret.
- Use SSH tunnel for secure remote access when possible.
- In remote mode, Ollama must run on the server/VM only.

See full manual deployment guide in `docs/GCP_VM_MANUAL_SETUP.md`.
