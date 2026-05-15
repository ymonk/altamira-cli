import yaml

from altamira.cli.app import app


# ── init ──────────────────────────────────────────────────────────────────────

_EXPECTED_DIRS = [
    "chapters",
    "materials/raw",
    "notes/source",
    "publish/preview",
    ".altamira",
]


def test_init_named_subdir_creates_structure(cli_runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = cli_runner.invoke(app, ["init", "myproject"])
    assert result.exit_code == 0

    root = tmp_path / "myproject"
    assert (root / "altamira.yaml").exists()
    for d in _EXPECTED_DIRS:
        assert (root / d).is_dir(), f"missing directory: {d}"


def test_init_dot_creates_structure(cli_runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = cli_runner.invoke(app, ["init", "."])
    assert result.exit_code == 0

    assert (tmp_path / "altamira.yaml").exists()
    for d in _EXPECTED_DIRS:
        assert (tmp_path / d).is_dir(), f"missing directory: {d}"


def test_init_yaml_required_fields(cli_runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli_runner.invoke(app, ["init", "."], catch_exceptions=False)

    config = yaml.safe_load((tmp_path / "altamira.yaml").read_text())
    assert "name" in config
    assert "version" in config
    assert "subject_type" in config
    assert config["subject_type"] in ("person", "event")
    assert "subject_name" in config
    assert "language" in config


def test_init_duplicate_fails(cli_runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli_runner.invoke(app, ["init", "."], catch_exceptions=False)

    result = cli_runner.invoke(app, ["init", "."])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_init_force_overwrites(cli_runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli_runner.invoke(app, ["init", "."], catch_exceptions=False)

    result = cli_runner.invoke(app, ["init", ".", "--force"])
    assert result.exit_code == 0


# ── status ────────────────────────────────────────────────────────────────────

def test_status_in_project(cli_runner, initialized_project):
    result = cli_runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "project" in result.output
    assert "chapters" in result.output
    assert "notes" in result.output


def test_status_outside_project(cli_runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = cli_runner.invoke(app, ["status"])
    assert result.exit_code == 1
    assert "Error" in result.output


# ── config show ───────────────────────────────────────────────────────────────

def test_config_show_in_project(cli_runner, initialized_project):
    result = cli_runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    for field in ("name", "version", "subject_type", "language"):
        assert field in result.output, f"missing field in output: {field}"


def test_config_show_outside_project(cli_runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = cli_runner.invoke(app, ["config", "show"])
    assert result.exit_code == 1
    assert "Error" in result.output
