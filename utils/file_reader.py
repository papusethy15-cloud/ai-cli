import os

def read_file(path):

    if not os.path.exists(path):
        print("File not found")
        exit()

    with open(path,"r",encoding="utf-8") as f:
        return f.read()
