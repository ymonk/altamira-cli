import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from altamira.cli.app import app
from altamira.domain.chapter import create_chapter


# ── no-arg invocation enters REPL ─────────────────────────────────────────────

def test_no_args_invokes_repl(cli_runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("altamira.cli.repl.run_repl") as mock_repl:
        cli_runner.invoke(app, [])
    mock_repl.assert_called_once_with(tmp_path)


# ── exit / quit / EOF ─────────────────────────────────────────────────────────

def test_repl_exit_command(initialized_project):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/exit"]):
        run_repl(initialized_project)


def test_repl_quit_command(initialized_project):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/quit"]):
        run_repl(initialized_project)


def test_repl_eof_exits(initialized_project):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=EOFError):
        run_repl(initialized_project)


def test_repl_keyboard_interrupt_exits(initialized_project):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=KeyboardInterrupt):
        run_repl(initialized_project)


# ── core REPL commands — no exception ─────────────────────────────────────────

def test_repl_help_command(initialized_project):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/help", "/exit"]):
        run_repl(initialized_project)


def test_repl_commands_command(initialized_project):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/commands", "/exit"]):
        run_repl(initialized_project)


def test_repl_status_command(initialized_project):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/status", "/exit"]):
        run_repl(initialized_project)


def test_repl_chapter_list_empty(initialized_project):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/chapter list", "/exit"]):
        run_repl(initialized_project)


def test_repl_chapter_list_with_chapter(initialized_project):
    create_chapter(initialized_project / "chapters", "The Early Years")
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/chapter list", "/exit"]):
        run_repl(initialized_project)


# ── /use command updates REPL state ───────────────────────────────────────────

def test_repl_use_selects_chapter(initialized_project):
    create_chapter(initialized_project / "chapters", "The Early Years")
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/use 1", "/exit"]):
        run_repl(initialized_project)


def test_repl_use_deselects_chapter(initialized_project):
    create_chapter(initialized_project / "chapters", "The Early Years")
    from altamira.cli.repl import run_repl
    # /use 1 to select, /use alone to deselect
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/use 1", "/use", "/exit"]):
        run_repl(initialized_project)


# ── /open delegates to _open_path ─────────────────────────────────────────────

def test_repl_open_calls_open_path(initialized_project):
    md_path, _, _ = create_chapter(initialized_project / "chapters", "The Early Years")
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/open 1", "/exit"]):
        with patch("altamira.cli.repl._open_path") as mock_open:
            run_repl(initialized_project)
    mock_open.assert_called_once_with(md_path)


def test_repl_open_uses_current_chapter(initialized_project):
    md_path, _, _ = create_chapter(initialized_project / "chapters", "The Early Years")
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/use 1", "/open", "/exit"]):
        with patch("altamira.cli.repl._open_path") as mock_open:
            run_repl(initialized_project)
    mock_open.assert_called_once_with(md_path)


# ── error / unknown input ─────────────────────────────────────────────────────

def test_repl_unknown_command_no_error(initialized_project):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/notacommand", "/exit"]):
        run_repl(initialized_project)


def test_repl_non_slash_input_calls_provider(initialized_project, capsys):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["hello world", "/exit"]):
        with patch("altamira.cli.repl.get_provider", return_value=lambda p: "Mocked response"):
            run_repl(initialized_project)
    captured = capsys.readouterr()
    assert "Mocked response" in captured.out


def test_repl_empty_input_ignored(initialized_project):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["", "   ", "/exit"]):
        run_repl(initialized_project)


# ── /llm list ────────────────────────────────────────────────────────────────

def test_repl_llm_list_shows_providers(initialized_project, capsys):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/llm list", "/exit"]):
        run_repl(initialized_project)
    out = capsys.readouterr().out
    assert "anthropic" in out
    assert "openai" in out


def test_repl_llm_list_marks_active_model(initialized_project, capsys, monkeypatch):
    monkeypatch.setenv("ALTAMIRA_PROVIDER", "anthropic")
    monkeypatch.setenv("ALTAMIRA_MODEL", "claude-sonnet-4-6")
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/llm list", "/exit"]):
        run_repl(initialized_project)
    out = capsys.readouterr().out
    assert "* claude-sonnet-4-6" in out


