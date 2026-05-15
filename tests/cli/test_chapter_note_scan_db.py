import yaml
from sqlalchemy import select

from altamira.cli.app import app
from altamira.infra.db import get_engine, indexed_files


# ── chapter new ───────────────────────────────────────────────────────────────

def test_chapter_new_creates_files(cli_runner, initialized_project):
    result = cli_runner.invoke(app, ["chapter", "new", "The Early Years"])
    assert result.exit_code == 0

    chapter_dir = initialized_project / "chapters" / "chapter-01"
    assert chapter_dir.is_dir()
    assert (chapter_dir / "chapter-01.md").exists()
    assert (chapter_dir / "chapter-01.meta.yaml").exists()
    assert (chapter_dir / "chapter-01.history.md").exists()


def test_chapter_new_meta_fields(cli_runner, initialized_project):
    cli_runner.invoke(app, ["chapter", "new", "The Early Years"], catch_exceptions=False)

    meta = yaml.safe_load(
        (initialized_project / "chapters" / "chapter-01" / "chapter-01.meta.yaml").read_text()
    )
    assert meta["title"] == "The Early Years"
    assert meta["slug"] == "the-early-years"
    assert meta["order"] == 1
    assert meta["status"] == "draft"


# ── chapter list ──────────────────────────────────────────────────────────────

def test_chapter_list_shows_chapter(cli_runner, initialized_project):
    cli_runner.invoke(app, ["chapter", "new", "The Early Years"], catch_exceptions=False)
    result = cli_runner.invoke(app, ["chapter", "list"])
    assert result.exit_code == 0
    assert "The Early Years" in result.output


# ── chapter delete ────────────────────────────────────────────────────────────

def test_chapter_delete_moves_to_trash(cli_runner, initialized_project):
    cli_runner.invoke(app, ["chapter", "new", "The Early Years"], catch_exceptions=False)

    result = cli_runner.invoke(app, ["chapter", "delete", "1"], input="y\n")
    assert result.exit_code == 0
    assert not (initialized_project / "chapters" / "chapter-01").exists()

    trash = initialized_project / "chapters" / ".trash"
    assert trash.is_dir()
    assert any(p.is_dir() for p in trash.iterdir())


def test_chapter_delete_cancelled(cli_runner, initialized_project):
    cli_runner.invoke(app, ["chapter", "new", "The Early Years"], catch_exceptions=False)

    result = cli_runner.invoke(app, ["chapter", "delete", "1"], input="n\n")
    assert result.exit_code == 0
    assert (initialized_project / "chapters" / "chapter-01").is_dir()


# ── chapter restore ───────────────────────────────────────────────────────────

def test_chapter_restore_restores_chapter(cli_runner, initialized_project):
    cli_runner.invoke(app, ["chapter", "new", "The Early Years"], catch_exceptions=False)
    cli_runner.invoke(app, ["chapter", "delete", "1"], input="y\n", catch_exceptions=False)

    result = cli_runner.invoke(app, ["chapter", "restore"], input="1\n")
    assert result.exit_code == 0
    assert (initialized_project / "chapters" / "chapter-01").is_dir()


# ── note add-source ───────────────────────────────────────────────────────────

def test_note_add_source_creates_files(cli_runner, initialized_project):
    result = cli_runner.invoke(app, ["note", "add-source", "Interview with Aunt Rosa"])
    assert result.exit_code == 0

    notes_dir = initialized_project / "notes" / "source"
    assert any(notes_dir.glob("*.md"))
    assert any(notes_dir.glob("*.meta.yaml"))


def test_note_add_source_meta_fields(cli_runner, initialized_project):
    cli_runner.invoke(
        app, ["note", "add-source", "Interview with Aunt Rosa"], catch_exceptions=False
    )

    notes_dir = initialized_project / "notes" / "source"
    meta_file = next(notes_dir.glob("*.meta.yaml"))
    meta = yaml.safe_load(meta_file.read_text())
    assert meta["title"] == "Interview with Aunt Rosa"
    assert meta["source_type"] == "memory"  # default
    assert meta.get("created_at")           # non-empty timestamp, no exact value check


# ── note list ─────────────────────────────────────────────────────────────────

def test_note_list_shows_note(cli_runner, initialized_project):
    cli_runner.invoke(
        app, ["note", "add-source", "Interview with Aunt Rosa"], catch_exceptions=False
    )
    result = cli_runner.invoke(app, ["note", "list"])
    assert result.exit_code == 0
    assert "Interview with Aunt Rosa" in result.output


# ── scan ──────────────────────────────────────────────────────────────────────

def test_scan_auto_creates_db(cli_runner, initialized_project):
    db_path = initialized_project / ".altamira" / "app.db"
    db_path.unlink(missing_ok=True)

    result = cli_runner.invoke(app, ["scan"])
    assert result.exit_code == 0
    assert db_path.exists()


def test_scan_indexes_chapter_files(cli_runner, initialized_project):
    cli_runner.invoke(app, ["chapter", "new", "The Early Years"], catch_exceptions=False)
    cli_runner.invoke(app, ["scan"], catch_exceptions=False)

    engine = get_engine(initialized_project)
    with engine.connect() as conn:
        rows = conn.execute(select(indexed_files)).fetchall()
    assert len(rows) > 0


# ── db show ───────────────────────────────────────────────────────────────────

def test_db_show_after_scan(cli_runner, initialized_project):
    cli_runner.invoke(app, ["scan"], catch_exceptions=False)

    result = cli_runner.invoke(app, ["db", "show"])
    assert result.exit_code == 0
    assert "Indexed files" in result.output


def test_db_show_auto_creates_db(cli_runner, initialized_project):
    db_path = initialized_project / ".altamira" / "app.db"
    db_path.unlink(missing_ok=True)

    result = cli_runner.invoke(app, ["db", "show"])
    assert result.exit_code == 0
    assert db_path.exists()
