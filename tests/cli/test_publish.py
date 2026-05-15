import yaml
import pytest

from altamira.cli.app import app
from altamira.domain.chapter import create_chapter


# ── shared helpers ────────────────────────────────────────────────────────────

def _set_meta(meta_path, **overrides):
    """Read a chapter .meta.yaml, apply overrides, write it back."""
    data = yaml.safe_load(meta_path.read_text())
    data.update(overrides)
    meta_path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )


def _set_config(project, **overrides):
    """Read altamira.yaml, apply overrides, write it back."""
    config_path = project / "altamira.yaml"
    data = yaml.safe_load(config_path.read_text())
    data.update(overrides)
    config_path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )


@pytest.fixture
def publishable_project(initialized_project):
    """Project with one chapter that passes every prepare check."""
    md_path, meta_path, _ = create_chapter(
        initialized_project / "chapters", "The Early Years"
    )
    md_path.write_text("# The Early Years\n\nRosa grew up in a vibrant town near the coast.\n")
    _set_meta(meta_path, status="complete", summary="The story of Rosa's early life.")
    return initialized_project


# ── publish prepare — success ─────────────────────────────────────────────────

def test_prepare_clean_project_passes(cli_runner, publishable_project):
    result = cli_runner.invoke(app, ["publish", "prepare"])
    assert result.exit_code == 0
    assert "All checks passed" in result.output


# ── publish prepare — warnings (exit 0) ──────────────────────────────────────

def test_prepare_draft_status_warns(cli_runner, initialized_project):
    md_path, meta_path, _ = create_chapter(initialized_project / "chapters", "Draft Chapter")
    md_path.write_text("# Draft Chapter\n\nSome body content.\n")
    _set_meta(meta_path, status="draft", summary="Has a summary.")

    result = cli_runner.invoke(app, ["publish", "prepare"])
    assert result.exit_code == 0
    assert "draft" in result.output


def test_prepare_missing_summary_warns(cli_runner, initialized_project):
    md_path, meta_path, _ = create_chapter(initialized_project / "chapters", "The Early Years")
    md_path.write_text("# The Early Years\n\nSome body content.\n")
    _set_meta(meta_path, status="complete", summary="")

    result = cli_runner.invoke(app, ["publish", "prepare"])
    assert result.exit_code == 0
    assert "Summary is empty" in result.output


def test_prepare_heading_only_body_warns(cli_runner, initialized_project):
    md_path, meta_path, _ = create_chapter(initialized_project / "chapters", "The Early Years")
    md_path.write_text("# The Early Years\n")  # no body beyond heading
    _set_meta(meta_path, status="complete", summary="Has a summary.")

    result = cli_runner.invoke(app, ["publish", "prepare"])
    assert result.exit_code == 0
    assert "only a heading" in result.output


# ── publish prepare — errors (exit 1) ────────────────────────────────────────

def test_prepare_missing_md_errors(cli_runner, initialized_project):
    md_path, meta_path, _ = create_chapter(initialized_project / "chapters", "The Early Years")
    _set_meta(meta_path, status="complete", summary="Has a summary.")
    md_path.unlink()  # remove after meta is in place

    result = cli_runner.invoke(app, ["publish", "prepare"])
    assert result.exit_code == 1
    assert "Markdown file not found" in result.output


def test_prepare_empty_title_errors(cli_runner, initialized_project):
    md_path, meta_path, _ = create_chapter(initialized_project / "chapters", "The Early Years")
    md_path.write_text("# The Early Years\n\nSome body content.\n")
    _set_meta(meta_path, status="complete", summary="Has a summary.", title="")

    result = cli_runner.invoke(app, ["publish", "prepare"])
    assert result.exit_code == 1
    assert "Title is empty" in result.output


def test_prepare_missing_cover_errors(cli_runner, publishable_project):
    _set_config(publishable_project, cover="materials/raw/cover.jpg")
    # cover file is NOT created on disk

    result = cli_runner.invoke(app, ["publish", "prepare"])
    assert result.exit_code == 1
    assert "Cover image not found" in result.output


# ── publish build — core output ───────────────────────────────────────────────

def test_build_creates_index_html(cli_runner, publishable_project):
    result = cli_runner.invoke(app, ["publish", "build"])
    assert result.exit_code == 0
    assert (publishable_project / "publish" / "preview" / "index.html").exists()


def test_build_includes_project_title(cli_runner, publishable_project):
    cli_runner.invoke(app, ["publish", "build"], catch_exceptions=False)
    html = (publishable_project / "publish" / "preview" / "index.html").read_text()
    project_name = publishable_project.name
    assert project_name in html


def test_build_includes_chapter_title(cli_runner, publishable_project):
    cli_runner.invoke(app, ["publish", "build"], catch_exceptions=False)
    html = (publishable_project / "publish" / "preview" / "index.html").read_text()
    assert "The Early Years" in html


def test_build_includes_chapter_body_html(cli_runner, publishable_project):
    cli_runner.invoke(app, ["publish", "build"], catch_exceptions=False)
    html = (publishable_project / "publish" / "preview" / "index.html").read_text()
    # Python-Markdown wraps paragraphs in <p> tags
    assert "<p>" in html
    assert "Rosa grew up" in html


def test_build_includes_nav_sidebar(cli_runner, publishable_project):
    cli_runner.invoke(app, ["publish", "build"], catch_exceptions=False)
    html = (publishable_project / "publish" / "preview" / "index.html").read_text()
    assert 'href="#chapter-01"' in html
    assert "book-title" in html


# ── publish build — image handling ───────────────────────────────────────────

@pytest.fixture
def project_with_image(publishable_project):
    """publishable_project extended with a fake image referenced in the chapter."""
    image_src = publishable_project / "materials" / "raw" / "photo.jpg"
    image_src.write_bytes(b"fake-image-data")

    chapter_dir = publishable_project / "chapters" / "chapter-01"
    md_path = chapter_dir / "chapter-01.md"
    md_path.write_text(
        "# The Early Years\n\n"
        "Rosa grew up in a vibrant town near the coast.\n\n"
        "![Photo](photo.jpg)\n"
    )
    return publishable_project


def test_build_image_copied_to_images_dir(cli_runner, project_with_image):
    cli_runner.invoke(app, ["publish", "build"], catch_exceptions=False)
    assert (project_with_image / "publish" / "preview" / "images" / "photo.jpg").exists()


def test_build_image_path_rewritten_in_html(cli_runner, project_with_image):
    cli_runner.invoke(app, ["publish", "build"], catch_exceptions=False)
    html = (project_with_image / "publish" / "preview" / "index.html").read_text()
    assert 'src="images/photo.jpg"' in html
    # original relative path must not survive into the output
    assert '(photo.jpg)' not in html
