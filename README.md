# AI CLI

AI CLI is a local/remote coding assistant with:
- Project analysis
- File and project fixing
- Interactive agent mode
- Memory cache
- HTTP API for remote usage
- Remote CLI commands for API access
- Workspace-scoped execution guard
- Scoped API authentication (`read`, `write`, `agent`)

## Ollama Requirement (Important)

- If you run CLI commands directly on a machine (`chat-ai`, `agent`, `fix-code`), that same machine needs Ollama.
- If you run remote commands (`remote-*`) against a VM API server, only the VM needs Ollama.
- Local client machine does **not** need Ollama in remote-only usage.

## 1) Quick Start (Local)

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
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

Optional install as command (Linux/macOS):

```bash
pip install -e .
aicli --help
```

Optional install as command (Windows PowerShell):

```powershell
python -m pip install -e .
.\venv\Scripts\aicli.exe --help
```

## 2) API Server

Start API server (Linux/macOS):

```bash
export AI_CLI_API_KEY="CHANGE_ME_STRONG_KEY"
export AI_CLI_API_HOST="0.0.0.0"
export AI_CLI_API_PORT="8787"
export AI_CLI_WORKSPACE_ROOT="/home/ubuntu/workspaces"
export AI_CLI_AUTH_USERS_JSON='{
  "devuser": {"password": "CHANGE_ME_PASSWORD", "scopes": ["read","write","agent"]}
}'
export AI_CLI_AUTH_STATE_PERSIST=true
export AI_CLI_AUTH_STATE_BACKEND=sqlite
export AI_CLI_AUTH_DB_PATH="/home/ubuntu/ai-cli/.ai_cli_auth.db"
python main.py serve-api-server
```

Start API server (Windows PowerShell):

```powershell
$env:AI_CLI_API_KEY="CHANGE_ME_STRONG_KEY"
$env:AI_CLI_API_HOST="0.0.0.0"
$env:AI_CLI_API_PORT="8787"
$env:AI_CLI_WORKSPACE_ROOT="C:\workspaces"
$env:AI_CLI_AUTH_USERS_JSON='{"devuser":{"password":"CHANGE_ME_PASSWORD","scopes":["read","write","agent"]}}'
$env:AI_CLI_AUTH_STATE_PERSIST="true"
$env:AI_CLI_AUTH_STATE_BACKEND="sqlite"
$env:AI_CLI_AUTH_DB_PATH="C:\ai-cli\.ai_cli_auth.db"
python main.py serve-api-server
```

Health check:

```bash
curl -H "x-api-key: $AI_CLI_API_KEY" http://127.0.0.1:8787/health
```

Who am I check:

```bash
curl -H "x-api-key: $AI_CLI_API_KEY" http://127.0.0.1:8787/auth/whoami
```

### Multi-user Scoped Tokens (Optional)

You can define multiple API tokens with scopes:

```bash
export AI_CLI_AUTH_TOKENS_JSON='{
  "token_read_only": {"user_id": "viewer", "scopes": ["read"]},
  "token_writer": {"user_id": "developer", "scopes": ["read","write","agent"]}
}'
```

If no auth tokens are configured, server startup defaults to protected mode and rejects requests
until you set a token. Use `AI_CLI_ALLOW_NO_AUTH=true` only for local dev.

### Device/Password Login (Phase 2)

You can authenticate users via password or device-code flow (then CLI uses bearer access tokens):

```bash
python main.py remote-password-login --base-url http://127.0.0.1:8787 --username devuser
python main.py remote-device-login --base-url http://127.0.0.1:8787 --username devuser
python main.py remote-whoami
```

### Persistent Auth Sessions (Phase 3)

- Access/refresh/device auth state is persisted in SQLite by default.
- Configure with:
  - `AI_CLI_AUTH_STATE_PERSIST=true|false`
  - `AI_CLI_AUTH_DB_PATH=/path/to/.ai_cli_auth.db`
- This keeps active sessions across API restarts.

### Multi-Instance Auth State (Phase 4)

- For multiple API instances, use Redis backend with distributed state lock:
  - `AI_CLI_AUTH_STATE_BACKEND=redis`
  - `AI_CLI_AUTH_REDIS_URL=redis://127.0.0.1:6379/0`
  - `AI_CLI_AUTH_REDIS_PREFIX=aicli:auth`
  - `AI_CLI_AUTH_REDIS_LOCK_TTL_MS=15000`
