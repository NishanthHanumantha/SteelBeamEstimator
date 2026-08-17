"""P2.6.1 policy. Runtime must stay GT-free. Vision metadata must stay unframed."""
from __future__ import annotations

from .config import DECISION_SHADOW, ENGINEERING_CHANGES, PRODUCTION_WRITE

BANNED_VISION_METADATA_KEYS = (
    "gap_reasons",
    "selection_reason",
    "stratum",
    "expected_failure_type",
    "expected_missing_bar",
    "failure_labels",
    "selection_features",
    "score",
)

RUNTIME_CONTEXT_KEYS = (
    "beam_id",
    "region_id",
    "crop_path",
    "set_key",
    "source_set",
    "r13_summary",
    "annotation_count",
    "ocr_flags",
)


def assert_runtime_context(ctx: dict) -> None:
    extra = sorted(set(ctx) - set(RUNTIME_CONTEXT_KEYS))
    if extra:
        raise ValueError(f"unsupported runtime context key: {extra[0]}")


def assert_neutral_metadata(metadata: dict) -> None:
    for k in BANNED_VISION_METADATA_KEYS:
        if k in metadata:
            raise ValueError(f"framed Vision metadata key: {k}")


__all__ = [
    "BANNED_VISION_METADATA_KEYS",
    "DECISION_SHADOW",
    "ENGINEERING_CHANGES",
    "PRODUCTION_WRITE",
    "RUNTIME_CONTEXT_KEYS",
    "assert_neutral_metadata",
    "assert_runtime_context",
]
