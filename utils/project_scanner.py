import os
from pathlib import Path

EXT = [".py", ".js", ".ts", ".json", ".html", ".css"]
EXCLUDE = [
    "venv",
    ".venv",
    ".git",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    "dist",
    "build",
]
MAX_FILE_SIZE_BYTES = 1_000_000
SCAN_READ_LIMIT = 2000


def list_project_files(path, extensions=None):
    extensions = [e.lower() for e in (extensions or EXT)]
    paths = []

    for root, dirs, fs in os.walk(path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE]

        for name in fs:
            if Path(name).suffix.lower() in extensions:
                paths.append(os.path.join(root, name))

    return sorted(paths)


def scan_project(path):
    files = []

    for file_path in list_project_files(path, extensions=EXT):
        try:
            if os.path.getsize(file_path) > MAX_FILE_SIZE_BYTES:
                continue
            with open(file_path, "r", encoding="utf-8") as file:
                files.append(
                    {
                        "path": file_path,
                        "content": file.read()[:SCAN_READ_LIMIT],
                    }
                )
        except Exception:
            continue

    return files
