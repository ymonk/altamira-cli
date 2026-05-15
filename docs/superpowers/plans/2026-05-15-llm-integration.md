# LLM Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three mock LLM stubs (reviewer, rewriter, REPL chat) with real provider calls that work against Anthropic and OpenAI.

**Architecture:** All LLM calls go through `get_provider()` in `services/provider.py`, which already handles both Anthropic and OpenAI via env vars. The reviewer and rewriter each get a real implementation function added alongside the existing mock; the command files swap their module-level `_reviewer`/`_rewriter` variable to point at the real function. The REPL restores its context builder and plain-text dispatch path.

**Tech Stack:** `anthropic` / `openai` SDK (already plumbed in `provider.py`), Python `json` stdlib for response parsing, `pytest` + `unittest.mock` for tests.

---

## File Map

| Action | Path | Why |
|--------|------|-----|
| Create | `src/altamira/skills/prompts/chapter_reviewer.md` | Prompt template for editorial review |
| Modify | `src/altamira/services/reviewer.py` | Add `llm_review` alongside `mock_review` |
| Modify | `src/altamira/cli/review_cmd.py` | Swap `_reviewer` to `llm_review` |
| Modify | `src/altamira/services/rewriter.py` | Add `llm_rewrite` alongside `mock_rewrite` |
| Modify | `src/altamira/cli/rewrite_cmd.py` | Swap `_rewriter` to `llm_rewrite` |
| Modify | `src/altamira/cli/repl.py` | Restore `_build_agent_context` + LLM dispatch |
| Create | `tests/services/__init__.py` | Make test directory a package |
| Create | `tests/services/test_llm_reviewer.py` | Tests for `llm_review` |
| Create | `tests/services/test_llm_rewriter.py` | Tests for `llm_rewrite` |
| Modify | `tests/cli/test_repl.py` | Update plain-text tests to mock provider |

---

## Task 1: Add the chapter reviewer skill prompt

**Files:**
- Create: `src/altamira/skills/prompts/chapter_reviewer.md`

This gives the review prompt a home in the skills directory (visible via `/skill list`) and keeps the actual prompt out of Python source.

- [ ] **Step 1: Create the skill prompt file**

```markdown
# Chapter Reviewer

Provides paragraph-level editorial feedback for a memoir or biography chapter.

## Prompt

You are a memoir editor. Review the chapter below and provide specific editorial
feedback for the body paragraphs that most need attention (up to 4 paragraphs).

Return your response as a JSON array. Each element must have exactly two keys:
- "paragraph_index": the 0-based index of the paragraph among body paragraphs
  (do not count heading lines starting with #)
- "comment": one or two sentences of specific, actionable editorial feedback

Return ONLY the JSON array — no preamble, no trailing notes, no markdown fences.

Example response:
[
  {"paragraph_index": 0, "comment": "The opening sentence buries the most vivid detail — lead with the image of the kitchen instead."},
  {"paragraph_index": 2, "comment": "This transition is abrupt; a single bridging sentence would help the reader follow the time jump."}
]

Chapter:
```

Save to `src/altamira/skills/prompts/chapter_reviewer.md`.

- [ ] **Step 2: Verify the skill appears in the list**

Run: `.venv/bin/python -c "from altamira.skills.loader import list_skills; print(list_skills())"`

Expected: output includes a tuple starting with `'chapter_reviewer'`.

- [ ] **Step 3: Commit**

```bash
git add src/altamira/skills/prompts/chapter_reviewer.md
git commit -m "feat: add chapter_reviewer skill prompt"
```

---

## Task 2: Implement `llm_review` and its tests

**Files:**
- Modify: `src/altamira/services/reviewer.py`
- Create: `tests/services/__init__.py`
- Create: `tests/services/test_llm_reviewer.py`

The real reviewer calls `get_provider()`, builds a prompt with the chapter text, parses the JSON response into `ParagraphComment` objects. Body paragraphs are those that don't start with `#` and are non-empty — the `paragraph_index` in the JSON refers to position in that filtered list.

- [ ] **Step 1: Write the failing tests**

Create `tests/services/__init__.py` (empty).

Create `tests/services/test_llm_reviewer.py`:

