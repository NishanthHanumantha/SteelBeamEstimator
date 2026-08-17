"""P2.6 policy constants. Runtime must stay GT-free."""
from __future__ import annotations

from .config import DECISION_SHADOW, ENGINEERING_CHANGES, PRODUCTION_WRITE

RUNTIME_CONTEXT_KEYS = (
    "beam_id",
    "region_id",
    "crop_path",
    "accepted_annotations",
    "gap_reasons",
    "r13_summary",
    "quantity_statuses",
    "ocr_flags",
)


def assert_runtime_context(ctx: dict) -> None:
    extra = sorted(set(ctx) - set(RUNTIME_CONTEXT_KEYS))
    if extra:
        raise ValueError(f"unsupported runtime context key: {extra[0]}")


__all__ = [
    "DECISION_SHADOW",
    "ENGINEERING_CHANGES",
    "PRODUCTION_WRITE",
    "RUNTIME_CONTEXT_KEYS",
    "assert_runtime_context",
]
