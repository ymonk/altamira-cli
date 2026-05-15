import pytest
from typer.testing import CliRunner

from altamira.cli.app import app
from altamira.domain.chapter import create_chapter
from altamira.domain.note import create_note


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def temp_project_dir(tmp_path):
    """Bare temporary directory with no altamira.yaml."""
    return tmp_path


@pytest.fixture
def initialized_project(tmp_path, monkeypatch, cli_runner):
    """Temporary directory initialized as an Altamira project, set as cwd."""
    monkeypatch.chdir(tmp_path)
    result = cli_runner.invoke(app, ["init", "."], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return tmp_path


@pytest.fixture
def sample_chapter(initialized_project):
    """One chapter inside an initialized project."""
    _, meta, _ = create_chapter(initialized_project / "chapters", "The Early Years")
    return initialized_project, meta


@pytest.fixture
def sample_source_note(initialized_project):
    """One source note inside an initialized project."""
    _, meta = create_note(initialized_project / "notes" / "source", "Interview with Aunt Rosa")
    return initialized_project, meta