```python
import json
from unittest.mock import patch

import pytest


CHAPTER = """# The Early Years

My grandmother kept a garden behind the house, thick with mint and rosemary.

She never spoke about the war directly, but some evenings she would grow quiet.

We ate dinner late, the radio always on.

A photograph of her as a girl sat on the mantle, faded but unmistakable.
"""


def _make_provider(response: str):
    return lambda prompt: response


def test_llm_review_returns_paragraph_comments():
    mock_json = json.dumps([
        {"paragraph_index": 0, "comment": "Strong sensory opening."},
        {"paragraph_index": 2, "comment": "Pacing is too fast here."},
    ])
    with patch("altamira.services.reviewer.get_provider", return_value=_make_provider(mock_json)):
        from altamira.services.reviewer import llm_review
        comments = llm_review(CHAPTER)
    assert len(comments) == 2
    assert comments[0].paragraph_index == 0
    assert comments[0].comment == "Strong sensory opening."
    assert "grandmother" in comments[0].paragraph_text
    assert comments[1].paragraph_index == 2
    assert "radio" in comments[1].paragraph_text


def test_llm_review_includes_correct_paragraph_text():
    mock_json = json.dumps([{"paragraph_index": 1, "comment": "Good restraint."}])
    with patch("altamira.services.reviewer.get_provider", return_value=_make_provider(mock_json)):
        from altamira.services.reviewer import llm_review
        comments = llm_review(CHAPTER)
    assert "war" in comments[0].paragraph_text


def test_llm_review_ignores_out_of_range_indices():
    mock_json = json.dumps([
        {"paragraph_index": 99, "comment": "This index does not exist."},
        {"paragraph_index": 0, "comment": "Valid comment."},
    ])
    with patch("altamira.services.reviewer.get_provider", return_value=_make_provider(mock_json)):
        from altamira.services.reviewer import llm_review
        comments = llm_review(CHAPTER)
    assert len(comments) == 1
    assert comments[0].paragraph_index == 0


def test_llm_review_returns_empty_on_bad_json():
    with patch("altamira.services.reviewer.get_provider", return_value=_make_provider("not json")):
        from altamira.services.reviewer import llm_review
        comments = llm_review(CHAPTER)
    assert comments == []
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `.venv/bin/pytest tests/services/test_llm_reviewer.py -v`

Expected: `ImportError` or `AttributeError` — `llm_review` does not exist yet.

- [ ] **Step 3: Implement `llm_review` in `reviewer.py`**

Add to `src/altamira/services/reviewer.py` (keep `mock_review` in place):

```python
import json
from altamira.services.provider import get_provider
from altamira.skills.loader import load_skill


def llm_review(text: str) -> list[ParagraphComment]:
    """Call the active LLM provider and parse paragraph comments from the response."""
    body_paras = [
        p for p in text.split("\n\n")
        if p.strip() and not p.lstrip().startswith("#")
    ]

    skill_prompt = load_skill("chapter_reviewer") or ""
    # Append the chapter after the skill prompt's trailing newline
    prompt = f"{skill_prompt.strip()}\n\n{text}"

    try:
        provider = get_provider()
        raw = provider(prompt)
    except Exception:
        return []

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return []

    comments = []
    for item in data:
        idx = item.get("paragraph_index")
        comment = item.get("comment", "")
        if not isinstance(idx, int) or idx < 0 or idx >= len(body_paras):
            continue
        comments.append(ParagraphComment(
            paragraph_index=idx,
            paragraph_text=body_paras[idx],
            comment=comment,
        ))
    return comments
```

The full updated `reviewer.py` (complete file — replace entirely):

```python
import json
from dataclasses import dataclass
from typing import Callable

from altamira.services.provider import get_provider
from altamira.skills.loader import load_skill


@dataclass
class ParagraphComment:
    paragraph_index: int
    paragraph_text: str
    comment: str


ReviewFn = Callable[[str], list[ParagraphComment]]

_MOCK_COMMENTS = [
    "Consider adding more sensory detail to ground the reader in this moment.",
    "This transition feels abrupt — try bridging it to the previous idea.",
    "Strong passage. The pacing here could be slowed to let the scene breathe.",
    "The voice shifts slightly. Consider aligning the tone with the opening.",
]


def mock_review(text: str) -> list[ParagraphComment]:
    """Return mocked paragraph-level comments. Replace with an LLM call to go live."""
    body_paras = [
        (i, p)
        for i, p in enumerate(text.split("\n\n"))
        if p.strip() and not p.lstrip().startswith("#")
    ]
    return [
        ParagraphComment(
            paragraph_index=idx,
            paragraph_text=para,
            comment=_MOCK_COMMENTS[n % len(_MOCK_COMMENTS)],
        )
        for n, (idx, para) in enumerate(body_paras[:4])
    ]


