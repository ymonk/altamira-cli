from datetime import datetime
from pathlib import Path

from altamira.domain.chapter import find_chapter


def write_chapter(
    identifier: str,
    content: str,
    reason: str = "",
    project_root: Path | None = None,
) -> dict:
    """Write markdown content to a chapter and log the change in its history file.

    Snapshots the existing content to versions/ before overwriting, so the
    change is always reversible.

    Args:
        identifier: Chapter number ("1") or directory name ("chapter-01").
        content:    Full markdown text to write.
        reason:     Short note logged to the history entry (optional).
        project_root: Project root directory. Defaults to cwd.

    Returns:
        {
            "chapter":      chapter directory name (e.g. "chapter-01"),
            "md_path":      path to the written markdown file,
            "checkpoint":   path to the pre-write version snapshot,
            "history_path": path to the updated history file,
            "bytes_written": number of bytes written,
        }

    Raises:
        FileNotFoundError: if the chapter does not exist.
    """
    root = project_root or Path.cwd()
    chapters_dir = root / "chapters"

    result = find_chapter(chapters_dir, identifier)
    if result is None:
        raise FileNotFoundError(f"Chapter '{identifier}' not found in {chapters_dir}")

    chapter_dir, meta = result
    prefix = chapter_dir.name
    md_path = chapter_dir / f"{prefix}.md"
    history_path = chapter_dir / f"{prefix}.history.md"

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Snapshot existing content before overwriting.
    versions_dir = chapter_dir / "versions"
    versions_dir.mkdir(exist_ok=True)
    checkpoint = versions_dir / f"{timestamp}.md"
    if md_path.exists():
        checkpoint.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

#    print(f"About to write content: {content[:100]}... to {md_path} (checkpoint: {checkpoint})")

    # Write the new content.
    md_path.write_text(content, encoding="utf-8")

    # Append a structured history entry.
    ts = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[9:11]}:{timestamp[11:13]}:{timestamp[13:15]}"
    entry_lines = [f"\n## {ts} — agent write\n", f"- checkpoint: {checkpoint.name}\n", f"- bytes: {len(content.encode())}\n"]
    if reason:
        entry_lines.append(f"- reason: {reason}\n")
    with history_path.open("a", encoding="utf-8") as f:
        f.writelines(entry_lines)

    return {
        "chapter": prefix,
        "md_path": str(md_path),
        "checkpoint": str(checkpoint),
        "history_path": str(history_path),
        "bytes_written": len(content.encode()),
    }
