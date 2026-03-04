import os

EXT = [".py",".js",".ts",".json",".html",".css"]

EXCLUDE = ["venv",".git","__pycache__"]

def scan_project(path):

    files = []

    for root, dirs, fs in os.walk(path):

        dirs[:] = [d for d in dirs if d not in EXCLUDE]

        for f in fs:

            if any(f.endswith(e) for e in EXT):

                p = os.path.join(root,f)

                try:

                    with open(p,"r",encoding="utf-8") as file:

                        files.append({
                            "path":p,
                            "content":file.read()[:2000]
                        })

                except:
                    pass

    return files
