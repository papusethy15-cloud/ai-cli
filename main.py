import typer

from commands.chat import chat
from commands.explain import explain
from commands.fix import fix
from commands.fix_project import fix_project
from commands.memory import memory_command
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
def fix_code(
    file: str,
    apply: bool = False,
    refresh: bool = False,
):
    fix(file, apply=apply, refresh=refresh)

@app.command()
def analyze_project(
    path: str,
    use_llm: bool = True,
    refresh: bool = False,
):
    analyze(path, use_llm=use_llm, refresh=refresh)

@app.command()
def fix_project_code(
    path: str,
    apply: bool = False,
    use_llm: bool = False,
    refresh: bool = False,
    max_files: int = 20,
):
    fix_project(
        path,
        apply=apply,
        use_llm=use_llm,
        refresh=refresh,
        max_files=max_files,
    )

@app.command()
def agent():
    run_agent()

@app.command()
def memory(
    action: str = typer.Argument("stats"),
    limit: int = typer.Option(20),
    yes: bool = typer.Option(False),
):
    memory_command(action=action, limit=limit, yes=yes)

if __name__ == "__main__":
    app()
