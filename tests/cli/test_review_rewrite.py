import pytest

import altamira.cli.review_cmd as review_cmd
from altamira.cli.app import app
from altamira.domain.chapter import create_chapter
from altamira.services.reviewer import mock_review

# Four body paragraphs — each contains a word from _SUBSTITUTIONS so mock_rewrite
# produces exactly one change per paragraph.
#
#   Para 1: "very "     → "quite "
#   Para 2: " worked "  → " labored "
#   Para 3: "memorized" → "committed to memory"
#   Para 4: "lively"    → "vibrant"
_CHAPTER_CONTENT = (
    "# The Early Years\n"
    "\n"
    "Rosa was born in a very small town in the heart of Catalonia.\n"
    "\n"
    "She worked long hours alongside her mother, learning the rhythms of the household.\n"
    "\n"
    "The stories she memorized as a child stayed with her for a lifetime.\n"
    "\n"
    "Those lively memories of her early years carried her forward always.\n"
)


@pytest.fixture
def chapter_with_content(initialized_project):
    """Initialized project with a four-paragraph chapter pre-written to disk."""
    md_path, _, history_path = create_chapter(
        initialized_project / "chapters", "The Early Years"
    )
    md_path.write_text(_CHAPTER_CONTENT)
    chapter_dir = initialized_project / "chapters" / "chapter-01"
    return initialized_project, chapter_dir, md_path, history_path


@pytest.fixture
def patch_reviewer(monkeypatch):
    """Patch _reviewer on the module so review tests use the deterministic mock."""
    monkeypatch.setattr(review_cmd, "_reviewer", mock_review)


# ── review ────────────────────────────────────────────────────────────────────

def test_review_accept_one_creates_artifact(cli_runner, chapter_with_content, patch_reviewer):
    _, chapter_dir, _, history_path = chapter_with_content

    result = cli_runner.invoke(app, ["review", "1"], input="a\nr\nr\nr\n")
    assert result.exit_code == 0

    reviews_dir = chapter_dir / "reviews"
    artifacts = list(reviews_dir.glob("*.md"))
    assert len(artifacts) == 1

    history = history_path.read_text()
    assert "— review" in history
    assert "- accepted: 1" in history
    assert "- rejected: 3" in history
    assert "- artifact:" in history


def test_review_reject_all_writes_nothing(cli_runner, chapter_with_content, patch_reviewer):
    _, chapter_dir, _, history_path = chapter_with_content
    original_history = history_path.read_text()

    result = cli_runner.invoke(app, ["review", "1"], input="r\nr\nr\nr\n")
    assert result.exit_code == 0

    assert not (chapter_dir / "reviews").exists()
    assert history_path.read_text() == original_history


def test_review_accept_all_records_all_comments(cli_runner, chapter_with_content, patch_reviewer):
    _, chapter_dir, _, history_path = chapter_with_content

    result = cli_runner.invoke(app, ["review", "1"], input="A\n")
    assert result.exit_code == 0

    artifacts = list((chapter_dir / "reviews").glob("*.md"))
    assert len(artifacts) == 1

    history = history_path.read_text()
    assert "- accepted: 4" in history
    assert "- rejected: 0" in history


def test_review_artifact_contains_accepted_comment(cli_runner, chapter_with_content, patch_reviewer):
    _, chapter_dir, _, _ = chapter_with_content

    cli_runner.invoke(app, ["review", "1"], input="a\nr\nr\nr\n", catch_exceptions=False)

    artifact = next((chapter_dir / "reviews").glob("*.md"))
    content = artifact.read_text()
    # Artifact must include the quoted paragraph text and a comment
    assert "Rosa" in content
    assert "Comment:" in content


# ── rewrite ───────────────────────────────────────────────────────────────────

def test_rewrite_accept_one_modifies_md(cli_runner, chapter_with_content):
    _, chapter_dir, md_path, history_path = chapter_with_content

    result = cli_runner.invoke(app, ["rewrite", "1"], input="a\nr\nr\nr\n")
    assert result.exit_code == 0

    content = md_path.read_text()
    # Para 1 accepted: "very " → "quite "; original word gone
    assert "quite" in content
    assert "very " not in content
    # Paras 2–4 rejected: original words still present
    assert " worked " in content
    assert "memorized" in content
    assert "lively" in content

    versions = list((chapter_dir / "versions").glob("*.md"))
    assert len(versions) == 1

    history = history_path.read_text()
    assert "— rewrite" in history
    assert "- accepted: 1" in history
    assert "- rejected: 3" in history
    assert "- checkpoint:" in history


def test_rewrite_reject_all_keeps_md(cli_runner, chapter_with_content):
    _, chapter_dir, md_path, history_path = chapter_with_content
    original_history = history_path.read_text()

    result = cli_runner.invoke(app, ["rewrite", "1"], input="r\nr\nr\nr\n")
    assert result.exit_code == 0

    assert md_path.read_text() == _CHAPTER_CONTENT
    assert not (chapter_dir / "versions").exists()
    assert history_path.read_text() == original_history


def test_rewrite_accept_all_applies_all_changes(cli_runner, chapter_with_content):
    _, chapter_dir, md_path, history_path = chapter_with_content

    result = cli_runner.invoke(app, ["rewrite", "1"], input="A\n")
    assert result.exit_code == 0

    content = md_path.read_text()
    assert "quite" in content                # para 1: "very " → "quite "
    assert "extended" in content            # para 2: "long hours" → "extended hours"
    assert "committed to memory" in content  # para 3: "memorized" → "committed to memory"
    assert "vibrant" in content              # para 4: "lively" → "vibrant"

    history = history_path.read_text()
    assert "- accepted: 4" in history
    assert "- rejected: 0" in history


def test_rewrite_checkpoint_preserves_original(cli_runner, chapter_with_content):
    _, chapter_dir, md_path, _ = chapter_with_content

    cli_runner.invoke(app, ["rewrite", "1"], input="a\nr\nr\nr\n", catch_exceptions=False)

    checkpoint = next((chapter_dir / "versions").glob("*.md"))
    # Checkpoint must be the pre-rewrite original, not the modified version
    assert checkpoint.read_text() == _CHAPTER_CONTENT
