"""
End-to-end smoke test: happy path through the full project lifecycle.
Run with: pytest -m smoke
"""
import yaml
import pytest

from altamira.cli.app import app


@pytest.mark.smoke
def test_full_project_lifecycle(cli_runner, initialized_project):
    """init → chapter → note → scan → review (accept all) → publish prepare → build → index.html"""

    # chapter new
    result = cli_runner.invoke(app, ["chapter", "new", "The Early Years"], catch_exceptions=False)
    assert result.exit_code == 0

    chapter_dir = initialized_project / "chapters" / "chapter-01"
    md_path = chapter_dir / "chapter-01.md"
    meta_path = chapter_dir / "chapter-01.meta.yaml"

    # write chapter body
    md_path.write_text(
        "# The Early Years\n\n"
        "Rosa grew up in a very small town near the coast of Catalonia.\n\n"
        "She memorized the stories her mother told her every evening.\n"
    )

    # mark chapter complete with a summary
    data = yaml.safe_load(meta_path.read_text())
    data["status"] = "complete"
    data["summary"] = "Rosa's childhood near the Catalan coast."
    meta_path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )

    # note add-source
    result = cli_runner.invoke(
        app, ["note", "add-source", "Interview with Aunt Rosa"], catch_exceptions=False
    )
    assert result.exit_code == 0

    # scan
    result = cli_runner.invoke(app, ["scan"], catch_exceptions=False)
    assert result.exit_code == 0

    # review: accept all suggestions
    result = cli_runner.invoke(app, ["review", "1"], input="A\n")
    assert result.exit_code == 0

    # publish prepare — should pass cleanly
    result = cli_runner.invoke(app, ["publish", "prepare"])
    assert result.exit_code == 0
    assert "All checks passed" in result.output

    # publish build
    result = cli_runner.invoke(app, ["publish", "build"], catch_exceptions=False)
    assert result.exit_code == 0

    index_html = initialized_project / "publish" / "preview" / "index.html"
    assert index_html.exists()
    html = index_html.read_text()
    assert "The Early Years" in html
