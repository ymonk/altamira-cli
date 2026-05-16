from altamira import __version__
from altamira.cli.app import app


def test_version(cli_runner):
    result = cli_runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_doctor(cli_runner):
    result = cli_runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Python" in result.output
    assert "SQLite" in result.output


def test_help(cli_runner):
    result = cli_runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "altamira" in result.output.lower()


# ── --llm-list flag ───────────────────────────────────────────────────────────

def test_llm_list_flag_exits_zero(cli_runner):
    result = cli_runner.invoke(app, ["--llm-list"])
    assert result.exit_code == 0


def test_llm_list_flag_shows_providers(cli_runner):
    result = cli_runner.invoke(app, ["--llm-list"])
    assert "anthropic" in result.output
    assert "openai" in result.output


def test_llm_list_flag_marks_active_model(cli_runner, monkeypatch):
    monkeypatch.setenv("ALTAMIRA_PROVIDER", "anthropic")
    monkeypatch.setenv("ALTAMIRA_MODEL", "claude-sonnet-4-6")
    result = cli_runner.invoke(app, ["--llm-list"])
    assert "* claude-sonnet-4-6" in result.output


def test_llm_list_flag_active_tracks_env_override(cli_runner, monkeypatch):
    monkeypatch.setenv("ALTAMIRA_PROVIDER", "openai")
    monkeypatch.setenv("ALTAMIRA_MODEL", "gpt-4o-mini")
    result = cli_runner.invoke(app, ["--llm-list"])
    assert "* gpt-4o-mini" in result.output


def test_llm_list_flag_unknown_model_shown_as_active(cli_runner, monkeypatch):
    monkeypatch.setenv("ALTAMIRA_PROVIDER", "anthropic")
    monkeypatch.setenv("ALTAMIRA_MODEL", "claude-future-99")
    result = cli_runner.invoke(app, ["--llm-list"])
    assert "* claude-future-99" in result.output


# ── --llm-activate flag ───────────────────────────────────────────────────────

def test_llm_activate_writes_to_config(cli_runner, initialized_project, monkeypatch):
    monkeypatch.chdir(initialized_project)
    result = cli_runner.invoke(app, ["--llm-activate", "gpt-4o"])
    assert result.exit_code == 0
    assert "gpt-4o" in result.output

    from altamira.config.loader import load_config
    config = load_config(initialized_project)
    assert config.model == "gpt-4o"
    assert config.provider == "openai"


def test_llm_activate_marks_new_model_as_active(cli_runner, initialized_project, monkeypatch):
    monkeypatch.chdir(initialized_project)
    result = cli_runner.invoke(app, ["--llm-activate", "claude-opus-4-7"])
    assert result.exit_code == 0
    assert "* claude-opus-4-7" in result.output


def test_llm_activate_rejects_unknown_model(cli_runner, initialized_project, monkeypatch):
    monkeypatch.chdir(initialized_project)
    result = cli_runner.invoke(app, ["--llm-activate", "no-such-model-99"])
    assert result.exit_code == 0
    assert "Unknown model" in result.output

    from altamira.config.loader import load_config
    config = load_config(initialized_project)
    assert config.model == ""


def test_llm_activate_requires_project(cli_runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = cli_runner.invoke(app, ["--llm-activate", "gpt-4o"])
    assert result.exit_code == 0
    assert "Not in an Altamira project" in result.output
