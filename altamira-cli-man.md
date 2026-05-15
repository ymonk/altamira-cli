# Altamira CLI — Manual

Altamira is a local-first CLI for memoir and biography writing projects. All data lives on disk as plain Markdown and YAML files.

Running `altamira` with no arguments enters an interactive REPL. All subcommands remain available as before.

---

## REPL Mode

```
altamira
```

Launches the interactive REPL. Commands start with `/`. The REPL detects whether the current directory is an Altamira project and shows a notice if not.

### REPL commands

| Command | Description |
|---|---|
| `/help` | List all commands with descriptions |
| `/commands` | Compact command name list (quick reference) |
| `/history` | Show commands entered this session |
| `/clear` | Clear the screen |
| `/status` | Show project name, subject, chapter and note counts |
| `/config show` | Show all `altamira.yaml` fields |
| `/skill list` | List available prompt skills |
| `/chapter list` | List all chapters |
| `/chapter new <title>` | Create a new chapter |
| `/chapter delete <n>` | Move chapter n to trash (prompts for confirmation) |
| `/scan` | Update the file index (auto-initializes db if needed) |
| `/review [<n>]` | Review chapter paragraph by paragraph (uses current if no arg) |
| `/rewrite [<n>]` | Rewrite chapter paragraph by paragraph (uses current if no arg) |
| `/publish prepare` | Check project readiness for publishing |
| `/use [<n>]` | Select chapter n as current, or show current chapter |
| `/open [<n>]` | Open current or given chapter in the system default app |
| `/note list` | List source notes |
| `/note add <title>` | Create a source note (basic; full options via CLI) |
| `/quit` / `/exit` | Exit the REPL |

`/review` and `/rewrite` share the same interactive flow as their CLI equivalents.  
`/note add` creates a note with default fields. Use `altamira note add-source` for `--type`, `--tag`, `--url`, etc.

---

## Installation

```
pip install -e .
```

Requires Python 3.11+. The `altamira` command is registered as a console script.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | When using Anthropic | API key for Claude models |
| `OPENAI_API_KEY` | When using OpenAI | API key for OpenAI models |
| `ALTAMIRA_PROVIDER` | No | LLM provider to use (`anthropic` or `openai`, default: `anthropic`) |
| `ALTAMIRA_MODEL` | No | Model name override (default: `claude-sonnet-4-6` / `gpt-4o`) |
| `ALTAMIRA_EDITOR` | No | Editor command for `/open` (e.g. `code`, `nvim`). Falls back to system default app. |

---

## Project Layout

```
<project>/
  altamira.yaml          Project config
  chapters/
    chapter-01/
      chapter-01.md          Working chapter file
      chapter-01.meta.yaml
      chapter-01.history.md  Append-only structured log
      reviews/
        20260514-104523.md   Accepted review comments (one file per session)
      versions/
        20260514-110012.md   Pre-rewrite checkpoint snapshots
    .trash/              Deleted chapters (timestamped)
  materials/
    raw/                 Raw source documents and images
  notes/
    source/              Source notes (.md + .meta.yaml pairs)
  workspace/             Generated output (outlines, etc.)
  publish/
    preview/
      index.html         Built HTML book preview
      images/            Copied images referenced by chapters
  .altamira/
    app.db               SQLite file index
```

---

## Top-Level Commands

### `altamira version`

Print the installed version.

### `altamira doctor`

Print system diagnostics: Python version, working directory, SQLite availability.

### `altamira init <directory>`

Initialize a new Altamira project.

```
altamira init .           # initialize in the current directory
altamira init mybio       # create mybio/ and initialize inside it
altamira init . --force   # overwrite existing altamira.yaml
```

Creates the standard directory structure and writes `altamira.yaml`.

### `altamira status`

Show project name, version, subject, language, and file counts for chapters, materials, and notes. Description is shown if set.  
Must be run from inside an Altamira project directory.

### `altamira scan`

Walk `chapters/`, `materials/raw/`, and `notes/source/`, then update the SQLite index (`indexed_files`, `source_notes_index`, `scan_state`). If `.altamira/app.db` does not exist, it is created automatically before scanning.

### `altamira watch`

Watch `chapters/`, `materials/`, and `notes/source/` with Watchdog and re-run the scanner on any file change. Debounced at 0.4 s. Press `Ctrl+C` to stop.

Hidden files, swap files, and the `.altamira/` and `publish/` directories are ignored.

