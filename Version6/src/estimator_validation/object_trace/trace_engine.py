"""Engineering object trace engine — Phase QA.2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.estimator_validation.object_trace.trace_builder import TraceBuilder


class TraceEngine:
    """Orchestrate read-only engineering object trace and identity matching."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path.cwd()
        self.builder = TraceBuilder(self.project_root)

    def run(self) -> dict[str, Any]:
        return self.builder.build()
