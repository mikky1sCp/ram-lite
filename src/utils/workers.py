from __future__ import annotations

import threading
from typing import Callable

from PySide6.QtCore import QObject, Signal


class BackgroundTask(QObject):
    """Runs a callable on a daemon thread and delivers the outcome to the UI thread."""

    completed = Signal(object)
    failed = Signal(object)

    def __init__(self, work: Callable[[], object], parent=None):
        super().__init__(parent)
        self._work = work
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            result = self._work()
        except Exception as exc:
            self.failed.emit(exc)
        else:
            self.completed.emit(result)