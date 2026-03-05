from pathlib import Path


def edit_file(path, content, encoding="utf-8"):
    target = Path(path)

    if not target.exists() or not target.is_file():
        print(f"[AI] file not found: {path}")
        return False

    try:
        target.write_text(content, encoding=encoding)
    except OSError as e:
        print(f"[AI] failed to update file: {path} ({e})")
        return False

    print(f"[AI] updated file: {path}")
    return True
