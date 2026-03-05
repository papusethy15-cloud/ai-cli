import os

EXT = [".py",".js",".ts",".json",".html",".css"]

EXCLUDE = ["venv",".git","__pycache__"]


def list_project_files(path, extensions=None):

    extensions = extensions or EXT
    paths = []

    for root, dirs, fs in os.walk(path):

        dirs[:] = [d for d in dirs if d not in EXCLUDE]

        for f in fs:

            if any(f.endswith(e) for e in extensions):

                paths.append(os.path.join(root, f))

    return sorted(paths)

def scan_project(path):

    files = []

    for p in list_project_files(path, extensions=EXT):

        try:

            with open(p,"r",encoding="utf-8") as file:

                files.append({
                    "path":p,
                    "content":file.read()[:2000]
                })

        except Exception:
            pass

    return files
