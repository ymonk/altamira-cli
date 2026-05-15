from pathlib import Path

import typer

from altamira.cli.console import console, kv
from altamira.domain.publish import Issue, run_build, run_prepare

publish_app = typer.Typer(help="Publish and preview the book.")


def _require_project(cwd: Path) -> None:
    if not (cwd / "altamira.yaml").exists():
        console.print("[red]Error:[/red] Not in an Altamira project, this command must work in an Altamira project directory.")
        raise typer.Exit(code=1)


def _fmt_issue(issue: Issue) -> str:
    scope = f"[dim]{issue.scope}[/dim]  " if issue.scope != "project" else ""
    if issue.level == "error":
        return f"  [red]✗[/red]  {scope}{issue.message}"
    return f"  [yellow]⚠[/yellow]  {scope}{issue.message}"


@publish_app.command("prepare")
def prepare():
    """Check project readiness for publishing."""
    cwd = Path.cwd()
    _require_project(cwd)

    issues = run_prepare(cwd)

    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    if not issues:
        console.print("[green]✓[/green]  All checks passed. Ready to build.")
        return

    if errors:
        console.print(f"\n[bold red]Errors ({len(errors)})[/bold red]")
        for issue in errors:
            console.print(_fmt_issue(issue))

    if warnings:
        console.print(f"\n[bold yellow]Warnings ({len(warnings)})[/bold yellow]")
        for issue in warnings:
            console.print(_fmt_issue(issue))

    console.print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")

    if errors:
        raise typer.Exit(code=1)


@publish_app.command("build")
def build():
    """Convert chapters to HTML and write a local book preview."""
    cwd = Path.cwd()
    _require_project(cwd)

    out_dir = cwd / "publish" / "preview"
    console.print(f"Building preview → [bold]{out_dir.relative_to(cwd)}[/bold]\n")

    try:
        written = run_build(cwd, out_dir)
    except Exception as e:
        console.print(f"[red]Build error:[/red] {e}")
        raise typer.Exit(code=1)

    for path in written:
        kv("wrote", str(path.relative_to(cwd)))

    console.print(f"\n[bold]Build complete.[/bold]")
    console.print(f"Open: [bold]{(out_dir / 'index.html').relative_to(cwd)}[/bold]")
