from datetime import datetime
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from altamira.infra.db import get_engine, indexed_files, scan_state, source_notes_index

_SCAN_DIRS: dict[str, str] = {
    "chapters": "chapter",
    "materials/raw": "material",
    "notes/source": "note",
}


def _extract_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def scan_project(root: Path) -> dict[str, int]:
    """Walk project directories, update indexed_files / source_notes_index / scan_state.

    Returns a {directory: file_count} summary.
    """
    engine = get_engine(root)
    counts: dict[str, int] = {}
    now = datetime.now().isoformat()

    with engine.connect() as conn:
        for dir_rel, file_type in _SCAN_DIRS.items():
            scan_dir = root / dir_rel
            files = sorted(scan_dir.rglob("*"), key=lambda p: p.name) if scan_dir.exists() else []
            files = [f for f in files if f.is_file()]
            counts[dir_rel] = len(files)

            for f in files:
                rel = str(f.relative_to(root))
                stat = f.stat()

                conn.execute(
                    sqlite_insert(indexed_files)
                    .values(path=rel, file_type=file_type, size=stat.st_size, mtime=stat.st_mtime, indexed_at=now)
                    .on_conflict_do_update(
                        index_elements=["path"],
                        set_={"size": stat.st_size, "mtime": stat.st_mtime, "indexed_at": now},
                    )
                )

                if file_type == "note" and f.suffix == ".md":
                    row = conn.execute(
                        select(indexed_files.c.id).where(indexed_files.c.path == rel)
                    ).fetchone()
                    if row:
                        meta_path = f.with_suffix("").with_suffix(".meta.yaml")
                        if meta_path.exists():
                            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
                            title = meta.get("title") or _extract_title(f)
                            tags = ", ".join(meta.get("tags") or [])
                            summary = meta.get("summary") or ""
                        else:
                            title = _extract_title(f)
                            tags = ""
                            summary = ""
                        conn.execute(
                            sqlite_insert(source_notes_index)
                            .values(file_id=row[0], title=title, tags=tags, summary=summary, indexed_at=now)
                            .on_conflict_do_update(
                                index_elements=["file_id"],
                                set_={"title": title, "tags": tags, "summary": summary, "indexed_at": now},
                            )
                        )

            conn.execute(
                sqlite_insert(scan_state)
                .values(directory=dir_rel, last_scan_at=now, file_count=len(files))
                .on_conflict_do_update(
                    index_elements=["directory"],
                    set_={"last_scan_at": now, "file_count": len(files)},
                )
            )

        conn.commit()

    return counts
