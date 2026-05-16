# Repository Guidelines

## Project Structure & Module Organization

Altamira CLI is a Python 3.11+ package using a `src/` layout. Application code lives in `src/altamira/`:

- `cli/`: Typer command groups and the interactive REPL; `app.py` wires the CLI together.
- `domain/`: filesystem-first chapter, note, and publish logic. Keep this layer free of LLM and DB dependencies.
- `infra/`: SQLite index, scanner, and watcher support. The DB is a cache; Markdown/YAML files are canonical.
- `services/`: LLM provider integration, reviewer, and rewriter logic.
- `skills/prompts/`: bundled prompt templates loaded with `importlib.resources`.
- `publish/templates/`: Jinja2 HTML publishing templates.

Tests are under `tests/`, grouped by feature area (`tests/cli`, `tests/services`, `tests/tools`). `myanbio/` is a committed sample project for manual testing.

## Build, Test, and Development Commands

```bash
pip install -e ".[dev]"      # editable install with pytest
altamira --help              # verify the CLI entry point
altamira                     # launch the REPL
pytest                       # run all tests
pytest -m smoke              # run end-to-end lifecycle tests
pytest -m "not smoke"        # skip slower smoke tests
pytest tests/cli/test_publish.py
```

The package is built with setuptools via `pyproject.toml`; there is no separate build script.

## Coding Style & Naming Conventions

Follow existing Python style: 4-space indentation, type hints for public interfaces, small functions, and explicit imports. Use `snake_case` for modules, functions, variables, and pytest names. CLI command modules follow the pattern `<group>_cmd.py`. Tests should be named `test_*.py` and test functions `test_*`.

Preserve key domain conventions: chapter IDs may be numeric or `chapter-NN`; history files are append-only; rewrite flows must save a snapshot under `versions/YYYYMMDD-HHMMSS.md`.

## Testing Guidelines

Use pytest. Add focused tests near the behavior changed, and prefer fixtures from `tests/conftest.py` (`initialized_project`, `sample_chapter`, `sample_source_note`) over ad hoc setup. Mark full lifecycle tests with `@pytest.mark.smoke`; use `@pytest.mark.regression` for previously fixed bugs.

## Commit & Pull Request Guidelines

Recent history uses concise subject lines, usually Conventional Commit prefixes such as `feat:` and `fix:`; keep using that style, for example `fix: preserve chapter history on rewrite`. PRs should describe the behavior change, list test commands run, link related issues, and include terminal output or screenshots only when UI/CLI behavior is easier to review visually.

## Security & Configuration Tips

Do not commit API keys. LLM behavior is configured with `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `ALTAMIRA_PROVIDER`, and `ALTAMIRA_MODEL`. Keep provider changes isolated in `src/altamira/services/provider.py` when possible.
