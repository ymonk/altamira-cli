import os
import platform
import subprocess
from pathlib import Path

import typer
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style

from altamira import __version__
from altamira.cli.console import console, kv
from altamira.cli.review_cmd import review
from altamira.cli.rewrite_cmd import rewrite
from altamira.config.loader import load_config
from altamira.domain.chapter import create_chapter, find_chapter, list_chapters, trash_chapter
from altamira.domain.note import create_note, list_notes
from altamira.infra.db import ensure_tables
from altamira.infra.scanner import scan_project
from altamira.services.provider import get_provider
from altamira.skills.loader import list_skills

_CMD_COLOR = "#7C9FCE"

_CMD_DESCRIPTIONS: dict[str, str] = {
    "cat":      "print chapter markdown to stdout",
    "chapter":  "manage chapters  (list · new · delete)",
    "clear":    "clear the screen",
    "commands": "quick command list",
    "config":   "show project configuration  (show)",
    "exit":     "exit the REPL",
    "help":     "list all commands with descriptions",
    "history":  "show commands entered this session",
    "note":     "manage source notes  (list · add)",
    "open":     "open chapter in system editor",
    "publish":  "check project readiness  (prepare)",
    "quit":     "exit the REPL",
    "review":   "review chapter paragraph by paragraph",
    "rewrite":  "rewrite chapter paragraph by paragraph",
    "scan":     "update the file index",
    "skill":    "list available prompt skills  (list)",
    "status":   "show project name, subject, chapter count",
    "use":      "select or deselect current chapter",
}

_SUBCMD_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "chapter": {
        "list":   "list all chapters",
        "new":    "create a new chapter",
        "delete": "move chapter to trash",
    },
    "note": {
        "list": "list source notes",
        "add":  "create a source note",
    },
    "config": {
        "show": "show all altamira.yaml fields",
    },
    "skill": {
        "list": "list available prompt skills",
    },
    "publish": {
        "prepare": "check project readiness",
    },
}

_SUBCOMMANDS: dict[str, set[str]] = {
    cmd: set(subcmds.keys()) for cmd, subcmds in _SUBCMD_DESCRIPTIONS.items()
}

_REPL_STYLE = Style.from_dict({
    "completion-menu.completion":              "fg:#666688",
    "completion-menu.completion.current":      f"fg:{_CMD_COLOR}",
    "completion-menu.meta.completion":         "fg:#444466",
    "completion-menu.meta.completion.current": f"fg:{_CMD_COLOR}",
})


class _ReplLexer(Lexer):
    def lex_document(self, document):
        style = f"fg:{_CMD_COLOR}" if self._is_valid(document.text) else ""

        def get_line(lineno):
            return [(style, document.text)]

        return get_line

    @staticmethod
    def _is_valid(text: str) -> bool:
        if not text.startswith("/"):
            return False
        after = text[1:]
        if not after or after[0] == " ":
            return False
        space_idx = after.find(" ")
        if space_idx == -1:
            return after.lower() in (set(_DISPATCH) | {"quit", "exit"})
        cmd = after[:space_idx].lower()
        if cmd not in (set(_DISPATCH) | {"quit", "exit"}):
            return False
        if cmd not in _SUBCOMMANDS:
            return True  # free-form arg (e.g. /review 1, /open 2, /use 3)
        subcmd_text = after[space_idx + 1:]
        if not subcmd_text:
            return False
        subcmd = subcmd_text.split()[0].lower() if subcmd_text.split() else ""
        return subcmd in _SUBCOMMANDS[cmd]


class _ReplCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        after = text[1:]
        space_idx = after.find(" ")
        if space_idx == -1:
            partial = after.lower()
            for cmd, desc in sorted(_CMD_DESCRIPTIONS.items()):
                if cmd.startswith(partial):
                    yield Completion("/" + cmd, start_position=-len(text), display_meta=desc)
        else:
            cmd = after[:space_idx].lower()
            subcmd_partial = after[space_idx + 1:]
            subcmds = _SUBCMD_DESCRIPTIONS.get(cmd)
            if not subcmds:
                return
            for subcmd, desc in sorted(subcmds.items()):
                if subcmd.startswith(subcmd_partial.lower()):
                    yield Completion(subcmd, start_position=-len(subcmd_partial), display_meta=desc)


