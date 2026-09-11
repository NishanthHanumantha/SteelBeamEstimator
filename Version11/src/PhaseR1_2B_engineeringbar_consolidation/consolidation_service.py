"""
Dict-level consolidation service (no R.1.3 import dependency).
MODEL_VERSION: 8.3.1
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .engineeringbar_consolidator import EngineeringBarConsolidator

MODEL_VERSION = "8.3.1"


class EngineeringBarConsolidationService:
    """Apply R.1.2B consolidation to beam-model dicts."""

    def __init__(self, threshold: float = 0.85):
        self._consolidator = EngineeringBarConsolidator(threshold=threshold)

    def apply(
        self, beam_model_dicts: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        consolidated, payload = self._consolidator.consolidate(beam_model_dicts)
        payload["model_version"] = MODEL_VERSION
        return consolidated, payload
