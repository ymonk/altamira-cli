from pathlib import Path

import typer
from sqlalchemy import func, select

from altamira.cli.console import console, kv
from altamira.infra.db import create_tables, ensure_tables, get_engine, indexed_files, scan_state, source_notes_index

db_app = typer.Typer(help="Manage the local database.")


def _require_project(cwd: Path) -> None:
    if not (cwd / "altamira.yaml").exists():
        console.print("[red]Error:[/red] Not in an Altamira project. Run: altamira init <dir>")
        raise typer.Exit(code=1)


@db_app.command("init")
def db_init():
    """Initialize the local SQLite database under .altamira/app.db."""
    cwd = Path.cwd()
    _require_project(cwd)

    already = not ensure_tables(cwd)
    if already:
        create_tables(cwd)   # idempotent — create_all skips existing tables
        kv("ready", ".altamira/app.db  (already initialized)")
    else:
        kv("ready", ".altamira/app.db")
    console.print("\n[bold]Database initialized.[/bold]")


@db_app.command("show")
def db_show():
    """Summarize the contents of the local database."""
    cwd = Path.cwd()
    _require_project(cwd)
    if ensure_tables(cwd):
        console.print("[dim]Database not found, initializing .altamira/app.db[/dim]\n")

    engine = get_engine(cwd)
    with engine.connect() as conn:
        # --- Indexed files by type ---
        file_counts = conn.execute(
            select(indexed_files.c.file_type, func.count().label("n"))
            .group_by(indexed_files.c.file_type)
            .order_by(indexed_files.c.file_type)
        ).fetchall()

        # --- Scan state ---
        state_rows = conn.execute(
            select(scan_state.c.directory, scan_state.c.last_scan_at, scan_state.c.file_count)
            .order_by(scan_state.c.directory)
        ).fetchall()

        # --- Source notes ---
        note_rows = conn.execute(
            select(source_notes_index.c.title).order_by(source_notes_index.c.id)
        ).fetchall()

    console.print("[bold]Indexed files[/bold]")
    if file_counts:
        for file_type, count in file_counts:
            kv(file_type, str(count))
    else:
        console.print("  (none — run: altamira scan)")

    console.print()
    console.print("[bold]Last scan[/bold]")
    if state_rows:
        for directory, last_scan_at, file_count in state_rows:
            ts = last_scan_at[:19].replace("T", " ")
            kv(directory, f"{ts}   {file_count} file{'s' if file_count != 1 else ''}")
    else:
        console.print("  (none — run: altamira scan)")

    console.print()
    console.print("[bold]Source notes[/bold]")
    if note_rows:
        for (title,) in note_rows:
            console.print(f"  {title}")
    else:
        console.print("  (none)")
