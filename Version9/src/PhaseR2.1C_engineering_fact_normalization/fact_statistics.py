"""
fact_statistics.py — Engineering fact statistics for Phase R.2.1C.
MODEL_VERSION: 7.12.0

Computed statistics:
  - Role distribution
  - Placement distribution
  - Intent UNKNOWN count
  - Candidate distribution (which candidates appear, how often)
  - Modifier distribution
  - Confidence distribution
  - Coverage (non-unknown role, non-unknown placement)
  - Geometry-required count
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .fact_models import EngineeringFact, INTENT_UNKNOWN, PLACEMENT_UNKNOWN, ROLE_UNKNOWN


class FactStatistics:

    def compute(self, facts_by_beam: Dict[str, List[EngineeringFact]]) -> Dict[str, Any]:
        all_facts = [f for fl in facts_by_beam.values() for f in fl]
        total = len(all_facts)

        role_ctr       = Counter(f.role for f in all_facts)
        placement_ctr  = Counter(f.placement for f in all_facts)
        confidence_ctr = Counter(f.confidence for f in all_facts)
        modifier_ctr   = Counter(m for f in all_facts for m in f.modifiers)
        candidate_ctr  = Counter(c for f in all_facts for c in f.intent_candidates)
        source_ctr     = Counter(f.source for f in all_facts)

        intent_unknown = sum(1 for f in all_facts if f.intent == INTENT_UNKNOWN)
        geometry_req   = sum(1 for f in all_facts if f.geometry_required)

        role_known      = total - role_ctr.get(ROLE_UNKNOWN, 0)
        placement_known = total - placement_ctr.get(PLACEMENT_UNKNOWN, 0)
        role_coverage      = (role_known / total * 100) if total else 0.0
        placement_coverage = (placement_known / total * 100) if total else 0.0

        beam_count = len(facts_by_beam)
        per_beam   = {bid: len(fl) for bid, fl in facts_by_beam.items()}

        return {
            "total_facts":           total,
            "beam_count":            beam_count,
            "per_beam_fact_count":   per_beam,
            "role_distribution":     dict(role_ctr),
            "placement_distribution":dict(placement_ctr),
            "confidence_distribution":dict(confidence_ctr),
            "modifier_distribution": dict(modifier_ctr),
            "candidate_distribution":dict(candidate_ctr),
            "source_distribution":   dict(source_ctr),
            "intent_unknown_count":  intent_unknown,
            "intent_unknown_pct":    round(intent_unknown / total * 100, 1) if total else 0.0,
            "geometry_required_count": geometry_req,
            "geometry_required_pct": round(geometry_req / total * 100, 1) if total else 0.0,
            "role_coverage_pct":      round(role_coverage, 1),
            "placement_coverage_pct": round(placement_coverage, 1),
        }
