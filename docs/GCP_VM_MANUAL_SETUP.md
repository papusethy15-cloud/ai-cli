# GCP VM Manual Setup Guide

This guide shows how to run AI CLI API on a Google Cloud VM and use it from your local machine.

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
```

Run API:

```bash
python main.py serve-api-server
```

## B) Recommended Secure Access (SSH Tunnel)

From your local machine:

```bash
gcloud compute ssh <VM_NAME> --zone <ZONE> -- -L 8787:127.0.0.1:8787
```

Use `http://127.0.0.1:8787` on your local machine after tunnel is open.

## C) Local Client Setup

```bash
git clone <REPO_URL> ~/ai-cli-client
cd ~/ai-cli-client
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Optional global alias command:

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/aicli <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
source "$HOME/ai-cli-client/venv/bin/activate"
exec python "$HOME/ai-cli-client/main.py" "$@"
EOS
chmod +x ~/.local/bin/aicli
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
echo 'export AI_CLI_REMOTE_URL="http://127.0.0.1:8787"' >> ~/.bashrc
echo 'export AI_CLI_REMOTE_API_KEY="CHANGE_ME_STRONG_KEY"' >> ~/.bashrc
source ~/.bashrc
```

## D) Test Remote Access

```bash
aicli remote-health-check
aicli remote-memory-cache stats
aicli remote-analyze-project /home/paleienterprises43/ai-cli --no-use-llm
```

## E) systemd Service (API Auto Start)

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

### Model errors
- Ensure Ollama is running on VM:
  ```bash
  ollama serve
  ollama list
  ```
