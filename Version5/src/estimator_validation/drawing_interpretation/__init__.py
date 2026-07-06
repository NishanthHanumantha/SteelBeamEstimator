"""Drawing interpretation audit package — Phase QA.3."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.estimator_validation.drawing_interpretation.interpretation_builder import InterpretationAuditBuilder


def __getattr__(name: str):
    if name == "InterpretationAuditBuilder":
        from src.estimator_validation.drawing_interpretation.interpretation_builder import InterpretationAuditBuilder

        return InterpretationAuditBuilder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["InterpretationAuditBuilder"]
