import re
import shutil
from datetime import date, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel


class ChapterMeta(BaseModel):
    title: str
    slug: str
    order: int
    status: str = "draft"
    summary: str = ""
    prompt: str = ""


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _next_order(chapters_dir: Path) -> int:
    nums = []
    for p in chapters_dir.iterdir() if chapters_dir.exists() else []:
        if p.is_dir():
            m = re.match(r"chapter-(\d+)$", p.name)
            if m:
                nums.append(int(m.group(1)))
    return max(nums) + 1 if nums else 1


def create_chapter(chapters_dir: Path, title: str, prompt: str = "") -> tuple[Path, Path, Path]:
    chapters_dir.mkdir(parents=True, exist_ok=True)
    order = _next_order(chapters_dir)
    prefix = f"chapter-{order:02d}"
    chapter_dir = chapters_dir / prefix
    chapter_dir.mkdir(exist_ok=True)

    meta = ChapterMeta(title=title, slug=slugify(title), order=order, prompt=prompt)

    md_path = chapter_dir / f"{prefix}.md"
    meta_path = chapter_dir / f"{prefix}.meta.yaml"
    history_path = chapter_dir / f"{prefix}.history.md"

    md_path.write_text(f"# {title}\n")
    meta_path.write_text(
        yaml.dump(meta.model_dump(), default_flow_style=False, sort_keys=False, allow_unicode=True)
    )
    history_path.write_text(
        f"# History: {title}\n\n"
        f"## {date.today()} — Initial checkpoint\n\n"
        f"Chapter created.\n"
    )

    return md_path, meta_path, history_path


def find_chapter(chapters_dir: Path, identifier: str) -> tuple[Path, ChapterMeta] | None:
    """Find a chapter by order number (e.g. '3') or directory name (e.g. 'chapter-03')."""
    if identifier.isdigit():
        target = f"chapter-{int(identifier):02d}"
    else:
        target = identifier
    chapter_dir = chapters_dir / target
    meta_file = chapter_dir / f"{target}.meta.yaml"
    if not meta_file.exists():
        return None
    data = yaml.safe_load(meta_file.read_text())
    return chapter_dir, ChapterMeta.model_validate(data)


def trash_chapter(chapters_dir: Path, chapter_dir: Path) -> Path:
    """Move a chapter directory into chapters/.trash/, timestamped."""
    trash_dir = chapters_dir / ".trash"
    trash_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = trash_dir / f"{chapter_dir.name}-{timestamp}"
    shutil.move(str(chapter_dir), dest)
    return dest


def list_trash(chapters_dir: Path) -> list[tuple[Path, str, ChapterMeta, str]]:
    """Return trashed entries as (trash_dir, original_name, meta, display_timestamp)."""
    trash_dir = chapters_dir / ".trash"
    if not trash_dir.exists():
        return []
    entries = []
    for p in sorted(trash_dir.iterdir()):
        if not p.is_dir():
            continue
        m = re.match(r"(chapter-\d+)-(\d{8})-(\d{6})$", p.name)
        if not m:
            continue
        original_name = m.group(1)
        d, t = m.group(2), m.group(3)
        display_ts = f"{d[:4]}-{d[4:6]}-{d[6:]} {t[:2]}:{t[2:4]}:{t[4:]}"
        meta_files = list(p.glob("*.meta.yaml"))
        if not meta_files:
            continue
        data = yaml.safe_load(meta_files[0].read_text())
        entries.append((p, original_name, ChapterMeta.model_validate(data), display_ts))
    return entries


def restore_chapter(chapters_dir: Path, trash_path: Path, original_name: str) -> Path:
    """Move a trashed chapter back into chapters/."""
    dest = chapters_dir / original_name
    if dest.exists():
        raise FileExistsError(f"'{original_name}' already exists in chapters/. Rename or delete it first.")
    shutil.move(str(trash_path), dest)
    return dest


def list_chapters(chapters_dir: Path) -> list[ChapterMeta]:
    if not chapters_dir.exists():
        return []
    metas = []
    for p in chapters_dir.iterdir():
        if p.is_dir() and re.match(r"chapter-\d+$", p.name):
            meta_file = p / f"{p.name}.meta.yaml"
            if meta_file.exists():
                data = yaml.safe_load(meta_file.read_text())
                metas.append(ChapterMeta.model_validate(data))
    return sorted(metas, key=lambda m: m.order)