### `altamira review <chapter>`

Review a chapter paragraph by paragraph. For each paragraph that has a comment, prompt to accept (`a`), reject (`r`), or accept all remaining (`A`).

When at least one comment is accepted:
- Accepted comments are written to `reviews/YYYYMMDD-HHMMSS.md` inside the chapter directory.
- A structured entry is appended to `.history.md`.

History entry format:
```markdown
## 2026-05-14 10:45:23 — review

- accepted: 2
- rejected: 1
- artifact: 20260514-104523.md
```

`<chapter>` can be a number (`1`) or a slug (`chapter-01`).

### `altamira rewrite <chapter>`

Rewrite a chapter paragraph by paragraph. Shows original and rewritten text side by side. For each changed paragraph, prompt to accept (`a`), reject (`r`), or accept all remaining (`A`).

When at least one change is accepted:
- A snapshot of the chapter **before** the rewrite is saved to `versions/YYYYMMDD-HHMMSS.md`.
- Accepted changes are written back to the working chapter `.md` file.
- A structured entry is appended to `.history.md`.

History entry format:
```markdown
## 2026-05-14 11:00:12 — rewrite

- accepted: 3
- rejected: 1
- checkpoint: 20260514-110012.md
```

`<chapter>` can be a number (`1`) or a slug (`chapter-01`).

---

## `chapter` Subcommands

### `altamira chapter new <title> [--prompt TEXT]`

Create a new chapter. Adds a numbered subdirectory (`chapter-01/`, `chapter-02/`, etc.) containing:

- `chapter-XX.md` — blank Markdown file with a heading
- `chapter-XX.meta.yaml` — title, slug, order, status, optional writing prompt
- `chapter-XX.history.md` — append-only change log

Warns if a chapter with the same title already exists but still creates it.

**Options:**

| Flag | Description |
|---|---|
| `-m`, `--prompt TEXT` | Writing prompt to attach to this chapter |

### `altamira chapter list`

Display all chapters in a table: number, title, slug, and status.

### `altamira chapter delete <identifier>`

Move a chapter to the trash after confirmation. Displays the chapter title and path before prompting. The chapter is moved to `chapters/.trash/<slug>-<YYYYMMDD-HHMMSS>/`.

`<identifier>` can be a number (`3`) or a slug (`chapter-03`).

### `altamira chapter restore`

Interactively restore a trashed chapter. Lists all trashed chapters with number, original name, title, and timestamp. Enter a number to restore or `N` to cancel. Invalid input re-prompts.

---

## `config` Subcommands

### `altamira config show`

Print the current `altamira.yaml` as formatted key-value pairs.

---

## `note` Subcommands

### `altamira note add-source <title> [options]`

Create a new source note in `notes/source/`. Generates a slugified `.md` file (with a Markdown heading) and a `.meta.yaml` sidecar.

**Options:**

| Flag | Description |
|---|---|
| `-t`, `--type TEXT` | Source type: `memory`, `interview`, `document`, `book`, `article`, `other` (default: `memory`) |
| `--url TEXT` | URL if the source is online |
| `--origin TEXT` | Origin description (person, place, or event) |
| `--tag TEXT` | Tag to attach (repeatable: `--tag family --tag 1970s`) |
| `-s`, `--summary TEXT` | Brief summary of the source |

### `altamira note list`

Display all source notes in a table: title, type, tags, creation date, and summary (truncated at 60 characters).

---

## `publish` Subcommands

### `altamira publish prepare`

Check project readiness for publishing. Runs the following checks against every chapter and the project config:

| Check | Level | Condition |
|---|---|---|
| Chapter completeness | Warning | Status is still `draft` |
| Metadata presence | Error | Title field is empty |
| Summary presence | Warning | Summary field is empty |
| Chapter body | Warning | File contains only a heading, no body text |
| Markdown file | Error | `.md` file is missing from the chapter directory |
| Cover image | Error | `cover` is set in `altamira.yaml` but the file does not exist |
| Source notes | Warning | `require_source_notes: true` in config but `notes/source/` is empty |

Exits with code 1 if any errors are found. Warnings do not block the exit code.

### `altamira publish build`

Convert all chapters to HTML and render a single local book preview at `publish/preview/index.html`.

