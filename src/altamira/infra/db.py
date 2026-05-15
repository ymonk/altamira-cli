from pathlib import Path

from sqlalchemy import Column, Float, ForeignKey, Integer, MetaData, Table, Text, create_engine

metadata = MetaData()

indexed_files = Table(
    "indexed_files",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("path", Text, unique=True, nullable=False),
    Column("file_type", Text, nullable=False),   # 'chapter' | 'material' | 'note'
    Column("size", Integer),
    Column("mtime", Float),
    Column("indexed_at", Text, nullable=False),
)

source_notes_index = Table(
    "source_notes_index",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("file_id", Integer, ForeignKey("indexed_files.id"), unique=True, nullable=False),
    Column("title", Text),
    Column("tags", Text),
    Column("summary", Text),
    Column("indexed_at", Text, nullable=False),
)

scan_state = Table(
    "scan_state",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("directory", Text, unique=True, nullable=False),
    Column("last_scan_at", Text, nullable=False),
    Column("file_count", Integer, nullable=False),
)


def get_engine(root: Path):
    db_path = root / ".altamira" / "app.db"
    return create_engine(f"sqlite:///{db_path}")


def create_tables(root: Path) -> None:
    metadata.create_all(get_engine(root))


def ensure_tables(root: Path) -> bool:
    """Create tables if the database file does not exist yet.

    Returns True if initialization was performed, False if already present.
    """
    db_path = root / ".altamira" / "app.db"
    if db_path.exists():
        return False
    db_path.parent.mkdir(parents=True, exist_ok=True)
    create_tables(root)
    return True
