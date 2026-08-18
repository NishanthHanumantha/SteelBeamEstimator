"""Offline control-case table. Evaluation only — not imported by the resolver."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .config import COVER_FULL, COVER_LAYER

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

SEPARABILITY_TRIPLE = (("Fifth", "B128"), ("Fourth", "B141"), ("Fourth", "B23"))


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
    det = sorted({str(c.get("deterministic_match_status") or "") for c in long_c if c.get("deterministic_match_status")})
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
        "frozen_det_match_statuses": det,
    }


def build_control_table(
    *,
    records: List[Dict[str, Any]],
    frozen_candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by: Dict[Tuple[Any, Any], Dict[str, Any]] = {
        (d.get("set_key"), d.get("beam_id")): d for d in records
    }
    wanted = list(TRUE_RECOVERY_CONTROLS) + list(DUPLICATE_CONTROLS) + list(FALSE_SKIP_CONTROLS)
    rows: List[Dict[str, Any]] = []
    for set_key, beam_id in wanted:
        d = by.get((set_key, beam_id)) or {}
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
        semantic = d.get("semantic") or {}
        hypo = d.get("hypothetical") or {}
        rows.append(
            {
                "family": family,
                "set_key": set_key,
                "beam_id": beam_id,
                "eval_stratum": d.get("eval_stratum"),
                "annotation": vis.get("annotation_texts"),
                "populated_layer": (d.get("production_features") or {}).get("populated_layer")
                or ((d.get("spatial_features") or {}).get("populated_layer")),
                "longitudinal_coverage": d.get("longitudinal_coverage"),
                "p264_decision": d.get("observed_decision") or d.get("decision"),
                "p265_context_status": d.get("context_status"),
                "p265_evidence_codes": d.get("context_evidence_codes"),
                "semantic_class": semantic.get("decision"),
                "semantic_confidence": semantic.get("confidence"),
                "semantic_source": semantic.get("source") or d.get("adapter_source"),
                "target_layer": semantic.get("target_layer"),
                "representation": semantic.get("existing_representation_assessment"),
                "reason_codes": semantic.get("semantic_reason_codes"),
                "spatial_context_consistent": semantic.get("spatial_context_consistent"),
                "deterministic_context_consistent": semantic.get("deterministic_context_consistent"),
                "conflict_present": semantic.get("conflict_present"),
                "shadow_decision": hypo.get("semantic_decision"),
                "hypothetical_vision_routing": hypo.get("hypothetical_vision_routing"),
                "hypothetical_reason": hypo.get("hypothetical_reason"),
                "safe_skip_candidate": hypo.get("safe_skip_candidate"),
                "in_sample": bool(d),
                "is_role_coverage_gap": d.get("longitudinal_coverage") == COVER_LAYER,
                "is_fully_covered": d.get("longitudinal_coverage") == COVER_FULL,
                **vis,
            }
        )
    return rows


def separability_report(controls: List[Dict[str, Any]]) -> Dict[str, Any]:
    by = {(r.get("set_key"), r.get("beam_id")): r for r in controls}
    b128 = by.get(("Fifth", "B128")) or {}
    b141 = by.get(("Fourth", "B141")) or {}
    b23 = by.get(("Fourth", "B23")) or {}
    cls128 = b128.get("semantic_class")
    cls141 = b141.get("semantic_class")
    cls23 = b23.get("semantic_class")
    distinguished = (
        cls128 == "DISTINCT_REINFORCEMENT"
        and cls141 == "DUPLICATE_OR_REPEAT"
        and cls23 == "DUPLICATE_OR_REPEAT"
    )
    spatial_same = (
        b128.get("p265_context_status")
        and b128.get("p265_context_status") == b141.get("p265_context_status") == b23.get("p265_context_status")
    )
    return {
        "b128_class": cls128,
        "b141_class": cls141,
        "b23_class": cls23,
        "b128_p265_context": b128.get("p265_context_status"),
        "b141_p265_context": b141.get("p265_context_status"),
        "b23_p265_context": b23.get("p265_context_status"),
        "spatial_pattern_same": bool(spatial_same),
        "semantic_distinguishes_b128_from_b141_b23": distinguished,
        "note": (
            "P2.6.5 spatial status could not separate these three. "
            "P2.6.6 success is semantic class separation, not call reduction."
        ),
    }


__all__ = [
    "DUPLICATE_CONTROLS",
    "FALSE_SKIP_CONTROLS",
    "SEPARABILITY_TRIPLE",
    "TRUE_RECOVERY_CONTROLS",
    "build_control_table",
    "separability_report",
]
