import typer
from rich.markdown import Markdown

from altamira.cli.console import console
from altamira.skills.loader import list_skills, load_skill

skills_app = typer.Typer(help="Manage built-in prompt skills.")


@skills_app.command("list")
def skills_list():
    """List available prompt skills."""
    skills = list_skills()
    if not skills:
        console.print("No skills found.")
        return
    for name, description in skills:
        console.print(f"  [bold]{name:<28}[/bold]{description}")


@skills_app.command("show")
def skills_show(name: str = typer.Argument(..., help="Skill name.")):
    """Show the full content of a skill prompt."""
    content = load_skill(name)
    if content is None:
        console.print(f"[red]Error:[/red] Skill '{name}' not found. Run: altamira skill list")
        raise typer.Exit(code=1)
    console.print(Markdown(content))
