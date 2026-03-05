import subprocess


def run_shell(command, timeout=120):
    if not command or not str(command).strip():
        print("[AI] empty command, skipped")
        return {"ok": False, "error": "empty_command", "command": command}

    print(f"[AI] running command: {command}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
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
