"""Lightweight wall-clock timer for performance_profile.json."""
from __future__ import annotations

import time
from typing import Optional


class Timer:
    def __init__(self) -> None:
        self.seconds = 0.0
        self._t0: Optional[float] = None

    def __enter__(self) -> "Timer":
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc) -> None:
        self.seconds = time.perf_counter() - (self._t0 or time.perf_counter())


class PerfClock:
    def __init__(self) -> None:
        self.buckets = {
            "dxf_load_s": 0.0,
            "discovery_s": 0.0,
            "region_s": 0.0,
            "context_render_s": 0.0,
            "detail_render_s": 0.0,
            "quality_s": 0.0,
            "recovery_s": 0.0,
            "diagnostic_io_s": 0.0,
            "reuse_copy_s": 0.0,
        }
        self.t0 = time.perf_counter()

    def add(self, name: str, seconds: float) -> None:
        self.buckets[name] = self.buckets.get(name, 0.0) + float(seconds)

    def elapsed(self) -> float:
        return time.perf_counter() - self.t0
