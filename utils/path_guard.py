import os
from pathlib import Path

from config import WORKSPACE_ROOT


class WorkspacePathError(Exception):
    pass


def normalize_workspace_root(root: str | None = None) -> Path:
    base = root or WORKSPACE_ROOT
    return Path(base).expanduser().resolve()


def resolve_in_workspace(
    requested_path: str,
    *,
    workspace_root: str | None = None,
    require_exists: bool = False,
    require_file: bool = False,
    require_dir: bool = False,
) -> str:
    if not requested_path or not requested_path.strip():
        raise WorkspacePathError("Path is required.")

    root = normalize_workspace_root(workspace_root)
    raw = Path(requested_path.strip()).expanduser()
    candidate = raw.resolve() if raw.is_absolute() else (root / raw).resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        raise WorkspacePathError(
            f"Path '{requested_path}' is outside allowed workspace root '{root}'."
        ) from None

    if require_exists and not candidate.exists():
        raise WorkspacePathError(f"Path not found: {candidate}")
    if require_file and not candidate.is_file():
        raise WorkspacePathError(f"Expected a file path, got: {candidate}")
    if require_dir and not candidate.is_dir():
        raise WorkspacePathError(f"Expected a directory path, got: {candidate}")

    return os.path.abspath(str(candidate))
