"""
Pattern Registry — stores and indexes all EngineeringPattern records.

Registry entry per beam:
  pattern_id, beam_id, pattern_type, confidence, creation_stage,
  classification_source, validation_status.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pattern_models import EngineeringPattern

PHASE = "L.3"
MODEL_VERSION = "6.5.0"
CREATION_STAGE = "PhaseL3_PatternRecognition"


class PatternRegistry:

    def __init__(self) -> None:
        self._patterns: Dict[str, EngineeringPattern] = {}
        self._registry_entries: List[Dict[str, Any]] = []

    def register(self, pattern: EngineeringPattern) -> None:
        self._patterns[pattern.beam_id] = pattern
        self._registry_entries.append(
            {
                "pattern_id": pattern.pattern_id,
                "beam_id": pattern.beam_id,
                "beam_name": pattern.beam_name,
                "pattern_type": pattern.span_pattern,
                "continuity_type": pattern.continuity_pattern,
                "reinforcement_pattern": pattern.reinforcement_pattern,
                "structural_behavior": pattern.structural_behavior,
                "confidence": pattern.classification_confidence,
                "confidence_level": pattern.confidence_level,
                "creation_stage": CREATION_STAGE,
                "classification_source": "L2.1_EngineeringFeatures",
                "validation_status": "PENDING",
                "registered_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def get(self, beam_id: str) -> Optional[EngineeringPattern]:
        return self._patterns.get(beam_id)

    def all_patterns(self) -> List[EngineeringPattern]:
        return list(self._patterns.values())

    def beam_ids(self) -> List[str]:
        return sorted(self._patterns.keys(), key=lambda b: (len(b), b))

    def count(self) -> int:
        return len(self._patterns)

    def update_validation_status(self, beam_id: str, status: str) -> None:
        for entry in self._registry_entries:
            if entry["beam_id"] == beam_id:
                entry["validation_status"] = status

    def to_registry_list(self) -> List[Dict[str, Any]]:
        return list(self._registry_entries)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "total_patterns": self.count(),
            "beam_ids": self.beam_ids(),
            "creation_stage": CREATION_STAGE,
            "registry": self.to_registry_list(),
        }
