"""Offline control-case table. Evaluation only — not imported by the classifier."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .config import COVER_LAYER


TRUE_RECOVERY_CONTROLS = (
    ("Fifth", "B128"),
    ("Fifth", "B173"),
    ("Fourth", "B102"),
    ("Fourth", "B170"),
    ("Fourth", "B173"),
    ("Fourth", "B174"),
    ("Sixth", "B138"),
)
DUPLICATE_CONTROLS = (
    ("Fifth", "B100"),
    ("Fourth", "B23"),
    ("Fourth", "B141"),
    ("Fifth", "B62"),
    ("Sixth", "B56"),
    ("Fourth", "B143"),
    ("Fourth", "B176"),
    ("Sixth", "B45"),
)
FALSE_SKIP_CONTROLS = (("Fifth", "B136"),)


def _vis(cands: List[Dict[str, Any]], set_key: str, beam_id: str) -> Dict[str, Any]:
    long_c = [
        c
        for c in cands
        if c.get("set_key") == set_key
        and c.get("beam_id") == beam_id
        and "LONGITUDINAL" in str(c.get("candidate_type") or "").upper()
    ]
    tr = sum(1 for c in long_c if c.get("gt_match_status") == "TRUE_RECOVERY")
    dup = sum(
        1
        for c in long_c
        if c.get("gt_match_status") == "DUPLICATE"
        or c.get("deterministic_match_status") == "ALREADY_DETECTED"
    )
    uns = sum(1 for c in long_c if c.get("gt_match_status") == "UNSUPPORTED")
    texts = list(
        dict.fromkeys(str(c.get("annotation") or c.get("annotation_text") or "") for c in long_c)
    )
    return {
        "vision_true_recoveries": tr,
        "vision_duplicates": dup,
        "vision_unsupported": uns,
        "vision_duplicate_only": tr == 0 and dup > 0 and uns == 0,
        "vision_outcome": (
            "TRUE_RECOVERY"
            if tr > 0
            else ("DUPLICATE_ONLY" if dup > 0 and uns == 0 else "OTHER")
        ),
        "annotation_texts": texts,
    }


def build_control_table(
    *,
    decisions: List[Dict[str, Any]],
    frozen_candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by: Dict[Tuple[Any, Any], Dict[str, Any]] = {
        (d.get("set_key"), d.get("beam_id")): d for d in decisions
    }
    wanted = list(TRUE_RECOVERY_CONTROLS) + list(DUPLICATE_CONTROLS) + list(FALSE_SKIP_CONTROLS)
    rows: List[Dict[str, Any]] = []
    for set_key, beam_id in wanted:
        d = by.get((set_key, beam_id)) or {}
        spat = d.get("spatial_features") or {}
        vis = _vis(frozen_candidates, set_key, beam_id)
        family = (
            "TRUE_RECOVERY_CONTROL"
            if (set_key, beam_id) in TRUE_RECOVERY_CONTROLS
            else (
                "FALSE_SKIP_CONTROL"
                if (set_key, beam_id) in FALSE_SKIP_CONTROLS
                else "DUPLICATE_CONTROL"
            )
        )
        rows.append(
            {
                "family": family,
                "set_key": set_key,
                "beam_id": beam_id,
                "eval_stratum": d.get("eval_stratum"),
                "annotation": vis.get("annotation_texts"),
                "populated_layer": spat.get("populated_layer")
                or (d.get("production_features") or {}).get("populated_layer"),
                "longitudinal_coverage": d.get("longitudinal_coverage"),
                "p264_decision": d.get("observed_decision") or d.get("decision"),
                "hypothetical_decision": d.get("hypothetical_decision"),
                "context_status": d.get("context_status"),
                "evidence_codes": d.get("context_evidence_codes"),
                "tip_layer_votes": spat.get("tip_layer_votes"),
                "max_repeat_dy": spat.get("max_repeat_dy"),
                "physical_bar_count": spat.get("physical_bar_count"),
                "leader_count": spat.get("leader_count"),
                "annotation_xy_available": spat.get("annotation_xy_available"),
                "role_gap_status": d.get("role_gap_status"),
                "role_gap_reason": d.get("role_gap_reason"),
                **vis,
                "in_sample": bool(d),
                "is_role_coverage_gap": d.get("longitudinal_coverage") == COVER_LAYER,
            }
        )
    return rows


__all__ = [
    "DUPLICATE_CONTROLS",
    "FALSE_SKIP_CONTROLS",
    "TRUE_RECOVERY_CONTROLS",
    "build_control_table",
]