def _make_prompt(cwd: Path, state: dict) -> FormattedText:
    if not _is_project(cwd):
        return FormattedText([("", ">> ")])
    try:
        name = load_config(cwd).name
    except Exception:
        name = cwd.name
    parts: list[tuple[str, str]] = [("fg:" + _CMD_COLOR, name)]
    if "chapter" in state:
        _, meta = state["chapter"]
        parts.append(("fg:" + _CMD_COLOR, f"/{meta.slug}"))
    parts.append(("", ">> "))
    return FormattedText(parts)


def _open_path(path: Path) -> None:
    editor = os.environ.get("ALTAMIRA_EDITOR")
    if editor:
        subprocess.run([editor, str(path)])
        return
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", str(path)])
    elif system == "Windows":
        os.startfile(str(path))
    else:
        subprocess.run(["xdg-open", str(path)])


def _is_project(cwd: Path) -> bool:
    return (cwd / "altamira.yaml").exists()


def _require_project(cwd: Path) -> bool:
    if not _is_project(cwd):
        console.print("[yellow]Not in an Altamira project.[/yellow] Run: altamira init <dir>")
        return False
    return True


def _chapter_id(args: list[str], state: dict) -> str | None:
    if args:
        return args[0]
    if "chapter" in state:
        _, meta = state["chapter"]
        return meta.slug
    return None


# ── Command handlers ──────────────────────────────────────────────────────────

def _cmd_help(_args: list[str], _cwd: Path, _state: dict) -> None:
    rows = [
        ("commands",             "compact command list"),
        ("history",              "show commands entered this session"),
        ("clear",                "clear the screen"),
        ("status",               "show project name, subject, chapter count"),
        ("config show",          "show all project config fields"),
        ("skill list",           "list available prompt skills"),
        ("chapter list",         "list all chapters"),
        ("chapter new <title>",  "create a new chapter"),
        ("chapter delete <n>",   "move chapter n to trash"),
        ("scan",                 "update the file index"),
        ("review [<n>]",         "review chapter (uses current if no arg)"),
        ("rewrite [<n>]",        "rewrite chapter (uses current if no arg)"),
        ("publish prepare",      "check project readiness for publishing"),
        ("use [<n>]",            "select chapter, or /use alone to deselect"),
        ("open [<n>]",           "open current or given chapter in default app"),
        ("cat [<n>]",            "print chapter markdown to stdout"),
        ("note list",            "list source notes"),
        ("note add <title>",     "create a source note"),
        ("quit",                 "exit the REPL"),
        ("exit",                 "exit the REPL"),
    ]
    console.print("\n[bold]Commands[/bold]\n")
    for cmd, desc in rows:
        console.print(f"  [{_CMD_COLOR}]/{cmd:<28}[/{_CMD_COLOR}]{desc}")
    console.print()


def _cmd_commands(_args: list[str], _cwd: Path, _state: dict) -> None:
    names = sorted(_DISPATCH.keys()) + ["quit", "exit"]
    cols = 3
    col_w = 18
    console.print()
    row: list[str] = []
    for name in sorted(set(names)):
        row.append(f"/{name}")
        if len(row) == cols:
            console.print("  " + "".join(f"[{_CMD_COLOR}]{c:<{col_w}}[/{_CMD_COLOR}]" for c in row))
            row = []
    if row:
        console.print("  " + "".join(f"[{_CMD_COLOR}]{c:<{col_w}}[/{_CMD_COLOR}]" for c in row))
    console.print(f"\n[dim]/help for descriptions[/dim]")


def _cmd_history(_args: list[str], _cwd: Path, state: dict) -> None:
    history = state.get("history", [])
    if not history:
        console.print("[dim]No commands yet.[/dim]")
        return
    for i, entry in enumerate(history, 1):
        console.print(f"  [dim]{i:>3}[/dim]  {entry}")


def _cmd_clear(_args: list[str], _cwd: Path, _state: dict) -> None:
    cmd = "cls" if platform.system() == "Windows" else "clear"
    subprocess.run(cmd, shell=True)


