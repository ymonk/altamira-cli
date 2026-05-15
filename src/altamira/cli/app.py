import sqlite3
import sys
from pathlib import Path

import typer

from altamira import __version__
from altamira.cli.chapter_cmd import chapter_app
from altamira.cli.config_cmd import config_app
from altamira.cli.console import console, kv
from altamira.cli.db_cmd import db_app
from altamira.cli.note_cmd import note_app
from altamira.cli.outline_cmd import outline_app
from altamira.cli.publish_cmd import publish_app
from altamira.cli.review_cmd import review
from altamira.cli.rewrite_cmd import rewrite
from altamira.cli.skills_cmd import skills_app
from altamira.config.loader import load_config, write_config
from altamira.config.model import ProjectConfig
from altamira.domain.chapter import list_chapters
from altamira.infra.db import ensure_tables
from altamira.infra.scanner import scan_project
from altamira.infra.watcher import ProjectEventHandler

app = typer.Typer(invoke_without_command=True, help="Altamira — local-first project CLI.")


@app.callback()
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        from altamira.cli.repl import run_repl
        run_repl(Path.cwd())


app.add_typer(chapter_app, name="chapter")
app.add_typer(config_app, name="config")
app.add_typer(note_app, name="note")
app.add_typer(outline_app, name="outline")
app.add_typer(publish_app, name="publish")
app.command("review")(review)
app.command("rewrite")(rewrite)
app.add_typer(skills_app, name="skill")
app.add_typer(db_app, name="db")

_INIT_DIRS = [
    "chapters",
    "materials/raw",
    "notes/source",
    "publish/preview",
    ".altamira",
]


@app.command()
def version():
    """Print the current version."""
    console.print(f"[bold]altamira[/bold] {__version__}")


@app.command()
def doctor():
    """Print system diagnostics."""
    kv("Python", sys.version)
    kv("CWD", str(Path.cwd()))

    try:
        sqlite3.connect(":memory:").close()
        kv("SQLite", "[green]available[/green]")
    except Exception as e:
        kv("SQLite", f"[red]unavailable[/red] ({e})")


@app.command()
def init(
    directory: str | None = typer.Argument(None, help="Target directory ('.' for current)."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing config."),
):
    """Initialize an Altamira project in a directory."""
    if directory is None:
        console.print("[red]Error:[/red] A directory argument is required.\n")
        console.print("  [bold]altamira init .[/bold]        initialize in the current directory")
        console.print("  [bold]altamira init <name>[/bold]   create <name>/ and initialize inside it")
        raise typer.Exit(code=1)

    root = Path.cwd() if directory == "." else Path.cwd() / directory
    root.mkdir(parents=True, exist_ok=True)

    config_path = root / "altamira.yaml"
    if config_path.exists() and not force:
        console.print("[red]Error:[/red] altamira.yaml already exists. Use --force to overwrite.")
        raise typer.Exit(code=1)

    for d in _INIT_DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
        kv("created", d)

    write_config(ProjectConfig(name=root.name, subject_name=root.name), root)
    kv("created", "altamira.yaml")

    console.print("\n[bold]Project initialized.[/bold]")


@app.command()
def status():
    """Show project status and file counts."""
    cwd = Path.cwd()

    try:
        config = load_config(cwd)
    except FileNotFoundError:
        console.print("[red]Error:[/red] Not an Altamira project. Run: altamira init <dir>")
        raise typer.Exit(code=1)

    kv("project", config.name)
    kv("version", config.version)
    kv("subject", f"{config.subject_name or '—'}  [{config.subject_type}]")
    kv("language", config.language)
    if config.description:
        kv("description", config.description)
    console.print()

    def file_count(path: Path) -> int:
        return sum(1 for p in path.iterdir() if p.is_file()) if path.exists() else 0

    kv("chapters", str(len(list_chapters(cwd / "chapters"))))
    kv("materials", str(file_count(cwd / "materials" / "raw")))
    kv("notes", str(file_count(cwd / "notes" / "source")))


@app.command()
def scan():
    """Scan project directories and update the file index."""
    cwd = Path.cwd()
    if not (cwd / "altamira.yaml").exists():
        console.print("[red]Error:[/red] Not in an Altamira project. Run: altamira init <dir>")
        raise typer.Exit(code=1)

    if ensure_tables(cwd):
        console.print("[dim]Database not found, initializing .altamira/app.db[/dim]")

    counts = scan_project(cwd)
    for directory, count in counts.items():
        kv("scanned", f"{directory}/  ({count} files)")
    console.print("\n[bold]Index updated.[/bold]")


@app.command()
def watch():
    """Watch project directories and re-index on file changes."""
    import time
    from watchdog.observers import Observer

    cwd = Path.cwd()
    if not (cwd / "altamira.yaml").exists():
        console.print("[red]Error:[/red] Not in an Altamira project. Run: altamira init <dir>")
        raise typer.Exit(code=1)

    if ensure_tables(cwd):
        console.print("[dim]Database not found, initializing .altamira/app.db[/dim]")

    def reindex() -> None:
        try:
            scan_project(cwd)
            console.print(f"[dim]  → index updated[/dim]")
        except Exception as e:
            console.print(f"[yellow]  → re-index failed:[/yellow] {e}")

    watch_dirs = ["chapters", "materials", "notes/source"]
    handler = ProjectEventHandler(cwd, reindex)
    observer = Observer()
    for d in watch_dirs:
        p = cwd / d
        if p.exists():
            observer.schedule(handler, str(p), recursive=True)

    watching = "  ".join(f"[bold]{d}/[/bold]" for d in watch_dirs)
    console.print(f"Watching {watching}\nPress Ctrl+C to stop.\n")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    console.print("\nStopped.")
