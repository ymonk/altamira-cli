import importlib.resources
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import jinja2
import markdown as md_lib

from altamira.config.loader import load_config
from altamira.domain.chapter import list_chapters


@dataclass
class Issue:
    level: str   # "error" | "warning"
    scope: str   # chapter slug / "project"
    message: str


def run_prepare(root: Path) -> list[Issue]:
    config = load_config(root)
    chapters_dir = root / "chapters"
    notes_dir = root / "notes" / "source"
    issues: list[Issue] = []

    chapters = list_chapters(chapters_dir)
    if not chapters:
        issues.append(Issue("error", "project", "No chapters found."))
        return issues

    for ch in chapters:
        label = f"chapter-{ch.order:02d}"

        # Completeness: not still draft
        if ch.status == "draft":
            issues.append(Issue("warning", label, "Status is 'draft'."))

        # Metadata: non-empty title
        if not ch.title.strip():
            issues.append(Issue("error", label, "Title is empty."))

        # Summary presence
        if not ch.summary.strip():
            issues.append(Issue("warning", label, "Summary is empty."))

        # Content: chapter body must have text beyond the heading
        chapter_dir = chapters_dir / label
        md_path = chapter_dir / f"{label}.md"
        if not md_path.exists():
            issues.append(Issue("error", label, f"Markdown file not found: {md_path.name}"))
        else:
            body_lines = [
                l for l in md_path.read_text(encoding="utf-8").splitlines()
                if not l.startswith("# ")
            ]
            if not "".join(body_lines).strip():
                issues.append(Issue("warning", label, "Chapter body is empty (only a heading)."))

    # Cover: if configured, must exist
    if config.cover:
        if not (root / config.cover).exists():
            issues.append(Issue("error", "project", f"Cover image not found: {config.cover}"))

    # Source notes: if required, at least one must exist
    if config.require_source_notes:
        note_files = list(notes_dir.glob("*.md")) if notes_dir.exists() else []
        if not note_files:
            issues.append(Issue("warning", "project", "require_source_notes is enabled but no source notes found."))

    return issues


def _resolve_images(text: str, chapter_dir: Path, root: Path, images_out: Path) -> str:
    """Rewrite markdown image paths: copy found files to images_out/, update refs."""

    def replace(m: re.Match) -> str:
        alt, path_str = m.group(1), m.group(2)
        # Skip data URIs and absolute URLs
        if path_str.startswith(("http://", "https://", "data:")):
            return m.group(0)
        candidates = [
            chapter_dir / path_str,
            root / path_str,
            root / "materials" / "raw" / Path(path_str).name,
        ]
        for src in candidates:
            if src.exists():
                images_out.mkdir(parents=True, exist_ok=True)
                dest = images_out / src.name
                if not dest.exists():
                    shutil.copy2(src, dest)
                return f"![{alt}](images/{src.name})"
        return m.group(0)

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace, text)


def run_build(root: Path, out_dir: Path) -> list[Path]:
    config = load_config(root)
    chapters = list_chapters(root / "chapters")

    out_dir.mkdir(parents=True, exist_ok=True)
    images_out = out_dir / "images"

    md = md_lib.Markdown(extensions=["tables", "fenced_code"])

    chapter_sections = []
    for ch in chapters:
        label = f"chapter-{ch.order:02d}"
        chapter_dir = root / "chapters" / label
        md_path = chapter_dir / f"{label}.md"
        text = md_path.read_text(encoding="utf-8") if md_path.exists() else f"# {ch.title}\n"
        text = _resolve_images(text, chapter_dir, root, images_out)
        md.reset()
        chapter_sections.append({
            "id": label,
            "title": ch.title,
            "order": ch.order,
            "html": md.convert(text),
        })

    cover_html = ""
    if config.cover:
        cover_src = root / config.cover
        if cover_src.exists():
            images_out.mkdir(parents=True, exist_ok=True)
            dest = images_out / cover_src.name
            shutil.copy2(cover_src, dest)
            cover_html = f'<img src="images/{cover_src.name}" alt="Cover" class="cover">'

    template_text = (
        importlib.resources.files("altamira.publish")
        .joinpath("templates/book.html.j2")
        .read_text(encoding="utf-8")
    )
    page_title = (
        f"{config.name} — {config.subject_name}"
        if config.subject_name
        else config.name
    )
    env = jinja2.Environment(autoescape=True, loader=jinja2.BaseLoader())
    html_out = env.from_string(template_text).render(
        title=page_title,
        subtitle=config.description,
        chapters=chapter_sections,
        cover_html=cover_html,
        lang=config.language,
    )

    index_path = out_dir / "index.html"
    index_path.write_text(html_out, encoding="utf-8")

    written = [index_path]
    if images_out.exists():
        written += sorted(images_out.iterdir())
    return written
