# GCP VM Manual Setup Guide

This guide shows how to run AI CLI API on a Google Cloud VM and use it from your local machine.

## Ollama Placement (Important)

- VM/server mode (this guide): run Ollama on VM only.
- Local client machine does not need Ollama for `remote-*` commands.
- Local machine needs Ollama only if you run non-remote commands there.

## A) VM Setup

```bash
cd ~/ai-cli
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set API environment values:

```bash
export AI_CLI_API_KEY="CHANGE_ME_STRONG_KEY"
export AI_CLI_API_HOST="0.0.0.0"
export AI_CLI_API_PORT="8787"
export AI_CLI_WORKSPACE_ROOT="/home/paleienterprises43/workspaces"
export AI_CLI_AUTH_USERS_JSON='{"devuser":{"password":"CHANGE_ME_PASSWORD","scopes":["read","write","agent"]}}'
export AI_CLI_AUTH_STATE_PERSIST=true
export AI_CLI_AUTH_STATE_BACKEND=sqlite
export AI_CLI_AUTH_DB_PATH="/home/paleienterprises43/ai-cli/.ai_cli_auth.db"
# Multi-instance option:
# export AI_CLI_AUTH_STATE_BACKEND=redis
# export AI_CLI_AUTH_REDIS_URL="redis://127.0.0.1:6379/0"
# export AI_CLI_AUTH_REDIS_PREFIX="aicli:auth"
# export AI_CLI_AUTH_REDIS_LOCK_TTL_MS=15000
```

Ensure Ollama is running on VM (required for LLM tasks):

```bash
ollama serve
ollama list
```

Run API:

```bash
python main.py serve-api-server
```

## B) Recommended Secure Access (SSH Tunnel)

From your local machine (Linux/macOS terminal or Windows PowerShell):

```bash
gcloud compute ssh <VM_NAME> --zone <ZONE> -- -L 8787:127.0.0.1:8787
```

Use `http://127.0.0.1:8787` on your local machine after tunnel is open.

## C) Local Client Setup

Linux/macOS:

```bash
git clone <REPO_URL> ~/ai-cli-client
cd ~/ai-cli-client
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
git clone <REPO_URL> $HOME\ai-cli-client
cd $HOME\ai-cli-client
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Note: Ollama install is not required on local client when using remote API commands.

Optional one-command bootstrap (recommended, works on Linux/macOS and Windows):

```bash
python3 main.py bootstrap-remote-client --base-url http://127.0.0.1:8787 --api-key "CHANGE_ME_STRONG_KEY"
```

Windows PowerShell bootstrap:

```powershell
py -3 main.py bootstrap-remote-client --base-url http://127.0.0.1:8787 --api-key "CHANGE_ME_STRONG_KEY"
if (Test-Path $PROFILE) { . $PROFILE }
```

Linux/macOS shell refresh:

```bash
source ~/.bashrc
```

## D) Test Remote Access

```bash
aicli setup --mode device --base-url http://127.0.0.1:8787 --username devuser
aicli setup --mode password --base-url http://127.0.0.1:8787 --username devuser
aicli setup --mode api-key --base-url http://127.0.0.1:8787 --api-key "CHANGE_ME_STRONG_KEY"
aicli remote-login
aicli remote-password-login --username devuser
aicli remote-device-login --username devuser
aicli remote-whoami
aicli remote-config
aicli remote-health-check
aicli remote-memory-cache stats
aicli remote-analyze-project /home/paleienterprises43/ai-cli --no-use-llm
aicli remote-agent "build todo api" --workspace-path /home/paleienterprises43/ai-cli --async-mode
```

Windows workspace path example:

```powershell
aicli remote-analyze-project C:\workspaces\ai-cli --no-use-llm
aicli remote-agent "build todo api" --workspace-path C:\workspaces\ai-cli --async-mode
```

## E) systemd Service (API Auto Start)

This section is Linux-only (systemd is not available on Windows).

Copy template files:

- `docs/systemd/aicli-api.service`
- `docs/systemd/aicli-api.env.example`

Install service:

```bash
sudo cp docs/systemd/aicli-api.service /etc/systemd/system/aicli-api.service
sudo cp docs/systemd/aicli-api.env.example /etc/default/aicli-api
sudo chmod 600 /etc/default/aicli-api
sudo systemctl daemon-reload
sudo systemctl enable --now aicli-api
sudo systemctl status aicli-api --no-pager
```

Follow logs:

```bash
journalctl -u aicli-api -f
```

## F) Troubleshooting

### Unit file not found
- Check `/etc/systemd/system/aicli-api.service` exists.
- Run `sudo systemctl daemon-reload` again.

### API not reachable
- Verify service status and logs.
- Verify API key header is sent.
- If no tunnel, verify firewall for TCP 8787.
- Verify `AI_CLI_WORKSPACE_ROOT` points to an existing directory.

### Model errors
- Ensure Ollama is running on VM:
  ```bash
  ollama serve
  ollama list
  ```
