"""
semantic_statistics.py — Compute statistics for Phase R.2.1B.
MODEL_VERSION: 7.11.0
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .semantic_models import EngineeringSemanticObject, MEANING_UNKNOWN


class SemanticStatistics:
    """
    Compute all statistics from the collection of EngineeringSemanticObjects.
    """

    def compute(
        self,
        esos_by_beam: Dict[str, List[EngineeringSemanticObject]],
    ) -> Dict[str, Any]:

        all_esos: List[EngineeringSemanticObject] = [
            e for elist in esos_by_beam.values() for e in elist
        ]
        total = len(all_esos)
        if total == 0:
            return {"total_semantic_objects": 0}

        role_counter     = Counter(e.engineering_role    for e in all_esos)
        meaning_counter  = Counter(e.engineering_meaning for e in all_esos)
        placement_counter= Counter(e.placement           for e in all_esos)
        confidence_ctr   = Counter(e.confidence          for e in all_esos)
        source_ctr       = Counter(e.source              for e in all_esos)

        modifier_counter: Counter = Counter()
        for e in all_esos:
            for mod in e.modifiers:
                modifier_counter[mod] += 1

        unknown_count    = sum(1 for e in all_esos if e.engineering_meaning == MEANING_UNKNOWN)
        overridden_count = sum(1 for e in all_esos if e.role_overridden)
        high_conf        = sum(1 for e in all_esos if e.confidence == "HIGH")
        with_modifiers   = sum(1 for e in all_esos if e.modifiers)

        # Semantic coverage = objects with known meaning / total
        known = total - unknown_count
        coverage_pct = round(100.0 * known / total, 2) if total else 0.0

        # Dictionary coverage = objects that had a dictionary match
        dict_covered = sum(
            1 for e in all_esos
            if e.source in ("SEMANTIC_DICTIONARY", "EXPLICIT_MODIFIER")
        )
        dict_coverage_pct = round(100.0 * dict_covered / total, 2) if total else 0.0

        semantic_confidence = round(100.0 * high_conf / total, 2) if total else 0.0

        return {
            "total_semantic_objects":    total,
            "beams_covered":             len(esos_by_beam),
            "role_distribution":         dict(role_counter.most_common()),
            "meaning_distribution":      dict(meaning_counter.most_common()),
            "modifier_distribution":     dict(modifier_counter.most_common()),
            "placement_distribution":    dict(placement_counter.most_common()),
            "confidence_distribution":   dict(confidence_ctr.most_common()),
            "source_distribution":       dict(source_ctr.most_common()),
            "unknown_count":             unknown_count,
            "role_overrides":            overridden_count,
            "objects_with_modifiers":    with_modifiers,
            "semantic_coverage_pct":     coverage_pct,
            "dictionary_coverage_pct":   dict_coverage_pct,
            "semantic_confidence_pct":   semantic_confidence,
        }
