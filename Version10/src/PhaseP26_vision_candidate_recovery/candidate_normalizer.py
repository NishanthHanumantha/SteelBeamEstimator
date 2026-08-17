"""Thin wrapper so callers import a dedicated normalizer module."""
from __future__ import annotations

from typing import Any, Dict

from .candidate_schema import empty_candidate, normalize_candidate


def normalize_one(obj: Dict[str, Any], *, beam_id: str, region_id: str, index: int) -> Dict[str, Any]:
    return normalize_candidate(obj, beam_id=beam_id, region_id=region_id, index=index)


__all__ = ["empty_candidate", "normalize_candidate", "normalize_one"]