def _cmd_status(_args: list[str], cwd: Path, _state: dict) -> None:
    if not _require_project(cwd):
        return
    config = load_config(cwd)
    kv("project", config.name)
    kv("subject", f"{config.subject_name or '—'}  [{config.subject_type}]")
    kv("language", config.language)
    if config.description:
        kv("desc", config.description)
    console.print()
    chapters = list_chapters(cwd / "chapters")
    notes_dir = cwd / "notes" / "source"
    note_count = len(list(notes_dir.glob("*.md"))) if notes_dir.exists() else 0
    kv("chapters", str(len(chapters)))
    kv("notes", str(note_count))


def _cmd_chapter(args: list[str], cwd: Path, _state: dict) -> None:
    if not _require_project(cwd):
        return
    subcmd = args[0].lower() if args else ""

    if subcmd == "list":
        chapters = list_chapters(cwd / "chapters")
        if not chapters:
            console.print("No chapters yet. Try: /chapter new <title>")
            return
        for ch in chapters:
            console.print(f"  [bold]{ch.order}[/bold]  {ch.title}  [dim]{ch.status}[/dim]")

    elif subcmd == "new":
        title = " ".join(args[1:]).strip()
        if not title:
            console.print("Usage: /chapter new <title>")
            return
        md, _meta, _history = create_chapter(cwd / "chapters", title)
        kv("created", str(md.relative_to(cwd)))

    elif subcmd == "delete":
        if not args[1:]:
            console.print("Usage: /chapter delete <number>")
            return
        result = find_chapter(cwd / "chapters", args[1])
        if result is None:
            console.print(f"Chapter '{args[1]}' not found.")
            return
        chapter_dir, meta = result
        confirm = console.input(f"Delete '[bold]{meta.title}[/bold]'? (y/N) ").strip().lower()
        if confirm != "y":
            console.print("Cancelled.")
            return
        dest = trash_chapter(cwd / "chapters", chapter_dir)
        console.print(f"[yellow]Moved to trash:[/yellow] {dest.name}")

    else:
        console.print("Usage: /chapter list | new <title> | delete <n>")


def _cmd_scan(_args: list[str], cwd: Path, _state: dict) -> None:
    if not _require_project(cwd):
        return
    if ensure_tables(cwd):
        console.print("[dim]Initialized .altamira/app.db[/dim]")
    counts = scan_project(cwd)
    for directory, count in counts.items():
        kv("scanned", f"{directory}/  ({count} files)")


def _cmd_review(args: list[str], cwd: Path, state: dict) -> None:
    if not _require_project(cwd):
        return
    chap_id = _chapter_id(args, state)
    if not chap_id:
        console.print("No chapter selected. Use /review <n> or /use <n> first.")
        return
    try:
        review(chapter=chap_id)
    except (typer.Exit, SystemExit):
        pass


def _cmd_rewrite(args: list[str], cwd: Path, state: dict) -> None:
    if not _require_project(cwd):
        return
    chap_id = _chapter_id(args, state)
    if not chap_id:
        console.print("No chapter selected. Use /rewrite <n> or /use <n> first.")
        return
    try:
        rewrite(chapter=chap_id)
    except (typer.Exit, SystemExit):
        pass


def _cmd_use(args: list[str], cwd: Path, state: dict) -> None:
    if not _require_project(cwd):
        return
    if not args:
        state.pop("chapter", None)
        console.print("Returned to project level.")
        return
    result = find_chapter(cwd / "chapters", args[0])
    if result is None:
        console.print(f"Chapter '{args[0]}' not found.")
        return
    chapter_dir, meta = result
    state["chapter"] = (chapter_dir, meta)
    kv("using", meta.title)


def _cmd_open(args: list[str], cwd: Path, state: dict) -> None:
    if not _require_project(cwd):
        return
    if args:
        result = find_chapter(cwd / "chapters", args[0])
        if result is None:
            console.print(f"Chapter '{args[0]}' not found.")
            return
        chapter_dir, _meta = result
    elif "chapter" in state:
        chapter_dir, _meta = state["chapter"]
    else:
        console.print("No chapter selected. Use /open <n> or /use <n> first.")
        return
    md_path = chapter_dir / f"{chapter_dir.name}.md"
    if not md_path.exists():
        console.print(f"[red]File not found:[/red] {md_path.relative_to(cwd)}")
        return
    console.print(f"Opening [bold]{md_path.relative_to(cwd)}[/bold]…")
    _open_path(md_path)


