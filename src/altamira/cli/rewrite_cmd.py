from datetime import datetime
from itertools import zip_longest
from pathlib import Path

import typer

from altamira.cli.console import console
from altamira.domain.chapter import find_chapter
from altamira.services.rewriter import RewriteFn, llm_rewrite

_rewriter: RewriteFn = llm_rewrite


def _resolve_chapter(cwd: Path, identifier: str) -> tuple[Path, Path, Path]:
    result = find_chapter(cwd / "chapters", identifier)
    if result is None:
        console.print(f"[red]Error:[/red] Chapter '{identifier}' not found.")
        raise typer.Exit(code=1)
    chapter_dir, _ = result
    prefix = chapter_dir.name
    return chapter_dir, chapter_dir / f"{prefix}.md", chapter_dir / f"{prefix}.history.md"


def _prompt_decision(n: int, total: int) -> str:
    while True:
        raw = console.input(
            f"  [[bold]a[/bold]] accept  [[bold]r[/bold]] reject  "
            f"[[bold]A[/bold]] accept all  "
            f"[dim]({n}/{total})[/dim] › "
        ).strip()
        if raw in ("a", "r", "A"):
            return raw
        console.print("[yellow]  Enter a, r, or A.[/yellow]")


def _write_checkpoint(chapter_dir: Path, md_path: Path, timestamp: str) -> Path:
    versions_dir = chapter_dir / "versions"
    versions_dir.mkdir(exist_ok=True)
    dest = versions_dir / f"{timestamp}.md"
    dest.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


def _append_history(
    history_path: Path,
    timestamp: str,
    accepted: int,
    rejected: int,
    checkpoint: Path,
) -> None:
    ts = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[9:11]}:{timestamp[11:13]}:{timestamp[13:15]}"
    entry = (
        f"\n## {ts} — rewrite\n\n"
        f"- accepted: {accepted}\n"
        f"- rejected: {rejected}\n"
        f"- checkpoint: {checkpoint.name}\n"
    )
    with history_path.open("a") as f:
        f.write(entry)


def rewrite(
    chapter: str = typer.Argument(..., help="Chapter number (1) or name (chapter-01)."),
) -> None:
    """Rewrite a chapter paragraph by paragraph and apply accepted changes."""
    cwd = Path.cwd()
    if not (cwd / "altamira.yaml").exists():
        console.print("[red]Error:[/red] Not in an Altamira project. Run: altamira init <dir>")
        raise typer.Exit(code=1)

    chapter_dir, md_path, history_path = _resolve_chapter(cwd, chapter)
    original = md_path.read_text()
    rewritten = _rewriter(original)

    orig_paras = original.split("\n\n")
    new_paras = rewritten.split("\n\n")

    changed = [
        (i, orig, new)
        for i, (orig, new) in enumerate(zip_longest(orig_paras, new_paras, fillvalue=""))
        if orig != new
    ]

    if not changed:
        console.print("No changes produced by the rewriter.")
        return

    title = next(
        (l[2:].strip() for l in original.splitlines() if l.startswith("# ")),
        md_path.stem,
    )
    console.print(f"\n[bold]Rewrite: {title}[/bold]  ({len(changed)} change(s))\n")

    decisions: dict[int, str] = {}
    accept_all = False

    for n, (para_idx, orig, new) in enumerate(changed, start=1):
        console.rule(f"Change {n} of {len(changed)}")
        console.print(f"\n  [dim]ORIGINAL[/dim]\n  {orig.strip()}\n")
        console.print(f"  [bold green]REWRITTEN[/bold green]\n  {new.strip()}\n")

        if accept_all:
            decisions[para_idx] = "accept"
            console.print(f"  [dim]auto-accepted[/dim]\n")
            continue

        decision = _prompt_decision(n, len(changed))
        console.print()
        decisions[para_idx] = "accept" if decision in ("a", "A") else "reject"
        if decision == "A":
            accept_all = True

    accepted_count = sum(1 for v in decisions.values() if v == "accept")
    if accepted_count == 0:
        console.print("[yellow]No changes accepted. File unchanged.[/yellow]")
        return

    # Reconstruct: use accepted new paragraphs, keep original for rejected
    final_paras = [
        new if decisions.get(i) == "accept" else orig
        for i, (orig, new) in enumerate(zip_longest(orig_paras, new_paras, fillvalue=""))
    ]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    checkpoint = _write_checkpoint(chapter_dir, md_path, timestamp)
    md_path.write_text("\n\n".join(p for p in final_paras if p is not None))
    rejected_count = len(changed) - accepted_count
    _append_history(history_path, timestamp, accepted_count, rejected_count, checkpoint)

    console.rule()
    console.print(f"\n[green]Applied {accepted_count} of {len(changed)} change(s).[/green]")
    console.print(f"Checkpoint: [bold]{checkpoint.relative_to(cwd)}[/bold]")
    console.print(f"Updated:    [bold]{md_path.relative_to(cwd)}[/bold]")
    console.print(f"History:    [bold]{history_path.relative_to(cwd)}[/bold]")
