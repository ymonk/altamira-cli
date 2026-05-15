import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler

from altamira.cli.console import console

# Top-level directories (relative to project root) to silently ignore
_IGNORE_TOP = {"publish", ".altamira"}

# Filename patterns for hidden/temp editor files
_IGNORE_NAME = re.compile(r"^[.~#]|\.sw[op]$|~$")


class ProjectEventHandler(FileSystemEventHandler):
    """Watchdog handler that filters noise and debounces the re-index callback."""

    def __init__(self, root: Path, on_change: Callable[[], None], debounce: float = 0.4):
        super().__init__()
        self._root = root
        self._on_change = on_change
        self._debounce = debounce
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def _should_ignore(self, path: str) -> bool:
        p = Path(path)
        if _IGNORE_NAME.search(p.name):
            return True
        try:
            top = p.relative_to(self._root).parts[0]
            if top in _IGNORE_TOP:
                return True
        except (ValueError, IndexError):
            pass
        return False

    def _schedule_reindex(self) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce, self._on_change)
            self._timer.daemon = True
            self._timer.start()

    def on_any_event(self, event) -> None:
        if event.is_directory:
            return
        src = event.src_path
        if self._should_ignore(src):
            return

        try:
            rel = str(Path(src).relative_to(self._root))
        except ValueError:
            rel = src

        ts = datetime.now().strftime("%H:%M:%S")
        label = event.event_type

        if event.event_type == "moved":
            try:
                dest = str(Path(event.dest_path).relative_to(self._root))
            except ValueError:
                dest = event.dest_path
            console.print(f"[dim]{ts}[/dim]  {label:<10} {rel} → {dest}")
        else:
            console.print(f"[dim]{ts}[/dim]  {label:<10} {rel}")

        self._schedule_reindex()
