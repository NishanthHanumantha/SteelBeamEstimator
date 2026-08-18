"""P2.6.3 gate features: P2.6.2 production signals plus longitudinal coverage."""
from __future__ import annotations

from typing import Any, Dict, Optional

from PhaseP262_selective_vision_candidate_gate.gate_features import (
    extract_gate_features as extract_p262_features,
)

from .longitudinal_coverage import evaluate_longitudinal_coverage


def extract_gate_features(
    *,
    beam_id: str,
    rec: Dict[str, Any],
    model: Optional[Dict[str, Any]],
    association: str = "TARGET_BEAM",
) -> Dict[str, Any]:
    feat = extract_p262_features(
        beam_id=beam_id, rec=rec, model=model, association=association
    )
    cov = evaluate_longitudinal_coverage(rec=rec, model=model)
    feat.update(cov)
    if cov.get("longitudinal_coverage") == "MISSING_OBJECT":
        feat["unmatched_longitudinal_count"] = max(
            1, int(feat.get("unmatched_longitudinal_count") or 0)
        )
    elif not cov.get("longitudinal_gap"):
        feat["unmatched_longitudinal_count"] = 0
        feat["longitudinal_object_shortfall"] = 0
    return feat


__all__ = ["extract_gate_features"]