def _cmd_note(args: list[str], cwd: Path, _state: dict) -> None:
    if not _require_project(cwd):
        return
    subcmd = args[0].lower() if args else ""

    if subcmd == "list":
        notes = list_notes(cwd / "notes" / "source")
        if not notes:
            console.print("No source notes yet. Try: /note add <title>")
            return
        for note in notes:
            tags = f"  [dim]{', '.join(note.tags)}[/dim]" if note.tags else ""
            console.print(f"  {note.title}{tags}")

    elif subcmd == "add":
        title = " ".join(args[1:]).strip()
        if not title:
            console.print("Usage: /note add <title>")
            return
        md, _meta = create_note(cwd / "notes" / "source", title)
        kv("created", str(md.relative_to(cwd)))
        console.print(f"[dim]For more options: altamira note add-source '{title}' --type ... --tag ...[/dim]")

    else:
        console.print("Usage: /note list | add <title>")


def _cmd_config(args: list[str], cwd: Path, _state: dict) -> None:
    if not _require_project(cwd):
        return
    subcmd = args[0].lower() if args else ""
    if subcmd == "show":
        config = load_config(cwd)
        for field, value in config.model_dump().items():
            kv(field, str(value))
    else:
        console.print("Usage: /config show")


def _cmd_publish(args: list[str], cwd: Path, _state: dict) -> None:
    if not _require_project(cwd):
        return
    subcmd = args[0].lower() if args else ""
    if subcmd == "prepare":
        from altamira.domain.publish import run_prepare
        issues = run_prepare(cwd)
        errors = [i for i in issues if i.level == "error"]
        warnings = [i for i in issues if i.level == "warning"]
        if not issues:
            console.print("[green]✓[/green]  All checks passed. Ready to build.")
            return
        if errors:
            console.print(f"\n[bold red]Errors ({len(errors)})[/bold red]")
            for i in errors:
                scope = f"[dim]{i.scope}[/dim]  " if i.scope != "project" else ""
                console.print(f"  [red]✗[/red]  {scope}{i.message}")
        if warnings:
            console.print(f"\n[bold yellow]Warnings ({len(warnings)})[/bold yellow]")
            for i in warnings:
                scope = f"[dim]{i.scope}[/dim]  " if i.scope != "project" else ""
                console.print(f"  [yellow]⚠[/yellow]  {scope}{i.message}")
        console.print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")
    else:
        console.print("Usage: /publish prepare")