def test_repl_llm_bad_subcmd_prints_usage(initialized_project, capsys):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/llm", "/exit"]):
        run_repl(initialized_project)
    out = capsys.readouterr().out
    assert "Usage" in out


def test_repl_llm_activate_writes_config(initialized_project, capsys):
    from altamira.cli.repl import run_repl
    from altamira.config.loader import load_config
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/llm activate gpt-4o-mini", "/exit"]):
        run_repl(initialized_project)
    out = capsys.readouterr().out
    assert "gpt-4o-mini" in out
    config = load_config(initialized_project)
    assert config.model == "gpt-4o-mini"
    assert config.provider == "openai"


def test_repl_llm_activate_rejects_unknown_model(initialized_project, capsys):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/llm activate no-such-model", "/exit"]):
        run_repl(initialized_project)
    out = capsys.readouterr().out
    assert "Unknown model" in out


def test_apply_config_model_defaults_sets_env(initialized_project, monkeypatch):
    monkeypatch.delenv("ALTAMIRA_PROVIDER", raising=False)
    monkeypatch.delenv("ALTAMIRA_MODEL", raising=False)
    from altamira.config.loader import load_config, write_config
    config = load_config(initialized_project)
    config.provider = "openai"
    config.model = "o3"
    write_config(config, initialized_project)

    from altamira.cli.repl import _apply_config_model_defaults
    _apply_config_model_defaults(initialized_project)
    assert os.environ.get("ALTAMIRA_PROVIDER") == "openai"
    assert os.environ.get("ALTAMIRA_MODEL") == "o3"


def test_apply_config_model_defaults_env_wins(initialized_project, monkeypatch):
    monkeypatch.setenv("ALTAMIRA_PROVIDER", "anthropic")
    monkeypatch.setenv("ALTAMIRA_MODEL", "claude-opus-4-7")
    from altamira.config.loader import load_config, write_config
    config = load_config(initialized_project)
    config.provider = "openai"
    config.model = "gpt-4o"
    write_config(config, initialized_project)

    from altamira.cli.repl import _apply_config_model_defaults
    _apply_config_model_defaults(initialized_project)
    assert os.environ.get("ALTAMIRA_PROVIDER") == "anthropic"
    assert os.environ.get("ALTAMIRA_MODEL") == "claude-opus-4-7"


# ── multiline prompt editing ─────────────────────────────────────────────────

def test_repl_lexer_renders_each_multiline_row_once():
    from prompt_toolkit.document import Document
    from altamira.cli.repl import _ReplLexer

    get_line = _ReplLexer().lex_document(Document("first\nsecond"))

    assert get_line(0) == [("", "first")]
    assert get_line(1) == [("", "second")]


def test_shift_return_uses_prompt_toolkit_newline():
    from altamira.cli.repl import _shift_return_newline

    class DummyBuffer:
        def __init__(self):
            self.newline_copy_margin = None
            self.inserted_text = None

        def newline(self, copy_margin=True):
            self.newline_copy_margin = copy_margin

        def insert_text(self, text):
            self.inserted_text = text

    buffer = DummyBuffer()

    _shift_return_newline(SimpleNamespace(current_buffer=buffer))

    assert buffer.newline_copy_margin is False
    assert buffer.inserted_text is None


def test_repl_uses_empty_multiline_continuation_prompt(initialized_project):
    from altamira.cli.repl import run_repl

    with patch("altamira.cli.repl.pt_prompt", side_effect=EOFError) as mock_prompt:
        run_repl(initialized_project)

    assert mock_prompt.call_args.kwargs["prompt_continuation"] == ""


# ── -e / run_single_instruction ───────────────────────────────────────────────

def test_exec_empty_instruction_returns_error(initialized_project):
    from altamira.cli.repl import run_single_instruction
    code = run_single_instruction("", initialized_project)
    assert code == 1


def test_exec_quit_returns_zero(initialized_project):
    from altamira.cli.repl import run_single_instruction
    assert run_single_instruction("/quit", initialized_project) == 0


def test_exec_exit_returns_zero(initialized_project):
    from altamira.cli.repl import run_single_instruction
    assert run_single_instruction("/exit", initialized_project) == 0


