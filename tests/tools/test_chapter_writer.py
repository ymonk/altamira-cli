import pytest
from altamira.domain.chapter import create_chapter
from altamira.tools.chapter_writer import write_chapter


NEW_CONTENT = "# The Early Years\n\nRevised opening paragraph.\n\nSecond paragraph added by the agent.\n"


def test_write_chapter_creates_md_content(initialized_project):
    create_chapter(initialized_project / "chapters", "The Early Years")
    result = write_chapter("1", NEW_CONTENT, project_root=initialized_project)
    md = (initialized_project / "chapters" / "chapter-01" / "chapter-01.md").read_text()
    assert md == NEW_CONTENT


def test_write_chapter_creates_version_snapshot(initialized_project):
    create_chapter(initialized_project / "chapters", "The Early Years")
    result = write_chapter("1", NEW_CONTENT, project_root=initialized_project)
    checkpoint = (initialized_project / "chapters" / "chapter-01" / "versions").iterdir()
    assert any(True for _ in checkpoint), "versions/ should contain at least one snapshot"


def test_write_chapter_snapshot_contains_original(initialized_project):
    create_chapter(initialized_project / "chapters", "The Early Years")
    original = (initialized_project / "chapters" / "chapter-01" / "chapter-01.md").read_text()
    result = write_chapter("1", NEW_CONTENT, project_root=initialized_project)
    from pathlib import Path
    checkpoint_text = Path(result["checkpoint"]).read_text()
    assert checkpoint_text == original


def test_write_chapter_appends_history_entry(initialized_project):
    create_chapter(initialized_project / "chapters", "The Early Years")
    write_chapter("1", NEW_CONTENT, reason="Agent draft", project_root=initialized_project)
    history = (initialized_project / "chapters" / "chapter-01" / "chapter-01.history.md").read_text()
    assert "agent write" in history
    assert "Agent draft" in history


def test_write_chapter_history_records_bytes(initialized_project):
    create_chapter(initialized_project / "chapters", "The Early Years")
    write_chapter("1", NEW_CONTENT, project_root=initialized_project)
    history = (initialized_project / "chapters" / "chapter-01" / "chapter-01.history.md").read_text()
    assert "bytes:" in history


def test_write_chapter_returns_expected_keys(initialized_project):
    create_chapter(initialized_project / "chapters", "The Early Years")
    result = write_chapter("1", NEW_CONTENT, project_root=initialized_project)
    assert result["chapter"] == "chapter-01"
    assert result["bytes_written"] == len(NEW_CONTENT.encode())
    assert "checkpoint" in result
    assert "history_path" in result
    assert "md_path" in result


def test_write_chapter_accepts_slug_identifier(initialized_project):
    create_chapter(initialized_project / "chapters", "The Early Years")
    result = write_chapter("chapter-01", NEW_CONTENT, project_root=initialized_project)
    assert result["chapter"] == "chapter-01"


def test_write_chapter_raises_for_missing_chapter(initialized_project):
    with pytest.raises(FileNotFoundError):
        write_chapter("99", NEW_CONTENT, project_root=initialized_project)
