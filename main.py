import typer

from commands.chat import chat
from commands.explain import explain
from commands.fix import fix
from commands.analyze import analyze
from core.agent import run_agent

app = typer.Typer()

@app.command()
def chat_ai():
    chat()

@app.command()
def explain_code(file:str):
    explain(file)

@app.command()
def fix_code(file:str):
    fix(file)

@app.command()
def analyze_project(path:str):
    analyze(path)

@app.command()
def agent():
    run_agent()

if __name__ == "__main__":
    app()
