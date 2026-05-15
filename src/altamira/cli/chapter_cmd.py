from pathlib import Path

import typer
from rich.table import Table

from altamira.cli.console import console, kv
from altamira.domain.chapter import create_chapter, find_chapter, list_chapters, list_trash, restore_chapter, slugify, trash_chapter

chapter_app = typer.Typer(help="Manage chapters.")


def _require_project(cwd: Path) -> None:
    if not (cwd / "altamira.yaml").exists():
        console.print("[red]Error:[/red] Not in an Altamira project, this command must work in an Altamira project directory.")
        raise typer.Exit(code=1)


@chapter_app.command("new")
def chapter_new(
    title: str = typer.Argument(..., help="Chapter title."),
    prompt: str = typer.Option("", "-m", "--prompt", help="Writing prompt for this chapter."),
):
    """Create a new chapter with metadata and history files."""
    cwd = Path.cwd()
    _require_project(cwd)

    existing_slugs = {ch.slug for ch in list_chapters(cwd / "chapters")}
    if slugify(title) in existing_slugs:
        console.print(f"[yellow]Warning:[/yellow] A chapter with the title '{title}' already exists.")

    md, meta, history = create_chapter(cwd / "chapters", title, prompt=prompt)
    kv("created", str(md.relative_to(cwd)))
    kv("created", str(meta.relative_to(cwd)))
    kv("created", str(history.relative_to(cwd)))


@chapter_app.command("list")
def chapter_list():
    """List all chapters."""
    cwd = Path.cwd()
    _require_project(cwd)

    chapters = list_chapters(cwd / "chapters")
    if not chapters:
        console.print("No chapters yet. Run: altamira chapter new <title>")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title")
    table.add_column("Slug")
    table.add_column("Status")

    for ch in chapters:
        table.add_row(str(ch.order), ch.title, ch.slug, ch.status)

    console.print(table)


@chapter_app.command("delete")
def chapter_delete(
    identifier: str = typer.Argument(..., help="Chapter number (3) or name (chapter-03)."),
):
    """Move a chapter to the trash."""
    cwd = Path.cwd()
    _require_project(cwd)

    result = find_chapter(cwd / "chapters", identifier)
    if result is None:
        console.print(f"[red]Error:[/red] Chapter '{identifier}' not found.")
        raise typer.Exit(code=1)

    chapter_dir, meta = result
    console.print(f"Title:  [bold]{meta.title}[/bold]")
    console.print(f"Files:  {chapter_dir.relative_to(cwd)}/")

    if not typer.confirm("\nMove this chapter to trash?"):
        console.print("Cancelled.")
        raise typer.Exit()

    dest = trash_chapter(cwd / "chapters", chapter_dir)
    console.print(f"\n[yellow]Moved to trash:[/yellow] {dest.relative_to(cwd)}")


@chapter_app.command("restore")
def chapter_restore():
    """Restore a trashed chapter back into chapters/."""
    cwd = Path.cwd()
    _require_project(cwd)

    entries = list_trash(cwd / "chapters")
    if not entries:
        console.print("No trashed chapters to restore.")
        return

    console.print("\nTrashed chapters:\n")
    for i, (_, original_name, meta, timestamp) in enumerate(entries, start=1):
        console.print(f"  [bold]{i}[/bold]  {original_name:<14}  {meta.title:<30}  {timestamp}")

    console.print()
    while True:
        raw = console.input("Enter number to restore, or N to cancel: ").strip()
        if raw.lower() == "n":
            console.print("Cancelled.")
            return
        if raw.isdigit() and 1 <= int(raw) <= len(entries):
            break
        console.print(f"[red]Invalid input.[/red] Enter a number between 1 and {len(entries)}, or N to cancel.")

    trash_path, original_name, _, _ = entries[int(raw) - 1]
    try:
        dest = restore_chapter(cwd / "chapters", trash_path, original_name)
        console.print(f"\n[green]Restored:[/green] {dest.relative_to(cwd)}")
    except FileExistsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
