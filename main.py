import typer

from commands.chat import chat
from commands.explain import explain
from commands.fix import fix
from commands.fix_project import fix_project
from commands.api import serve_api
from commands.memory import memory_command
from commands.remote import (
    remote_agent_run,
    remote_analyze,
    remote_fix_file,
    remote_fix_project,
    remote_health,
    remote_job_events,
    remote_job_stream,
    remote_job,
    remote_memory,
)
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


@app.command()
def serve_api_server():
    serve_api()


@app.command()
def remote_health_check(
    base_url: str = "",
    api_key: str = "",
):
    remote_health(base_url=base_url or None, api_key=api_key or None)


@app.command()
def remote_analyze_project(
    path: str,
    use_llm: bool = True,
    refresh: bool = False,
    base_url: str = "",
    api_key: str = "",
):
    remote_analyze(
        path=path,
        use_llm=use_llm,
        refresh=refresh,
        base_url=base_url or None,
        api_key=api_key or None,
    )


@app.command()
def remote_fix_code(
    path: str,
    apply: bool = False,
    refresh: bool = False,
    base_url: str = "",
    api_key: str = "",
):
    remote_fix_file(
        path=path,
        apply=apply,
        refresh=refresh,
        base_url=base_url or None,
        api_key=api_key or None,
    )


@app.command()
def remote_fix_project_code(
    path: str,
    apply: bool = False,
    use_llm: bool = False,
    refresh: bool = False,
    max_files: int = 20,
    base_url: str = "",
    api_key: str = "",
):
    remote_fix_project(
        path=path,
        apply=apply,
        use_llm=use_llm,
        refresh=refresh,
        max_files=max_files,
        base_url=base_url or None,
        api_key=api_key or None,
    )


@app.command()
def remote_memory_cache(
    action: str = typer.Argument("stats"),
    limit: int = 20,
    yes: bool = False,
    base_url: str = "",
    api_key: str = "",
):
    remote_memory(
        action=action,
        limit=limit,
        yes=yes,
        base_url=base_url or None,
        api_key=api_key or None,
    )


@app.command()
def remote_agent(
    goal: str,
    max_steps: int = 0,
    async_mode: bool = False,
    base_url: str = "",
    api_key: str = "",
):
    remote_agent_run(
        goal=goal,
        max_steps=max_steps if max_steps > 0 else None,
        async_mode=async_mode,
        base_url=base_url or None,
        api_key=api_key or None,
    )


@app.command()
def remote_job_status(
    job_id: str,
    base_url: str = "",
    api_key: str = "",
):
    remote_job(job_id=job_id, base_url=base_url or None, api_key=api_key or None)


@app.command()
def remote_job_events_list(
    job_id: str,
    since: int = 0,
    max_items: int = 100,
    base_url: str = "",
    api_key: str = "",
):
    remote_job_events(
        job_id=job_id,
        since=since,
        max_items=max_items,
        base_url=base_url or None,
        api_key=api_key or None,
    )


@app.command()
def remote_job_stream_logs(
    job_id: str,
    since: int = 0,
    base_url: str = "",
    api_key: str = "",
):
    remote_job_stream(
        job_id=job_id,
        since=since,
        base_url=base_url or None,
        api_key=api_key or None,
    )

if __name__ == "__main__":
    app()