- Single-instance/default remains SQLite:
  - `AI_CLI_AUTH_STATE_BACKEND=sqlite`

## 3) Remote CLI Commands

First-time login (saves credentials to `~/.ai-cli/config.json` on Linux/macOS and `%USERPROFILE%\.ai-cli\config.json` on Windows):

```bash
python main.py setup --mode device --base-url http://127.0.0.1:8787 --username devuser
python main.py setup --mode password --base-url http://127.0.0.1:8787 --username devuser
python main.py setup --mode api-key --base-url http://127.0.0.1:8787 --api-key "$AI_CLI_API_KEY"
python main.py remote-login --base-url http://127.0.0.1:8787 --api-key "$AI_CLI_API_KEY"
python main.py remote-password-login --base-url http://127.0.0.1:8787 --username devuser
python main.py remote-device-login --base-url http://127.0.0.1:8787 --username devuser
python main.py remote-whoami
python main.py remote-config
```

Then run remote commands without repeating `--base-url/--api-key`:

```bash
python main.py remote-health-check
python main.py remote-analyze-project /path/on/server
python main.py remote-agent "build todo api" --workspace-path /path/on/server --async-mode
python main.py remote-job-stream-logs <JOB_ID>
```

## 4) One Command VM Client Bootstrap

If the user wants a RovoDev-like local terminal that controls a VM, run:

Linux/macOS:

```bash
python3 main.py bootstrap-remote-client --base-url http://127.0.0.1:8787 --api-key "CHANGE_ME_STRONG_KEY"
source ~/.bashrc
```

Windows (PowerShell):

```powershell
py -3 main.py bootstrap-remote-client --base-url http://127.0.0.1:8787 --api-key "CHANGE_ME_STRONG_KEY"
if (Test-Path $PROFILE) { . $PROFILE }
```

What this command does:
- Creates/reuses `venv/`
- Installs `requirements.txt`
- Installs editable CLI package (`pip install -e .`)
- Creates command wrapper:
  - Linux/macOS: `~/.local/bin/aicli`
  - Windows: `%USERPROFILE%\.local\bin\aicli.cmd`
- Saves remote URL/API key to CLI config file
- Adds `PATH` and remote env exports to shell profile (`.bashrc`/`.zshrc` or PowerShell profile)

If user has not downloaded the repo yet:

```bash
git clone <REPO_URL> ~/ai-cli-client
cd ~/ai-cli-client
python3 main.py bootstrap-remote-client --base-url http://127.0.0.1:8787 --api-key "CHANGE_ME_STRONG_KEY"
source ~/.bashrc
```

Windows clone/bootstrap example:

```powershell
git clone <REPO_URL> $HOME\ai-cli-client
cd $HOME\ai-cli-client
py -3 main.py bootstrap-remote-client --base-url http://127.0.0.1:8787 --api-key "CHANGE_ME_STRONG_KEY"
if (Test-Path $PROFILE) { . $PROFILE }
```

## 5) RovoDev Style Command Mapping

- Start interactive local coding agent: `aicli agent`
- Start interactive local chat assistant: `aicli chat-ai`
- Analyze current project quickly: `aicli analyze-project . --no-use-llm`
- Login/setup remote VM session: `aicli setup --mode device --base-url http://127.0.0.1:8787 --username devuser`
- Check VM API health: `aicli remote-health-check`
- Check active remote identity: `aicli remote-whoami`
- Run coding agent on VM workspace: `aicli remote-agent "build todo api" --workspace-path /path/on/vm --async-mode`
- Watch async job logs: `aicli remote-job-stream-logs <JOB_ID>`
- Analyze VM project path: `aicli remote-analyze-project /path/on/vm`
- Fix VM file/project: `aicli remote-fix-code /path/on/vm/file.py --apply` and `aicli remote-fix-project-code /path/on/vm --apply`

## 6) Important Notes

- Remote `path` values are resolved on the server machine, not your local machine.
- For Windows remote paths, use Windows format (example: `C:\workspaces\my-app`).
- Keep API key secret.
- Use SSH tunnel for secure remote access when possible.
- In remote mode, Ollama must run on the server/VM only.
- Remote paths are restricted to `AI_CLI_WORKSPACE_ROOT`.
- Agent shell commands are safety-filtered and run with an allowlist.

See full manual deployment guide in `docs/GCP_VM_MANUAL_SETUP.md`.
