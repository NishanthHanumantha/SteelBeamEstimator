"""Offline ROLE_COVERAGE_GAP diagnostics. Evaluation only — not imported by the gate."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .config import COVER_LAYER, DECISION_CALL, P263_OUTPUT_DIRNAME

_V10 = Path(__file__).resolve().parents[2]


def _load_p263_decisions() -> Dict[Tuple[Any, Any], Dict[str, Any]]:
    path = _V10 / "data" / "output" / P263_OUTPUT_DIRNAME / "gate_decisions.json"
    if not path.exists():
        return {}
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {(r.get("set_key"), r.get("beam_id")): r for r in rows if isinstance(r, dict)}


def build_role_gap_diagnostics(
    *,
    decisions: List[Dict[str, Any]],
    frozen_candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_beam: Dict[Tuple[Any, Any], List[Dict[str, Any]]] = {}
    for c in frozen_candidates:
        key = (c.get("set_key"), c.get("beam_id"))
        by_beam.setdefault(key, []).append(c)
    p263 = _load_p263_decisions()
    rows: List[Dict[str, Any]] = []
    for d in decisions:
        if d.get("longitudinal_coverage") != COVER_LAYER:
            continue
        key = (d.get("set_key"), d.get("beam_id"))
        cands = by_beam.get(key) or []
        long_c = [
            c
            for c in cands
            if "LONGITUDINAL" in str(c.get("candidate_type") or "").upper()
        ]
        statuses = [str(c.get("gt_match_status") or "") for c in long_c]
        tr = sum(1 for s in statuses if s == "TRUE_RECOVERY")
        dup = sum(
            1
            for c in long_c
            if c.get("gt_match_status") == "DUPLICATE"
            or c.get("deterministic_match_status") == "ALREADY_DETECTED"
        )
        uns = sum(1 for s in statuses if s == "UNSUPPORTED")
        amb = sum(1 for s in statuses if s == "AMBIGUOUS")
        feat = d.get("production_features") or {}
        anns = d.get("per_annotation_coverage") or feat.get("per_annotation_coverage") or []
        ann_specs = [
            {
                "text": a.get("text") or a.get("raw_text"),
                "quantity": a.get("quantity"),
                "diameter_mm": a.get("diameter_mm"),
                "role": a.get("role") or "UNKNOWN",
            }
            for a in anns
        ]
        p263_row = p263.get(key) or {}
        duplicate_only = (
            d.get("decision") == DECISION_CALL and tr == 0 and dup > 0 and uns == 0
        )
        rows.append(
            {
                "set_key": d.get("set_key"),
                "beam_id": d.get("beam_id"),
                "eval_stratum": d.get("eval_stratum"),
                "populated_layer": feat.get("populated_layer"),
                "top_object_count": feat.get("long_top_object_count"),
                "bottom_object_count": feat.get("long_bottom_object_count"),
                "top_quantity": feat.get("top_quantity"),
                "bottom_quantity": feat.get("bottom_quantity"),
                "top_diameters": feat.get("top_diameters") or [],
                "bottom_diameters": feat.get("bottom_diameters") or [],
                "annotation_specs": ann_specs,
                "unknown_annotation_count": feat.get("unknown_annotation_count"),
                "known_role_annotation_count": feat.get("known_role_annotation_count"),
                "extra_object_count": feat.get("extra_object_count"),
                "unique_accepted_spec_count": feat.get("unique_accepted_spec_count"),
                "accepted_instance_count": feat.get("accepted_instance_count"),
                "accepted_matches_main": feat.get("accepted_matches_main"),
                "rejected_matching_populated": feat.get("rejected_matching_populated"),
                "quantity_shortfall_count": feat.get("quantity_shortfall_count"),
                "role_conflict_count": feat.get("role_conflict_count"),
                "diameter_conflict_count": feat.get("diameter_conflict_count"),
                "association": feat.get("association"),
                "longitudinal_coverage": d.get("longitudinal_coverage"),
                "role_gap_status": d.get("role_gap_status"),
                "role_gap_reason": d.get("role_gap_reason"),
                "gate_decision": d.get("decision"),
                "reason_codes": d.get("reason_codes"),
                "p263_decision": p263_row.get("decision"),
                "p263_reason_codes": p263_row.get("reason_codes"),
                "vision_true_recoveries": tr,
                "vision_duplicates": dup,
                "vision_unsupported": uns,
                "vision_ambiguous": amb,
                "vision_duplicate_only": bool(duplicate_only),
                "p263_recovery_status": (
                    "TRUE_RECOVERY"
                    if tr > 0
                    else ("DUPLICATE_ONLY" if dup > 0 and uns == 0 else "NO_LONGITUDINAL_TR")
                ),
                "p263_style_coverage": COVER_LAYER,
            }
        )
    return rows


__all__ = ["build_role_gap_diagnostics"]
