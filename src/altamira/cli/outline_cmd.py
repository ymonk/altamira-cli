from pathlib import Path

import typer

from altamira.cli.console import console, kv
from altamira.config.loader import load_config
from altamira.domain.chapter import list_chapters
from altamira.services.provider import get_provider
from altamira.skills.loader import load_skill

outline_app = typer.Typer(help="Generate project outlines.")


def _build_context(cwd: Path) -> str:
    """Assemble project context to inject into the outline_builder prompt."""
    config = load_config(cwd)
    sections: list[str] = [
        f"Project name: {config.name}",
        f"Subject type: {config.subject_type}",
        f"Subject name: {config.subject_name or 'not specified'}",
        f"Language: {config.language}",
    ]
    if config.description:
        sections.append(f"Description: {config.description}")
    sections.append("")

    chapters = list_chapters(cwd / "chapters")
    if chapters:
        sections.append(f"Chapters ({len(chapters)} total):")
        for ch in chapters:
            line = f"  {ch.order}. \"{ch.title}\" — status: {ch.status}"
            sections.append(line)
            if ch.prompt:
                sections.append(f"     Writing prompt: {ch.prompt}")
        sections.append("")

    notes_dir = cwd / "notes" / "source"
    note_files = sorted(notes_dir.glob("*.md")) if notes_dir.exists() else []
    if note_files:
        sections.append(f"Source notes ({len(note_files)} total):")
        for path in note_files:
            sections.append(f"\n--- {path.name} ---")
            sections.append(path.read_text(encoding="utf-8").strip())
        sections.append("")
    else:
        sections.append("Source notes: none")

    return "\n".join(sections)


@outline_app.command("generate")
def outline_generate():
    """Generate a chapter outline from project context using an LLM."""
    cwd = Path.cwd()
    if not (cwd / "altamira.yaml").exists():
        console.print("[red]Error:[/red] Not in an Altamira project. Run: altamira init <dir>")
        raise typer.Exit(code=1)

    skill_prompt = load_skill("outline_builder")
    if not skill_prompt:
        console.print("[red]Error:[/red] Skill 'outline_builder' not found.")
        raise typer.Exit(code=1)

    context = _build_context(cwd)
    prompt = skill_prompt.replace("[PASTE NOTES HERE]", context)

    try:
        provider = get_provider()
    except (EnvironmentError, ImportError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    import os
    provider_name = os.environ.get("ALTAMIRA_PROVIDER", "anthropic")
    model_defaults = {"anthropic": "claude-sonnet-4-6", "openai": "gpt-4o"}
    model = os.environ.get("ALTAMIRA_MODEL", model_defaults.get(provider_name, "unknown"))
    kv("provider", provider_name)
    kv("model", model)
    console.print("Calling provider…\n")

    try:
        result = provider(prompt)
    except Exception as e:
        console.print(f"[red]Provider error:[/red] {e}")
        raise typer.Exit(code=1)

    workspace = cwd / "workspace"
    workspace.mkdir(exist_ok=True)
    out_path = workspace / "outline.md"
    out_path.write_text(result)

    kv("saved", str(out_path.relative_to(cwd)))
    console.print("\n[bold]Outline generated.[/bold]")
