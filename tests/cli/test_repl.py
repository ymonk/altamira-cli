from pathlib import Path
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


def test_repl_non_slash_input_shows_not_configured(initialized_project, capsys):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["hello world", "/exit"]):
        run_repl(initialized_project)
    captured = capsys.readouterr()
    assert "AI model hasn't been configured" in captured.out


def test_repl_empty_input_ignored(initialized_project):
    from altamira.cli.repl import run_repl
    with patch("altamira.cli.repl.pt_prompt", side_effect=["", "   ", "/exit"]):
        run_repl(initialized_project)


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


def test_exec_plain_prompt_shows_not_configured(initialized_project, capsys):
    from altamira.cli.repl import run_single_instruction
    code = run_single_instruction("summarize the book", initialized_project)
    assert code == 1
    captured = capsys.readouterr()
    assert "AI model hasn't been configured" in captured.out


def test_exec_via_cli_plain_prompt(cli_runner, initialized_project):
    result = cli_runner.invoke(app, ["-e", "tell me about this project"])
    assert result.exit_code == 1
    assert "AI model hasn't been configured" in result.output