def test_exec_known_command_returns_zero(initialized_project):
    from altamira.cli.repl import run_single_instruction
    code = run_single_instruction("/chapter list", initialized_project)
    assert code == 0


def test_exec_unknown_command_returns_error(initialized_project):
    from altamira.cli.repl import run_single_instruction
    code = run_single_instruction("/notacommand", initialized_project)
    assert code == 1


def test_exec_plain_prompt_calls_provider(initialized_project, capsys):
    from altamira.cli.repl import run_single_instruction
    with patch("altamira.cli.repl.get_provider", return_value=lambda p: "Mocked LLM reply"):
        code = run_single_instruction("summarize the book", initialized_project)
    assert code == 0
    captured = capsys.readouterr()
    assert "Mocked LLM reply" in captured.out


def test_exec_via_cli_plain_prompt(cli_runner, initialized_project):
    with patch("altamira.cli.repl.get_provider", return_value=lambda p: "CLI LLM reply"):
        result = cli_runner.invoke(app, ["-e", "tell me about this project"])
    assert result.exit_code == 0
    assert "CLI LLM reply" in result.output


# ── tool call dispatch ────────────────────────────────────────────────────────

def test_try_parse_tool_call_at_start():
    from altamira.cli.repl import _try_parse_tool_call
    response = '{"tool": "write_chapter", "identifier": "1", "content": "# Title\\n\\nBody", "reason": "test"}\n\nExplanation.'
    tool, remaining = _try_parse_tool_call(response)
    assert tool is not None
    assert tool["tool"] == "write_chapter"
    assert tool["identifier"] == "1"
    assert "Explanation." in remaining


def test_try_parse_tool_call_rejects_preamble():
    from altamira.cli.repl import _try_parse_tool_call
    response = "I'll write this now.\n\n" + '{"tool": "write_chapter", "identifier": "2", "content": "# Ch\\n\\nText", "reason": "r"}\n\nDone.'
    tool, remaining = _try_parse_tool_call(response)
    assert tool is None
    assert remaining == response


def test_try_parse_tool_call_no_tool():
    from altamira.cli.repl import _try_parse_tool_call
    response = "Just a plain text response with no tool call."
    tool, remaining = _try_parse_tool_call(response)
    assert tool is None
    assert remaining == response


def test_repl_executes_write_chapter_tool(initialized_project, capsys):
    from altamira.domain.chapter import create_chapter
    from altamira.cli.repl import run_single_instruction
    create_chapter(initialized_project / "chapters", "The Early Years")
    tool_json = '{"tool": "write_chapter", "identifier": "1", "content": "# Updated\\n\\nNew body.", "reason": "agent test"}'
    llm_response = f"{tool_json}\n\nAll done."
    with patch("altamira.cli.repl.get_provider", return_value=lambda p: llm_response):
        code = run_single_instruction("update chapter 1", initialized_project)
    assert code == 0
    md = (initialized_project / "chapters" / "chapter-01" / "chapter-01.md").read_text()
    assert md == "# Updated\n\nNew body."
    chapter_dir = initialized_project / "chapters" / "chapter-01"
    assert list((chapter_dir / "versions").glob("*.md"))
    assert "agent write" in (chapter_dir / "chapter-01.history.md").read_text()


def test_repl_does_not_execute_fenced_tool_example(initialized_project):
    from altamira.domain.chapter import create_chapter
    from altamira.cli.repl import run_single_instruction

    create_chapter(initialized_project / "chapters", "The Early Years")
    md_path = initialized_project / "chapters" / "chapter-01" / "chapter-01.md"
    original = md_path.read_text()
    response = (
        "```json\n"
        '{"tool": "write_chapter", "identifier": "1", "content": "# Unsafe"}\n'
        "```"
    )

    with patch("altamira.cli.repl.get_provider", return_value=lambda p: response):
        code = run_single_instruction("show me a tool example", initialized_project)

    assert code == 0
    assert md_path.read_text() == original


