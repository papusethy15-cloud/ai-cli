from pathlib import Path


class FileReadError(Exception):
    pass


def read_file(path, encoding="utf-8", errors="strict", max_chars=None):
    target = Path(path)

    if not target.exists():
        raise FileReadError(f"File not found: {path}")
    if not target.is_file():
        raise FileReadError(f"Path is not a file: {path}")

    try:
        content = target.read_text(encoding=encoding, errors=errors)
    except UnicodeDecodeError:
        raise FileReadError(
            f"Could not decode file with encoding '{encoding}': {path}"
        ) from None
    except OSError as e:
        raise FileReadError(f"Failed to read file '{path}': {e}") from e

    if max_chars is not None:
        return content[:max_chars]
    return content
