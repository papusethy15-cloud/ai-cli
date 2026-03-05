import os
import shlex
import subprocess

from config import ALLOWED_SHELL_COMMANDS, BLOCKED_SHELL_TOKENS


def _normalize_command_name(binary):
    return os.path.basename(binary.strip())


def _validate_safe_command(command):
    for token in BLOCKED_SHELL_TOKENS:
        token = token.strip()
        if token and token in command:
            return None, f"blocked token detected: {token}"

    try:
        argv = shlex.split(command)
    except ValueError as e:
        return None, f"invalid shell syntax: {e}"

    if not argv:
        return None, "empty command"

    cmd_name = _normalize_command_name(argv[0])
    if cmd_name not in set(ALLOWED_SHELL_COMMANDS):
        return None, (
            f"command '{cmd_name}' is not in allowed list. "
            f"Allowed: {', '.join(sorted(ALLOWED_SHELL_COMMANDS))}"
        )
    return argv, None


def run_shell(command, timeout=120, cwd=None):
    if not command or not str(command).strip():
        print("[AI] empty command, skipped")
        return {"ok": False, "error": "empty_command", "command": command}

    print(f"[AI] running command: {command}")
    argv, validation_error = _validate_safe_command(str(command))
    if validation_error:
        print(f"[AI] blocked command: {validation_error}")
        return {
            "ok": False,
            "error": "blocked_command",
            "details": validation_error,
            "command": command,
        }

    try:
        result = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        print(f"[AI] command timed out after {timeout}s")
        return {"ok": False, "error": "timeout", "command": command}
    except Exception as e:
        print(f"[AI] command failed: {e}")
        return {"ok": False, "error": str(e), "command": command}

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return {
        "ok": result.returncode == 0,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