- Chapters are rendered in order using Python-Markdown (`tables` and `fenced_code` extensions).
- A fixed sidebar provides title and chapter navigation links.
- If `cover` is set in `altamira.yaml` and the file exists, the cover image is copied to `publish/preview/images/` and displayed at the top of the page.
- Images referenced in chapter Markdown (`![alt](path)`) are resolved in order: relative to the chapter directory, then the project root, then `materials/raw/`. Resolved images are copied to `publish/preview/images/` and paths are rewritten in the output.
- The output is fully self-contained (inline CSS, no external CDN dependencies) and works as a local file in any browser.

---

## `outline` Subcommands

### `altamira outline generate`

Generate a chapter outline using an LLM. Builds context from:

- Project name (`altamira.yaml`)
- All chapters with their status and writing prompts
- All source notes in `notes/source/`

Injects context into the `outline_builder` skill prompt and calls the active provider. Output is saved to `workspace/outline.md`.

Requires `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY` if `ALTAMIRA_PROVIDER=openai`) to be set.

---

## `skills` Subcommands

### `altamira skill list`

List all built-in prompt skills with their names and one-line descriptions.

Built-in skills:

| Skill | Purpose |
|---|---|
| `outline_builder` | Generate a chapter outline from project context |
| `chapter_rewriter` | Rewrite chapter prose for clarity and rhythm |
| `source_note_summarizer` | Summarize a source note |
| `timeline_extractor` | Extract a chronological timeline from notes |
| `publish_checker` | Check a chapter for publication readiness |
| `project_init` | Bootstrap prompt for a new project |

### `altamira skill show <name>`

Print the full content of a skill prompt, rendered as Markdown.

---

## `db` Subcommands

### `altamira db init`

Explicitly create the SQLite database at `.altamira/app.db`. This is now optional — `scan`, `watch`, and `db show` all auto-initialize the database if it does not exist. Use this command if you want to set up the database before running a scan, or to confirm the schema is in place.

If the database already exists, the command is a safe no-op (prints "already initialized").

Schema:

| Table | Purpose |
|---|---|
| `indexed_files` | Every tracked file: path, type (`chapter`/`material`/`note`), size, mtime |
| `source_notes_index` | Note metadata from `.meta.yaml`: title, tags, summary |
| `scan_state` | Last scan timestamp and file count per directory |

### `altamira db show`

Summarize database contents: file counts by type, last scan timestamp per directory, and a list of indexed source note titles. Auto-initializes the database if it does not exist.

---

## Testing

The test suite lives in `tests/`. Install dev dependencies and run:

```
pip install -e ".[dev]"
pytest
```

### Test markers

| Marker | Purpose |
|---|---|
| `smoke` | End-to-end happy-path test covering the full project lifecycle |
| `regression` | Guard tests for previously fixed bugs |

Run only smoke tests:

```
pytest -m smoke
```

Run everything except smoke tests:

```
pytest -m "not smoke"
```

### Test layout

| File | Coverage |
|---|---|
| `tests/cli/test_top_level.py` | `version`, `doctor`, `--help` |
| `tests/cli/test_init_status_config.py` | `init`, `status`, `config show` |
| `tests/cli/test_chapter_note_scan_db.py` | `chapter new/list/delete/restore`, `note add-source/list`, `scan`, `db show` |
| `tests/cli/test_review_rewrite.py` | `review`, `rewrite` — paragraph-level accept/reject, artifacts, history |
| `tests/cli/test_publish.py` | `publish prepare`, `publish build` — checks, HTML output, image handling |
| `tests/cli/test_repl.py` | REPL entry, commands, `/open` mock, error paths |
| `tests/cli/test_smoke.py` | Full lifecycle smoke test |

---

## File Formats

### `altamira.yaml`

```yaml
name: My Memoir
version: 0.1.0
subject_type: person             # "person" | "event"
subject_name: Rosa Mendes        # name of the person or event being documented
language: en                     # BCP-47 language tag, applied to <html lang="...">
description: ""                  # optional one-line description shown in the sidebar
cover: materials/raw/cover.jpg   # optional; path relative to project root
require_source_notes: false      # set true to warn when no source notes exist
```

### Chapter `.meta.yaml`

```yaml
title: The Early Years
slug: chapter-01
order: 1
status: draft
summary: ""
prompt: Focus on sensory details from childhood.
```

### Note `.meta.yaml`

```yaml
title: Interview with Aunt Rosa
source_type: interview
url: ""
origin: Rosa Mendes, family friend
created_at: "2026-05-14T10:30:00"
tags:
  - family
  - 1970s
summary: Recollections of the house on Maple Street.
```
