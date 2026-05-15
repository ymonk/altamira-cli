# Altamira CLI

A local-first CLI for memoir and biography writing projects. All data lives on disk as plain Markdown and YAML files — no cloud sync, no proprietary formats.

## Installation

Requires Python 3.11+.

```bash
pip install -e .
```

This registers the `altamira` command via the console scripts entry point.

## Quick Start

```bash
# Create a new project
altamira init mybio
cd mybio

# Add chapters
altamira chapter new "The Early Years"
altamira chapter new "Leaving Home"

# Add source notes
altamira note add-source "Interview with Aunt Rosa" --type interview --tag family

# Enter the interactive REPL
altamira
```

Running `altamira` with no arguments launches the REPL. All subcommands are available there prefixed with `/` (e.g. `/chapter list`, `/review`, `/rewrite`).

## Commands

| Command | Description |
|---|---|
| `altamira init <dir>` | Initialize a new project |
| `altamira status` | Show project summary and file counts |
| `altamira scan` | Index chapters, materials, and notes into SQLite |
| `altamira watch` | Auto-reindex on file changes |
| `altamira chapter new/list/delete/restore` | Manage chapters |
| `altamira note add-source/list` | Manage source notes |
| `altamira review <n>` | Review a chapter paragraph by paragraph |
| `altamira rewrite <n>` | Rewrite a chapter paragraph by paragraph |
| `altamira outline generate` | Generate a chapter outline via LLM |
| `altamira publish prepare` | Check readiness for publishing |
| `altamira publish build` | Build a self-contained HTML book preview |
| `altamira skill list/show` | List or inspect built-in LLM prompt skills |
| `altamira db init/show` | Manage the SQLite file index |

See `altamira-cli-man.md` for the full reference.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required for Anthropic (default provider) |
| `OPENAI_API_KEY` | — | Required if using OpenAI |
| `ALTAMIRA_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `ALTAMIRA_MODEL` | `claude-sonnet-4-6` / `gpt-4o` | Model override |
| `ALTAMIRA_EDITOR` | system default | Editor for `/open` |

## Project Layout

```
<project>/
  altamira.yaml          Project config
  chapters/
    chapter-01/
      chapter-01.md          Working file
      chapter-01.meta.yaml   Title, status, prompt
      chapter-01.history.md  Append-only change log
      reviews/               Accepted review sessions
      versions/              Pre-rewrite snapshots
    .trash/                  Deleted chapters (timestamped)
  notes/source/          Source notes (.md + .meta.yaml)
  materials/raw/         Raw documents and images
  workspace/             Generated output (outlines, etc.)
  publish/preview/       Built HTML book
  .altamira/app.db       SQLite file index
```

## Development

```bash
pip install -e ".[dev]"
pytest                    # all tests
pytest -m smoke           # full lifecycle test
pytest -m "not smoke"     # everything else
```
