"""Process-level single-flight guard for Version10 web estimates.

Concurrent runs are not proven safe (shared General Notes pointer).
POC policy: one estimation at a time.
"""
from __future__ import annotations

import threading
from typing import Optional


class FlightGuard:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_run_id: Optional[str] = None

    def acquire(self, run_id: str) -> bool:
        with self._lock:
            if self._active_run_id is not None:
                return False
            self._active_run_id = run_id
            return True

    def release(self, run_id: str) -> None:
        with self._lock:
            if self._active_run_id == run_id:
                self._active_run_id = None

    def active_run_id(self) -> Optional[str]:
        with self._lock:
            return self._active_run_id

    def is_busy(self) -> bool:
        return self.active_run_id() is not None


GUARD = FlightGuard()