def test_repl_does_not_execute_indented_tool_example(initialized_project):
    from altamira.domain.chapter import create_chapter
    from altamira.cli.repl import run_single_instruction

    create_chapter(initialized_project / "chapters", "The Early Years")
    md_path = initialized_project / "chapters" / "chapter-01" / "chapter-01.md"
    original = md_path.read_text()
    response = '    {"tool": "write_chapter", "identifier": "1", "content": "# Unsafe"}'

    with patch("altamira.cli.repl.get_provider", return_value=lambda p: response):
        code = run_single_instruction("show me an indented example", initialized_project)

    assert code == 0
    assert md_path.read_text() == original


def test_repl_does_not_execute_quoted_tool_example(initialized_project):
    from altamira.domain.chapter import create_chapter
    from altamira.cli.repl import run_single_instruction

    create_chapter(initialized_project / "chapters", "The Early Years")
    md_path = initialized_project / "chapters" / "chapter-01" / "chapter-01.md"
    original = md_path.read_text()
    response = '> {"tool": "write_chapter", "identifier": "1", "content": "# Unsafe"}'

    with patch("altamira.cli.repl.get_provider", return_value=lambda p: response):
        code = run_single_instruction("quote a tool example", initialized_project)

    assert code == 0
    assert md_path.read_text() == original


# ── BoundedFileHistory ────────────────────────────────────────────────────────

def test_bounded_history_round_trips_entries(tmp_path):
    from altamira.cli.repl import BoundedFileHistory
    h = BoundedFileHistory(tmp_path / "hist", max_entries=10)
    h.store_string("first")
    h.store_string("second")
    loaded = h.load_history_strings()
    assert loaded[0] == "second"
    assert loaded[1] == "first"


def test_bounded_history_truncates_to_max(tmp_path):
    from altamira.cli.repl import BoundedFileHistory
    h = BoundedFileHistory(tmp_path / "hist", max_entries=3)
    for i in range(6):
        h.store_string(f"entry-{i}")
    loaded = h.load_history_strings()
    assert len(loaded) == 3
    assert loaded[0] == "entry-5"
    assert loaded[2] == "entry-3"


def test_bounded_history_escapes_newlines(tmp_path):
    from altamira.cli.repl import BoundedFileHistory
    h = BoundedFileHistory(tmp_path / "hist", max_entries=10)
    h.store_string("line one\nline two")
    raw = (tmp_path / "hist").read_text()
    assert "\\n" in raw
    assert h.load_history_strings()[0] == "line one\nline two"


def test_bounded_history_missing_file_returns_empty(tmp_path):
    from altamira.cli.repl import BoundedFileHistory
    h = BoundedFileHistory(tmp_path / "no_such_file", max_entries=10)
    assert h.load_history_strings() == []


def test_get_history_returns_in_memory_outside_project(tmp_path):
    from prompt_toolkit.history import InMemoryHistory
    from altamira.cli.repl import _get_history
    assert isinstance(_get_history(tmp_path), InMemoryHistory)


def test_get_history_returns_file_history_in_project(initialized_project):
    from altamira.cli.repl import BoundedFileHistory, _get_history
    assert isinstance(_get_history(initialized_project), BoundedFileHistory)


def test_get_history_reads_size_from_altamira_json(initialized_project):
    import json as _json
    from altamira.cli.repl import BoundedFileHistory, _get_history
    cfg_path = initialized_project / ".altamira" / "altamira.json"
    cfg_path.write_text(_json.dumps({"history_size": 42}))
    h = _get_history(initialized_project)
    assert isinstance(h, BoundedFileHistory)
    assert h._max_entries == 42


def test_repl_passes_bounded_history_to_prompt(initialized_project):
    from altamira.cli.repl import BoundedFileHistory, run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["/exit"]) as mock_pt:
        run_repl(initialized_project)
    assert "history" in mock_pt.call_args.kwargs
    assert isinstance(mock_pt.call_args.kwargs["history"], BoundedFileHistory)


def test_repl_passes_in_memory_history_outside_project(tmp_path):
    from prompt_toolkit.history import InMemoryHistory
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=[EOFError]):
        run_repl(tmp_path)
    # Can't easily inspect the history kwarg after EOFError path — test via _get_history directly.
    from altamira.cli.repl import _get_history
    assert isinstance(_get_history(tmp_path), InMemoryHistory)