def llm_review(text: str) -> list[ParagraphComment]:
    """Call the active LLM provider and parse paragraph comments from the response."""
    body_paras = [
        p for p in text.split("\n\n")
        if p.strip() and not p.lstrip().startswith("#")
    ]

    skill_prompt = load_skill("chapter_reviewer") or ""
    prompt = f"{skill_prompt.strip()}\n\n{text}"

    try:
        provider = get_provider()
        raw = provider(prompt)
    except Exception:
        return []

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return []

    comments = []
    for item in data:
        idx = item.get("paragraph_index")
        comment = item.get("comment", "")
        if not isinstance(idx, int) or idx < 0 or idx >= len(body_paras):
            continue
        comments.append(ParagraphComment(
            paragraph_index=idx,
            paragraph_text=body_paras[idx],
            comment=comment,
        ))
    return comments
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `.venv/bin/pytest tests/services/test_llm_reviewer.py -v`

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/altamira/services/reviewer.py tests/services/__init__.py tests/services/test_llm_reviewer.py
git commit -m "feat: implement llm_review with JSON response parsing"
```

---

## Task 3: Wire `llm_review` into `review_cmd.py`

**Files:**
- Modify: `src/altamira/cli/review_cmd.py`

One-line change — swap the module-level variable.

- [ ] **Step 1: Update the import and reviewer assignment**

In `src/altamira/cli/review_cmd.py`, replace:

```python
from altamira.services.reviewer import ParagraphComment, ReviewFn, mock_review

# Swap this to point at a real LLM reviewer without changing the command.
_reviewer: ReviewFn = mock_review
```

With:

```python
from altamira.services.reviewer import ParagraphComment, ReviewFn, llm_review

_reviewer: ReviewFn = llm_review
```

- [ ] **Step 2: Run the existing review tests to confirm nothing broke**

Run: `.venv/bin/pytest tests/cli/test_review_rewrite.py -v`

Expected: all tests pass (they mock `_reviewer` directly, so the swap is invisible to them).

- [ ] **Step 3: Commit**

```bash
git add src/altamira/cli/review_cmd.py
git commit -m "feat: wire llm_review into review command"
```

---

## Task 4: Implement `llm_rewrite` and its tests

**Files:**
- Modify: `src/altamira/services/rewriter.py`
- Create: `tests/services/test_llm_rewriter.py`

The rewriter gets a simpler prompt: return only the rewritten text. The `rewrite_cmd.py` diffs it against the original paragraph-by-paragraph — so the LLM just needs to return valid chapter text, not structured data.

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_llm_rewriter.py`:

```python
from unittest.mock import patch


CHAPTER = """# The Early Years

My grandmother kept a garden behind the house, thick with mint and rosemary.

She never spoke about the war directly, but some evenings she would grow quiet.
"""

REWRITTEN = """# The Early Years

My grandmother tended a garden behind the house — mint, rosemary, the smell of both.

She rarely spoke about the war, but on certain evenings a stillness would settle over her.
"""


def _make_provider(response: str):
    return lambda prompt: response


def test_llm_rewrite_returns_string():
    with patch("altamira.services.rewriter.get_provider", return_value=_make_provider(REWRITTEN)):
        from altamira.services.rewriter import llm_rewrite
        result = llm_rewrite(CHAPTER)
    assert isinstance(result, str)
    assert len(result) > 0


def test_llm_rewrite_returns_provider_response():
    with patch("altamira.services.rewriter.get_provider", return_value=_make_provider(REWRITTEN)):
        from altamira.services.rewriter import llm_rewrite
        result = llm_rewrite(CHAPTER)
    assert result == REWRITTEN


def test_llm_rewrite_falls_back_to_original_on_error():
    def bad_provider(prompt):
        raise RuntimeError("API error")

    with patch("altamira.services.rewriter.get_provider", return_value=bad_provider):
        from altamira.services.rewriter import llm_rewrite
        result = llm_rewrite(CHAPTER)
    assert result == CHAPTER
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `.venv/bin/pytest tests/services/test_llm_rewriter.py -v`

Expected: `ImportError` or `AttributeError` — `llm_rewrite` does not exist yet.

- [ ] **Step 3: Implement `llm_rewrite` in `rewriter.py`**

The full updated `rewriter.py` (complete file — replace entirely):

```python
from typing import Callable

from altamira.services.provider import get_provider

RewriteFn = Callable[[str], str]

_SUBSTITUTIONS = [
    ("very ",         "quite "),
    (" born ",        " raised "),
    ("long hours",    "extended hours"),
    ("small ",        "modest "),
    (" worked ",      " labored "),
    ("only child",    "sole child"),
    ("lively",        "vibrant"),
    ("tired",         "weary"),
    ("memorized",     "committed to memory"),
    ("stories",       "narratives"),
    ("big ",          "considerable "),
    ("grew up",       "came of age"),
]

