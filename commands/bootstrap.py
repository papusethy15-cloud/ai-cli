from pathlib import Path
import os
import re
import shlex
import stat
import subprocess

from utils.cli_config import set_saved_remote


class BootstrapError(RuntimeError):
    pass


def _run(cmd):
    printable = " ".join(shlex.quote(str(part)) for part in cmd)
    print(f"[bootstrap] {printable}")
    completed = subprocess.run(cmd, check=False)
    if completed.returncode != 0:
        raise BootstrapError(f"Command failed ({completed.returncode}): {printable}")


def _escape_shell_value(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _escape_powershell_value(value):
    return value.replace("`", "``").replace('"', '`"')


def _is_windows():
    return os.name == "nt"


def _resolve_shell_rc(shell_rc):
    if shell_rc:
        return Path(shell_rc).expanduser()
    if _is_windows():
        return Path.home() / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
    shell_env = os.getenv("SHELL", "").strip()
    if shell_env.endswith("zsh"):
        return Path.home() / ".zshrc"
    return Path.home() / ".bashrc"


def _append_line_if_missing(path, line):
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if line in existing.splitlines():
            return False

    with path.open("a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(f"{line}\n")
    return True


def _write_wrapper(wrapper_path, python_bin, main_py):
    wrapper_path.parent.mkdir(parents=True, exist_ok=True)
    if _is_windows():
        if wrapper_path.suffix.lower() != ".cmd":
            wrapper_path = wrapper_path.with_suffix(".cmd")
        content = (
            "@echo off\r\n"
            f'"{python_bin}" "{main_py}" %*\r\n'
        )
        wrapper_path.write_text(content, encoding="utf-8")
        return wrapper_path

    content = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f'exec {shlex.quote(str(python_bin))} {shlex.quote(str(main_py))} "$@"\n'
    )
    wrapper_path.write_text(content, encoding="utf-8")
    mode = wrapper_path.stat().st_mode
    wrapper_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return wrapper_path


def _upsert_block(path, start_marker, end_marker, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    block_body = "\n".join(lines)
    block = f"{start_marker}\n{block_body}\n{end_marker}\n"
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker) + r"\n?", re.DOTALL)
    if pattern.search(existing):
        updated = pattern.sub(block, existing)
    else:
        updated = existing
        if updated and not updated.endswith("\n"):
            updated += "\n"
        if updated:
            updated += "\n"
        updated += block
    path.write_text(updated, encoding="utf-8")


def bootstrap_remote_client_setup(
    *,
    base_url="",
    api_key="",
    python_bin="python3",
    command_name="aicli",
    shell_rc="",
    install_command=True,
    install_editable=True,
    project_root=None,
):
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent
    else:
        project_root = Path(project_root).expanduser().resolve()
    requirements = project_root / "requirements.txt"
    main_py = project_root / "main.py"
    venv_path = project_root / "venv"
    venv_bin_dir = "Scripts" if _is_windows() else "bin"
    venv_python_name = "python.exe" if _is_windows() else "python"
    venv_pip_name = "pip.exe" if _is_windows() else "pip"
    venv_python = venv_path / venv_bin_dir / venv_python_name
    venv_pip = venv_path / venv_bin_dir / venv_pip_name

    if not requirements.exists():
        raise BootstrapError(f"Missing requirements file: {requirements}")
    if not main_py.exists():
        raise BootstrapError(f"Missing CLI entrypoint: {main_py}")

    if not venv_python.exists() or not venv_pip.exists():
        _run([python_bin, "-m", "venv", str(venv_path)])
    else:
        print(f"[bootstrap] Reusing existing virtualenv at {venv_path}")

    _run([str(venv_pip), "install", "-r", str(requirements)])

    if install_editable:
        _run([str(venv_python), "-m", "pip", "install", "-e", str(project_root)])

    rc_path = None
    wrapper_path = None
    if install_command:
        wrapper_path = Path.home() / ".local" / "bin" / command_name
        rc_path = _resolve_shell_rc(shell_rc)
        if _is_windows():
            lines = [
                '$AicliBin = Join-Path $HOME ".local\\bin"',
                'if (-not (($env:Path -split ";") -contains $AicliBin)) { $env:Path = "$AicliBin;$env:Path" }',
            ]
            if base_url:
                value = _escape_powershell_value(base_url.strip())
                lines.append(f'$env:AI_CLI_REMOTE_URL = "{value}"')
            if api_key:
                value = _escape_powershell_value(api_key.strip())
                lines.append(f'$env:AI_CLI_REMOTE_API_KEY = "{value}"')
            _upsert_block(
                rc_path,
                "# >>> AI_CLI_BOOTSTRAP >>>",
                "# <<< AI_CLI_BOOTSTRAP <<<",
                lines,
            )
        else:
            _append_line_if_missing(rc_path, 'export PATH="$HOME/.local/bin:$PATH"')
            if base_url:
                value = _escape_shell_value(base_url.strip())
                _append_line_if_missing(rc_path, f'export AI_CLI_REMOTE_URL="{value}"')
            if api_key:
                value = _escape_shell_value(api_key.strip())
                _append_line_if_missing(rc_path, f'export AI_CLI_REMOTE_API_KEY="{value}"')
        wrapper_path = _write_wrapper(wrapper_path, venv_python, main_py)

    if base_url or api_key:
        set_saved_remote(
            base_url=base_url.strip() if base_url else None,
            api_key=api_key.strip() if api_key else None,
        )

    print("\nBootstrap complete.")
    print(f"- Project: {project_root}")
    print(f"- Virtualenv: {venv_path}")
    if wrapper_path:
        print(f"- Command wrapper: {wrapper_path}")
    if rc_path:
        print(f"- Shell profile updated: {rc_path}")
    if base_url:
        print(f"- Remote URL saved: {base_url}")
    if api_key:
        print("- Remote API key saved.")
    print("\nNext commands:")
    if _is_windows():
        print(f"- {venv_path}\\Scripts\\Activate.ps1")
    else:
        print(f"- source {venv_path}/bin/activate")
    if install_command:
        print(f"- {command_name} remote-health-check")
        print(f'- {command_name} remote-agent "build todo api" --workspace-path /path/on/vm --async-mode')
    else:
        print(f"- {venv_python} {main_py} remote-health-check")
