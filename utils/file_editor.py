import os

def edit_file(path, content):

    if not os.path.exists(path):

        print(f"[AI] file not found: {path}")
        return

    with open(path, "w", encoding="utf-8") as f:

        f.write(content)

    print(f"[AI] updated file: {path}")