_REWRITE_PROMPT = """\
You are a memoir editor. Rewrite the chapter below to improve clarity, pacing, \
and voice consistency.

Rules:
- Preserve all factual details and the author's voice exactly
- Tighten sentences that are overlong or passive
- Improve paragraph transitions so the narrative flows naturally
- Do NOT add invented details, dialogue, or scenes
- Return ONLY the rewritten chapter text — no commentary, no revision notes

Chapter:
"""


def mock_rewrite(text: str) -> str:
    """Apply simple substitutions to body paragraphs. Replace with an LLM call to go live."""
    paragraphs = text.split("\n\n")
    result = []
    for para in paragraphs:
        if para.strip() and not para.lstrip().startswith("#"):
            changed = False
            for old, new in _SUBSTITUTIONS:
                if old in para:
                    para = para.replace(old, new, 1)
                    changed = True
                    break
            if not changed:
                para = para.rstrip() + " The memory of this period remains clear."
        result.append(para)
    return "\n\n".join(result)


def llm_rewrite(text: str) -> str:
    """Call the active LLM provider and return the rewritten chapter text."""
    try:
        provider = get_provider()
        return provider(_REWRITE_PROMPT + text)
    except Exception:
        return text
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `.venv/bin/pytest tests/services/test_llm_rewriter.py -v`

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/altamira/services/rewriter.py tests/services/test_llm_rewriter.py
git commit -m "feat: implement llm_rewrite with provider fallback"
```

---

## Task 5: Wire `llm_rewrite` into `rewrite_cmd.py`

**Files:**
- Modify: `src/altamira/cli/rewrite_cmd.py`

One-line change.

- [ ] **Step 1: Update the import and rewriter assignment**

In `src/altamira/cli/rewrite_cmd.py`, replace:

```python
from altamira.services.rewriter import RewriteFn, mock_rewrite

# Swap to point at a real LLM rewriter without changing the command.
_rewriter: RewriteFn = mock_rewrite
```

With:

```python
from altamira.services.rewriter import RewriteFn, llm_rewrite

_rewriter: RewriteFn = llm_rewrite
```

- [ ] **Step 2: Run the existing rewrite tests to confirm nothing broke**

Run: `.venv/bin/pytest tests/cli/test_review_rewrite.py -v`

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add src/altamira/cli/rewrite_cmd.py
git commit -m "feat: wire llm_rewrite into rewrite command"
```

---

## Task 6: Restore REPL/exec LLM dispatch

**Files:**
- Modify: `src/altamira/cli/repl.py`
- Modify: `tests/cli/test_repl.py`

We removed the LLM dispatch in a prior commit. Now we restore it, with the same structure: build a project context string, prepend it to the user's prompt, call the provider. The REPL loop also gets a real dispatch instead of the "not configured" message.

- [ ] **Step 1: Update the failing tests first**

In `tests/cli/test_repl.py`, replace the two "not configured" tests:

```python
# Replace this test:
def test_repl_non_slash_input_shows_not_configured(initialized_project, capsys):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["hello world", "/exit"]):
        run_repl(initialized_project)
    captured = capsys.readouterr()
    assert "AI model hasn't been configured" in captured.out

# With this test:
def test_repl_non_slash_input_calls_provider(initialized_project, capsys):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["hello world", "/exit"]):
        with patch("altamira.cli.repl.get_provider", return_value=lambda p: "Mocked response"):
            run_repl(initialized_project)
    captured = capsys.readouterr()
    assert "Mocked response" in captured.out
```

```python
# Replace this test:
def test_exec_plain_prompt_shows_not_configured(initialized_project, capsys):
    from altamira.cli.repl import run_single_instruction
    code = run_single_instruction("summarize the book", initialized_project)
    assert code == 1
    captured = capsys.readouterr()
    assert "AI model hasn't been configured" in captured.out

# With this test:
def test_exec_plain_prompt_calls_provider(initialized_project, capsys):
    from altamira.cli.repl import run_single_instruction
    with patch("altamira.cli.repl.get_provider", return_value=lambda p: "Mocked LLM reply"):
        code = run_single_instruction("summarize the book", initialized_project)
    assert code == 0
    captured = capsys.readouterr()
    assert "Mocked LLM reply" in captured.out
```

