"""Engineering object trace package — Phase QA.2."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.estimator_validation.object_trace.trace_engine import TraceEngine


def __getattr__(name: str):
    if name == "TraceEngine":
        from src.estimator_validation.object_trace.trace_engine import TraceEngine

        return TraceEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["TraceEngine"]
