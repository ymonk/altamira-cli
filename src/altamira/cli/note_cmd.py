from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from altamira.cli.console import console, kv
from altamira.domain.note import create_note, list_notes

note_app = typer.Typer(help="Manage source notes.")


def _require_project(cwd: Path) -> None:
    if not (cwd / "altamira.yaml").exists():
        console.print("[red]Error:[/red] Not in an Altamira project, this command must work in an Altamira project directory.")
        raise typer.Exit(code=1)


@note_app.command("add-source")
def add_source(
    title: str = typer.Argument(..., help="Note title."),
    source_type: str = typer.Option("memory", "--type", "-t", help="Source type (memory, interview, document, book, article, other)."),
    url: str = typer.Option("", "--url", help="URL if the source is online."),
    origin: str = typer.Option("", "--origin", help="Origin description (person, place, event)."),
    tags: Optional[list[str]] = typer.Option(None, "--tag", help="Tag (repeatable)."),
    summary: str = typer.Option("", "--summary", "-s", help="Brief summary of the source."),
):
    """Add a new source note."""
    cwd = Path.cwd()
    _require_project(cwd)

    notes_dir = cwd / "notes" / "source"
    md_path, meta_path = create_note(
        notes_dir=notes_dir,
        title=title,
        source_type=source_type,
        url=url,
        origin=origin,
        tags=tags or [],
        summary=summary,
    )

    kv("created", str(md_path.relative_to(cwd)))
    kv("meta", str(meta_path.relative_to(cwd)))
    console.print("\n[bold]Source note created.[/bold]")
    console.print(f"Open [bold]{md_path.relative_to(cwd)}[/bold] to add your notes.")


@note_app.command("list")
def list_cmd():
    """List all source notes."""
    cwd = Path.cwd()
    _require_project(cwd)

    notes = list_notes(cwd / "notes" / "source")

    if not notes:
        console.print("No source notes found. Add one with: altamira note add-source <title>")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Title")
    table.add_column("Type")
    table.add_column("Tags")
    table.add_column("Created")
    table.add_column("Summary")

    for note in notes:
        table.add_row(
            note.title,
            note.source_type,
            ", ".join(note.tags) if note.tags else "",
            note.created_at[:10] if note.created_at else "",
            note.summary[:60] + ("…" if len(note.summary) > 60 else "") if note.summary else "",
        )

    console.print(table)
