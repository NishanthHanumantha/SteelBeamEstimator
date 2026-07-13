"""
Pattern Reporter — builds structured report payloads for Phase L.3.

Produces
--------
Pattern Summary        aggregate counts + statistics
Beam Pattern Matrix    one row per beam with all pattern fields
Confidence Distribution  HIGH/MEDIUM/LOW breakdown
Pattern Counts          per-type totals
"""

from __future__ import annotations

import collections
from typing import Any, Dict, List

from pattern_models import EngineeringPattern
from pattern_registry import PatternRegistry

PHASE = "L.3"
MODEL_VERSION = "6.5.0"


def build_pattern_statistics(
    patterns: List[EngineeringPattern],
) -> Dict[str, Any]:
    """Compute aggregate statistics across all beam patterns."""
    total = len(patterns)
    if total == 0:
        return {"total_beams": 0}

    span_counts: Dict[str, int] = collections.Counter(p.span_pattern for p in patterns)
    cont_counts: Dict[str, int] = collections.Counter(p.continuity_pattern for p in patterns)
    rein_counts: Dict[str, int] = collections.Counter(p.reinforcement_pattern for p in patterns)
    supp_counts: Dict[str, int] = collections.Counter(p.support_pattern for p in patterns)
    behav_counts: Dict[str, int] = collections.Counter(p.structural_behavior for p in patterns)
    conf_counts: Dict[str, int] = collections.Counter(p.confidence_level for p in patterns)
    balance_counts: Dict[str, int] = collections.Counter(p.top_bottom_balance for p in patterns)

    avg_conf = round(sum(p.classification_confidence for p in patterns) / total, 4)
    min_conf = round(min(p.classification_confidence for p in patterns), 4)
    max_conf = round(max(p.classification_confidence for p in patterns), 4)

    return {
        "total_beams": total,
        "span_pattern_distribution": dict(span_counts),
        "continuity_distribution": dict(cont_counts),
        "reinforcement_pattern_distribution": dict(rein_counts),
        "support_pattern_distribution": dict(supp_counts),
        "structural_behavior_distribution": dict(behav_counts),
        "confidence_distribution": dict(conf_counts),
        "top_bottom_balance_distribution": dict(balance_counts),
        "confidence_stats": {
            "mean": avg_conf,
            "min": min_conf,
            "max": max_conf,
        },
    }


def build_beam_pattern_matrix(patterns: List[EngineeringPattern]) -> List[Dict[str, Any]]:
    """One row per beam with key pattern fields for the matrix view."""
    return [
        {
            "beam_id": p.beam_id,
            "span_pattern": p.span_pattern,
            "continuity_pattern": p.continuity_pattern,
            "reinforcement_pattern": p.reinforcement_pattern,
            "support_pattern": p.support_pattern,
            "structural_behavior": p.structural_behavior,
            "top_bottom_balance": p.top_bottom_balance,
            "dominant_reinforcement": p.dominant_reinforcement,
            "confidence": p.classification_confidence,
            "confidence_level": p.confidence_level,
        }
        for p in sorted(patterns, key=lambda p: (len(p.beam_id), p.beam_id))
    ]


def build_pattern_summary(
    patterns: List[EngineeringPattern],
    validation_result: Dict[str, Any],
    statistics: Dict[str, Any],
    run_timestamp: str,
    duration_s: float,
) -> Dict[str, Any]:
    return {
        "phase": PHASE,
        "model_version": MODEL_VERSION,
        "run_timestamp": run_timestamp,
        "duration_s": round(duration_s, 3),
        "total_beams_classified": len(patterns),
        "validation_status": validation_result.get("status"),
        "statistics": statistics,
        "beam_ids_classified": sorted(
            [p.beam_id for p in patterns],
            key=lambda b: (len(b), b),
        ),
    }
