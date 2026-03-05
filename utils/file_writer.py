from pathlib import Path


def write_file(path, content, encoding="utf-8"):
    target = Path(path)

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)
    except OSError as e:
        print(f"[AI] failed to write file: {path} ({e})")
        return False

    print(f"[AI] wrote file: {path}")
    return True
