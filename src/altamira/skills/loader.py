from importlib.resources import files


def _prompts_dir():
    return files("altamira.skills").joinpath("prompts")


def _extract_description(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:100]
    return ""


def list_skills() -> list[tuple[str, str]]:
    """Return [(name, description)] sorted alphabetically."""
    result = []
    for resource in _prompts_dir().iterdir():
        if resource.name.endswith(".md"):
            name = resource.name[:-3]
            description = _extract_description(resource.read_text(encoding="utf-8"))
            result.append((name, description))
    return sorted(result)


def load_skill(name: str) -> str | None:
    try:
        return _prompts_dir().joinpath(f"{name}.md").read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError):
        return None
