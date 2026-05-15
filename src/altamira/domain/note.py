import re
from datetime import datetime
from pathlib import Path

import yaml
from pydantic import BaseModel


class NoteMeta(BaseModel):
    title: str
    source_type: str = "memory"
    url: str = ""
    origin: str = ""
    created_at: str = ""
    tags: list[str] = []
    summary: str = ""


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _unique_slug(notes_dir: Path, base: str) -> str:
    slug, counter = base, 2
    while (notes_dir / f"{slug}.md").exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def create_note(
    notes_dir: Path,
    title: str,
    source_type: str = "memory",
    url: str = "",
    origin: str = "",
    tags: list[str] | None = None,
    summary: str = "",
) -> tuple[Path, Path]:
    notes_dir.mkdir(parents=True, exist_ok=True)
    slug = _unique_slug(notes_dir, _slugify(title))

    meta = NoteMeta(
        title=title,
        source_type=source_type,
        url=url,
        origin=origin,
        created_at=datetime.now().isoformat(timespec="seconds"),
        tags=tags or [],
        summary=summary,
    )

    md_path = notes_dir / f"{slug}.md"
    meta_path = notes_dir / f"{slug}.meta.yaml"

    md_path.write_text(f"# {title}\n\n")
    meta_path.write_text(
        yaml.dump(meta.model_dump(), default_flow_style=False, sort_keys=False, allow_unicode=True)
    )

    return md_path, meta_path


def list_notes(notes_dir: Path) -> list[NoteMeta]:
    if not notes_dir.exists():
        return []
    notes = []
    for meta_path in sorted(notes_dir.glob("*.meta.yaml")):
        data = yaml.safe_load(meta_path.read_text())
        if data:
            notes.append(NoteMeta.model_validate(data))
    return sorted(notes, key=lambda n: n.created_at, reverse=True)
