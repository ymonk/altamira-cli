# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable, with dev deps)
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/cli/test_chapter_note_scan_db.py

# Run a single test by name
pytest tests/cli/test_review_rewrite.py::test_review_accept_all

# Run only smoke tests (full lifecycle)
pytest -m smoke

# Run everything except smoke tests
pytest -m "not smoke"

# Run the CLI
altamira --help
altamira               # enters the REPL
```

## Architecture

The package lives under `src/altamira/` and is split into five layers:

**`cli/`** — Typer-based commands, one file per command group (`chapter_cmd.py`, `review_cmd.py`, etc.). `app.py` wires them all together. When invoked with no subcommand, the callback launches `repl.py`. The REPL's `/commands` delegate to the same domain/service functions the CLI uses — they are not re-implemented.

**`domain/`** — Pure file-system logic with no LLM or DB dependencies. `chapter.py` owns creation, listing, deletion, and restore of chapters as `chapter-NN/` directories. `note.py` owns source notes. `publish.py` owns publish-readiness checks. All persistent state is plain Markdown + YAML files on disk.

**`infra/`** — SQLite index managed via SQLAlchemy Core (not ORM). `db.py` defines three tables (`indexed_files`, `source_notes_index`, `scan_state`) and `ensure_tables()` for lazy init. `scanner.py` walks the project and upserts rows. `watcher.py` wraps Watchdog with a 0.4 s debounce. The DB is a cache of the file system — the canonical source of truth is always the files.

**`services/`** — LLM integration. `provider.py` defines `ProviderFn = Callable[[str], str]` — the single interface the rest of the codebase depends on. `reviewer.py` and `rewriter.py` are currently **mock implementations** (simple text substitutions) with clear comments saying "replace with an LLM call to go live." `get_provider()` in `provider.py` selects the backend via `ALTAMIRA_PROVIDER`.

**`config/`** — `ProjectConfig` (Pydantic model) loaded from `altamira.yaml` in the project root. `loader.py` handles reading and writing.

**`skills/`** — Prompt templates stored as `.md` files under `src/altamira/skills/prompts/`, loaded via `importlib.resources`. `loader.py` provides `list_skills()` and `load_skill(name)`. Adding a new skill means adding a `.md` file there — no code change needed.

**`publish/`** — A single Jinja2 template (`templates/book.html.j2`) that renders all chapters into a self-contained HTML file. Images are resolved from chapter directories, project root, and `materials/raw/`, then copied into `publish/preview/images/`.

## Key Conventions

- **Chapter identifiers**: commands accept either a number (`3`) or a slug (`chapter-03`). `find_chapter()` in `domain/chapter.py` resolves both.
- **History files** (`*.history.md`) are append-only structured logs; never overwrite them.
- **Before rewriting**, a snapshot is always saved to `versions/YYYYMMDD-HHMMSS.md`.
- **DB is optional**: `scan`, `watch`, and `db show` all call `ensure_tables()` to auto-initialize — explicit `db init` is a no-op if DB exists.
- **Provider swap**: to add a new LLM backend, add a factory function to `services/provider.py` and register it in `_PROVIDERS`. Nothing else changes.

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required for Anthropic provider |
| `OPENAI_API_KEY` | — | Required for OpenAI provider |
| `ALTAMIRA_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `ALTAMIRA_MODEL` | `claude-sonnet-4-6` / `gpt-4o` | Model name override |
| `ALTAMIRA_EDITOR` | system default | Editor for `/open` command |

## Test Fixtures

`tests/conftest.py` provides project-level fixtures used across all test files:
- `initialized_project` — temp dir with `altamira init .` already run, set as cwd via `monkeypatch`
- `sample_chapter` — initialized project with one chapter created
- `sample_source_note` — initialized project with one source note created

## Sample Project

`myanbio/` in the repo root is a real working Altamira project used for manual testing. Its SQLite DB is committed at `myanbio/.altamira/app.db`.