```python
# Replace this test:
def test_exec_via_cli_plain_prompt(cli_runner, initialized_project):
    result = cli_runner.invoke(app, ["-e", "tell me about this project"])
    assert result.exit_code == 1
    assert "AI model hasn't been configured" in result.output

# With this test:
def test_exec_via_cli_plain_prompt(cli_runner, initialized_project):
    with patch("altamira.cli.repl.get_provider", return_value=lambda p: "CLI LLM reply"):
        result = cli_runner.invoke(app, ["-e", "tell me about this project"])
    assert result.exit_code == 0
    assert "CLI LLM reply" in result.output
```

Also add the import at the top of the test file (it should already be there from `unittest.mock`; confirm `patch` is imported).

- [ ] **Step 2: Run the updated tests to confirm they fail**

Run: `.venv/bin/pytest tests/cli/test_repl.py::test_repl_non_slash_input_calls_provider tests/cli/test_repl.py::test_exec_plain_prompt_calls_provider tests/cli/test_repl.py::test_exec_via_cli_plain_prompt -v`

Expected: all three FAIL — `get_provider` is not imported in `repl.py` yet.

- [ ] **Step 3: Restore the LLM dispatch in `repl.py`**

Add the import near the top of `repl.py` (after the existing imports):

```python
from altamira.services.provider import get_provider
```

Add `_build_agent_context` back before `run_single_instruction`:

```python
def _build_agent_context(cwd: Path) -> str:
    parts: list[str] = []
    try:
        config = load_config(cwd)
        parts.append(f"Project: {config.name}")
        if config.subject_name:
            parts.append(f"Subject: {config.subject_name}")
        parts.append("")
    except Exception:
        pass

    chapters = list_chapters(cwd / "chapters")
    for ch in chapters:
        chapter_dir = cwd / "chapters" / f"chapter-{ch.order:02d}"
        md_path = chapter_dir / f"chapter-{ch.order:02d}.md"
        parts.append(f"--- Chapter {ch.order}: {ch.title} ---")
        parts.append(md_path.read_text(encoding="utf-8").strip() if md_path.exists() else f"[status: {ch.status}]")
        parts.append("")
    return "\n".join(parts)
```

In `run_single_instruction`, replace the stub:

```python
    # Plain-English prompt — AI not yet configured.
    console.print("[yellow]AI model hasn't been configured yet.[/yellow]  Use a /command instead, or configure a provider via ALTAMIRA_PROVIDER.")
    return 1
```

With:

```python
    # Plain-English prompt — dispatch to LLM provider with project context.
    if not _is_project(cwd):
        console.print("[yellow]Warning:[/yellow] Not in an Altamira project. Running without project context.")

    try:
        provider = get_provider()
    except (EnvironmentError, ImportError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        return 1

    context = _build_agent_context(cwd) if _is_project(cwd) else ""
    prompt = f"{context}\n{instruction}" if context.strip() else instruction

    try:
        result = provider(prompt)
    except Exception as e:
        console.print(f"[red]Provider error:[/red] {e}")
        return 1

    console.print(result)
    return 0
```

In `run_repl`, replace the stub for non-command input:

```python
        if not raw.startswith("/"):
            console.print("[yellow]AI model hasn't been configured yet.[/yellow]  Commands start with [bold]/[/bold]  — try /commands")
            continue
```

With:

```python
        if not raw.startswith("/"):
            try:
                provider = get_provider()
            except (EnvironmentError, ImportError, ValueError) as e:
                console.print(f"[red]Error:[/red] {e}")
                continue
            context = _build_agent_context(cwd) if _is_project(cwd) else ""
            prompt = f"{context}\n{raw}" if context.strip() else raw
            try:
                console.print(provider(prompt))
            except Exception as e:
                console.print(f"[red]Provider error:[/red] {e}")
            continue
```

- [ ] **Step 4: Run all REPL tests to confirm they pass**

Run: `.venv/bin/pytest tests/cli/test_repl.py -v`

Expected: all 24 tests pass.

- [ ] **Step 5: Run the full test suite**

Run: `.venv/bin/pytest -m "not smoke" -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/altamira/cli/repl.py tests/cli/test_repl.py
git commit -m "feat: restore LLM dispatch in REPL and -e mode"
```

---

## Done

After Task 6, all three LLM paths are live:

| Path | Trigger | Provider call |
|------|---------|---------------|
| `altamira review <n>` | paragraph review | `llm_review()` → structured JSON |
| `altamira rewrite <n>` | paragraph rewrite | `llm_rewrite()` → raw text |
| REPL free-text / `-e` | open-ended chat | `get_provider()` → raw text |

To use, export your API key and run:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
altamira -e "What themes are emerging across my chapters?"
```
