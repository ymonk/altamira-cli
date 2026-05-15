from datetime import datetime
from pathlib import Path

import typer

from altamira.cli.console import console
from altamira.domain.chapter import find_chapter
from altamira.services.reviewer import ParagraphComment, ReviewFn, llm_review

_reviewer: ReviewFn = llm_review


def _resolve_chapter(cwd: Path, identifier: str) -> tuple[Path, Path, Path]:
    """Return (chapter_dir, md_path, history_path) or exit."""
    result = find_chapter(cwd / "chapters", identifier)
    if result is None:
        console.print(f"[red]Error:[/red] Chapter '{identifier}' not found.")
        raise typer.Exit(code=1)
    chapter_dir, meta = result
    prefix = chapter_dir.name
    return chapter_dir, chapter_dir / f"{prefix}.md", chapter_dir / f"{prefix}.history.md"


def _prompt_decision(index: int, total: int) -> str:
    """Prompt until the user enters a valid choice. Returns 'a', 'r', or 'A'."""
    while True:
        raw = console.input(
            f"  [[bold]a[/bold]] accept  [[bold]r[/bold]] reject  "
            f"[[bold]A[/bold]] accept all  "
            f"[dim]({index}/{total})[/dim] › "
        ).strip()
        if raw in ("a", "r", "A"):
            return raw
        console.print("[yellow]  Enter a, r, or A.[/yellow]")


def _write_review_doc(
    chapter_dir: Path,
    title: str,
    accepted: list[ParagraphComment],
    timestamp: str,
) -> Path:
    reviews_dir = chapter_dir / "reviews"
    reviews_dir.mkdir(exist_ok=True)
    out_path = reviews_dir / f"{timestamp}.md"
    lines = [f"# Review: {title}", f"*{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}*", ""]
    for c in accepted:
        lines += [
            "---",
            "",
            f"> {c.paragraph_text.strip()}",
            "",
            f"**Comment:** {c.comment}",
            "",
        ]
    out_path.write_text("\n".join(lines))
    return out_path


def _append_history(
    history_path: Path,
    timestamp: str,
    accepted: int,
    rejected: int,
    artifact: Path,
) -> None:
    ts = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[9:11]}:{timestamp[11:13]}:{timestamp[13:15]}"
    entry = (
        f"\n## {ts} — review\n\n"
        f"- accepted: {accepted}\n"
        f"- rejected: {rejected}\n"
        f"- artifact: {artifact.name}\n"
    )
    with history_path.open("a") as f:
        f.write(entry)


def review(
    chapter: str = typer.Argument(..., help="Chapter number (1) or name (chapter-01)."),
) -> None:
    """Review a chapter paragraph by paragraph and record accepted comments."""
    cwd = Path.cwd()
    if not (cwd / "altamira.yaml").exists():
        console.print("[red]Error:[/red] Not in an Altamira project. Run: altamira init <dir>")
        raise typer.Exit(code=1)

    chapter_dir, md_path, history_path = _resolve_chapter(cwd, chapter)
    text = md_path.read_text()
    comments = _reviewer(text)

    if not comments:
        console.print("No review comments generated for this chapter.")
        return

    title = next(
        (l[2:].strip() for l in text.splitlines() if l.startswith("# ")),
        chapter_dir.name,
    )
    console.print(f"\n[bold]Review: {title}[/bold]  ({len(comments)} comment(s))\n")

    accepted: list[ParagraphComment] = []
    accept_all = False

    for n, c in enumerate(comments, start=1):
        console.rule(f"Paragraph {c.paragraph_index + 1}")
        console.print(f"\n  {c.paragraph_text.strip()}\n")
        console.print(f"  [cyan]💬 {c.comment}[/cyan]\n")

        if accept_all:
            accepted.append(c)
            console.print(f"  [dim]auto-accepted ({n}/{len(comments)})[/dim]\n")
            continue

        decision = _prompt_decision(n, len(comments))
        console.print()

        if decision == "A":
            accepted.append(c)
            accept_all = True
        elif decision == "a":
            accepted.append(c)

    if not accepted:
        console.print("[yellow]No comments accepted. Nothing written.[/yellow]")
        return

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    rejected = len(comments) - len(accepted)
    review_doc = _write_review_doc(chapter_dir, title, accepted, timestamp)
    _append_history(history_path, timestamp, len(accepted), rejected, review_doc)

    console.rule()
    console.print(f"\n[green]Accepted {len(accepted)} of {len(comments)} comment(s).[/green]")
    console.print(f"Review saved to: [bold]{review_doc.relative_to(cwd)}[/bold]")
    console.print(f"History updated: [bold]{history_path.relative_to(cwd)}[/bold]")
