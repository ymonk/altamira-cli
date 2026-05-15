from rich.console import Console

console = Console()


def kv(label: str, value: str) -> None:
    """Print a bold right-padded label with a plain value."""
    console.print(f"[bold]{label:<8}[/bold] {value}")
