import os

def write_file(path, content):

    folder = os.path.dirname(path)

    if folder and not os.path.exists(folder):
        os.makedirs(folder)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[AI] wrote file: {path}")