def _cmd_cat(args: list[str], cwd: Path, state: dict) -> None:
    if not _require_project(cwd):
        return

    if args and args[0].lower() == "help":
        console.print("\n[bold]Usage[/bold]\n")
        console.print(f"  [{_CMD_COLOR}]/cat[/{_CMD_COLOR}]        print current chapter, or prompt to select one")
        console.print(f"  [{_CMD_COLOR}]/cat <n>[/{_CMD_COLOR}]    print chapter n to stdout")
        console.print(f"  [{_CMD_COLOR}]/cat help[/{_CMD_COLOR}]   show this message\n")
        return

    if args:
        result = find_chapter(cwd / "chapters", args[0])
        if result is None:
            console.print(f"Chapter '{args[0]}' not found.")
            return
        chapter_dir, _meta = result
    elif "chapter" in state:
        chapter_dir, _meta = state["chapter"]
    else:
        chapters = list_chapters(cwd / "chapters")
        if not chapters:
            console.print("No chapters yet.")
            return
        for ch in chapters:
            console.print(f"  [bold]{ch.order}[/bold]  {ch.title}  [dim]{ch.status}[/dim]")
        try:
            choice = console.input("\nChapter number: ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not choice:
            return
        result = find_chapter(cwd / "chapters", choice)
        if result is None:
            console.print(f"Chapter '{choice}' not found.")
            return
        chapter_dir, _meta = result

    md_path = chapter_dir / f"{chapter_dir.name}.md"
    if not md_path.exists():
        console.print(f"[red]File not found:[/red] {md_path.relative_to(cwd)}")
        return
    content = md_path.read_text(encoding="utf-8")
    console.print(f"\n[dim]── {md_path.relative_to(cwd)} ──[/dim]\n")
    console.print(content, markup=False, highlight=False)


def _cmd_skill(args: list[str], _cwd: Path, _state: dict) -> None:
    subcmd = args[0].lower() if args else ""
    if subcmd == "list":
        skills = list_skills()
        if not skills:
            console.print("No skills found.")
            return
        for name, description in skills:
            console.print(f"  [bold]{name:<28}[/bold]{description}")
    else:
        console.print("Usage: /skill list")


# ── Dispatch table ────────────────────────────────────────────────────────────

_DISPATCH = {
    "help":     _cmd_help,
    "commands": _cmd_commands,
    "history":  _cmd_history,
    "clear":    _cmd_clear,
    "status":   _cmd_status,
    "config":   _cmd_config,
    "skill":    _cmd_skill,
    "chapter":  _cmd_chapter,
    "scan":     _cmd_scan,
    "review":   _cmd_review,
    "rewrite":  _cmd_rewrite,
    "use":      _cmd_use,
    "open":     _cmd_open,
    "cat":      _cmd_cat,
    "note":     _cmd_note,
    "publish":  _cmd_publish,
}


# ── Non-interactive execution ─────────────────────────────────────────────────

def _build_agent_context(cwd: Path) -> str:
    """Assemble project text (config + chapter content) for LLM prompts."""
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


def run_single_instruction(instruction: str, cwd: Path) -> int:
    """Execute one instruction as if typed in the REPL. Returns an exit code."""
    instruction = instruction.strip()
    if not instruction:
        console.print("[red]Error:[/red] Instruction cannot be empty.\n")
        console.print("Usage:")
        console.print("  altamira -e '/chapter list'")
        console.print("  altamira -e 'summarize the first three chapters'")
        return 1

    if instruction.startswith("/"):
        if instruction.lower() in ("/quit", "/exit"):
            return 0
        parts = instruction[1:].split()
        cmd = parts[0].lower()
        args = parts[1:]
        handler = _DISPATCH.get(cmd)
        if handler is None:
            console.print(f"[red]Error:[/red] Unknown command: /{cmd}\n")
            console.print("Valid commands: " + "  ".join(f"/{n}" for n in sorted(_DISPATCH)))
            return 1
        state: dict = {"history": []}
        try:
            handler(args, cwd, state)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            return 1
        return 0

    # Plain-English prompt — send to LLM provider with project context.
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


# ── REPL entry point ──────────────────────────────────────────────────────────

def run_repl(cwd: Path) -> None:
    in_project = _is_project(cwd)
    project_label = f"  [dim]{cwd.name}[/dim]" if in_project else "  [yellow]no project[/yellow]"
    console.print(f"\n[bold]Altamira[/bold] v{__version__}{project_label}\n")
    console.print(f"  Commands start with [{_CMD_COLOR}]/[/{_CMD_COLOR}]  —  type [{_CMD_COLOR}]/commands[/{_CMD_COLOR}] for a quick list, [{_CMD_COLOR}]/help[/{_CMD_COLOR}] for details.")
    console.print(f"  Select a chapter with [{_CMD_COLOR}]/use <n>[/{_CMD_COLOR}], then use [{_CMD_COLOR}]/open[/{_CMD_COLOR}]  [{_CMD_COLOR}]/review[/{_CMD_COLOR}]  [{_CMD_COLOR}]/rewrite[/{_CMD_COLOR}]\n")

    state: dict = {"history": []}

    while True:
        try:
            raw = pt_prompt(
                _make_prompt(cwd, state),
                lexer=_ReplLexer(),
                completer=_ReplCompleter(),
                complete_while_typing=True,
                complete_style=CompleteStyle.COLUMN,
                style=_REPL_STYLE,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nBye.")
            break

        if not raw:
            continue

        if raw.lower() in ("/quit", "/exit"):
            console.print("Bye.")
            break

        if not raw.startswith("/"):
            console.print("[yellow]Commands start with /  — try /commands[/yellow]")
            continue

        parts = raw[1:].split()
        cmd = parts[0].lower()
        args = parts[1:]

        handler = _DISPATCH.get(cmd)
        if handler is None:
            console.print(f"[yellow]Unknown command:[/yellow] /{cmd}  — try /commands")
            continue

        console.print(f"[{_CMD_COLOR}]{raw}[/{_CMD_COLOR}]", highlight=False)
        state["history"].append(raw)
        try:
            handler(args, cwd, state)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
