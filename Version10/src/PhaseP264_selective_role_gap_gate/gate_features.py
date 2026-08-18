"""P2.6.4 gate features: P2.6.3 coverage plus selective role-gap overlay."""
from __future__ import annotations

from typing import Any, Dict, Optional

from PhaseP263_longitudinal_aware_gate.gate_features import (
    extract_gate_features as extract_p263_features,
)

from .config import COVER_LAYER, ROLE_GAP_EXPLAINED
from .role_gap import evaluate_selective_role_gap


def extract_gate_features(
    *,
    beam_id: str,
    rec: Dict[str, Any],
    model: Optional[Dict[str, Any]],
    association: str = "TARGET_BEAM",
) -> Dict[str, Any]:
    feat = extract_p263_features(
        beam_id=beam_id, rec=rec, model=model, association=association
    )
    rg = evaluate_selective_role_gap(rec=rec, model=model, coverage=feat)
    feat.update(rg)
    if feat.get("longitudinal_coverage") == COVER_LAYER and rg.get(
        "role_gap_status"
    ) == ROLE_GAP_EXPLAINED:
        feat["longitudinal_gap"] = False
        feat["unmatched_longitudinal_count"] = 0
        feat["longitudinal_object_shortfall"] = 0
    return feat


__all__ = ["extract_gate_features"]
