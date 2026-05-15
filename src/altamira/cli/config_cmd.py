from pathlib import Path

import typer

from altamira.cli.console import console, kv
from altamira.config.loader import load_config

config_app = typer.Typer(help="Manage project configuration.")


@config_app.command("show")
def config_show():
    """Load and display altamira.yaml."""
    try:
        config = load_config(Path.cwd())
    except FileNotFoundError:
        console.print("[red]Error:[/red] No altamira.yaml found. Run: altamira init <dir>")
        raise typer.Exit(code=1)

    for field, value in config.model_dump().items():
        kv(field, str(value))
