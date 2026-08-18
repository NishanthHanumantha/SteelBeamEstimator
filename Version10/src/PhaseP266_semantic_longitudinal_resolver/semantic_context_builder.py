"""Build GT-free semantic context from P2.6.5 shadow records and R1.3 objects."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP26_vision_candidate_recovery.deterministic_comparator import flatten_r13, role_family

from .config import COVER_LAYER

_DROP_KEYS = {
    "gt_" "match_status",
    "stratum",
    "eval_stratum",
    "drawing_visibility",
    "p26_pilot_overlap",
    "vision_outcome",
    "control_family",
}


def strip_eval_fields(row: Any) -> Any:
    if isinstance(row, dict):
        return {k: strip_eval_fields(v) for k, v in row.items() if k not in _DROP_KEYS}
    if isinstance(row, list):
        return [strip_eval_fields(v) for v in row]
    return row


def _compact_bars(model: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for bar in flatten_r13(model):
        out.append(
            {
                "bar_id": bar.get("bar_id"),
                "family": bar.get("family"),
                "diameter_mm": bar.get("diameter_mm"),
                "quantity": bar.get("quantity"),
                "bar_label": bar.get("bar_label"),
            }
        )
    return out


def _long_cands(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for cand in candidates:
        ctype = str(cand.get("candidate_type") or "").upper()
        if "LONGITUDINAL" not in ctype:
            continue
        out.append(
            strip_eval_fields(
                {
                    "candidate_id": cand.get("candidate_id"),
                    "annotation_text": cand.get("annotation_text") or cand.get("annotation"),
                    "normalized_text": cand.get("normalized_text"),
                    "role": cand.get("role"),
                    "role_family": role_family(cand.get("role")),
                    "diameter_mm": cand.get("diameter_mm"),
                    "quantity": cand.get("quantity"),
                    "deterministic_match_status": cand.get("deterministic_match_status"),
                    "deterministic_match_reason": cand.get("deterministic_match_reason"),
                    "deterministic_matched_bar_id": cand.get("deterministic_matched_bar_id"),
                    "evidence_notes": cand.get("evidence_notes") or [],
                    "beam_association": cand.get("beam_association"),
                }
            )
        )
    return out


def build_semantic_context(
    *,
    p265_decision: Dict[str, Any],
    frozen_candidates: Optional[List[Dict[str, Any]]] = None,
    model: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    feat = dict(p265_decision.get("production_features") or {})
    spat = dict(p265_decision.get("spatial_features") or {})
    anns = list(p265_decision.get("per_annotation_spatial") or [])
    cov_rows = list(p265_decision.get("per_annotation_coverage") or [])
    bars = _compact_bars(model)
    top = [b for b in bars if b.get("family") == "TOP"]
    bot = [b for b in bars if b.get("family") == "BOTTOM"]
    side = [b for b in bars if b.get("family") == "SIDE"]
    long_cands = _long_cands(frozen_candidates or [])
    context = {
        "beam_id": p265_decision.get("beam_id"),
        "set_key": p265_decision.get("set_key"),
        "region_id": p265_decision.get("region_id"),
        "deterministic_reinforcement": {
            "beam_id": p265_decision.get("beam_id"),
            "beam_depth_mm": spat.get("depth_mm") or feat.get("beam_depth_mm"),
            "existing_longitudinal_objects": [b for b in bars if b.get("family") in ("TOP", "BOTTOM")],
            "existing_top_reinforcement": top,
            "existing_bottom_reinforcement": bot,
            "side_face_reinforcement": side,
            "top_quantity": feat.get("top_quantity"),
            "bottom_quantity": feat.get("bottom_quantity"),
            "populated_diameters": feat.get("populated_diameters"),
            "top_diameters": feat.get("top_diameters"),
            "bottom_diameters": feat.get("bottom_diameters"),
            "role_assignments": {
                "has_top": feat.get("has_top"),
                "has_bottom": feat.get("has_bottom"),
                "populated_layer": feat.get("populated_layer") or spat.get("populated_layer"),
            },
            "accepted_specs": feat.get("accepted_specs") or [],
            "accepted_spec_count": feat.get("unique_accepted_spec_count"),
            "accepted_instance_count": feat.get("accepted_instance_count"),
            "extra_object_count": feat.get("extra_object_count"),
            "quantity_shortfall": feat.get("quantity_shortfall_count"),
            "role_conflicts": feat.get("role_conflict_count"),
            "diameter_conflicts": feat.get("diameter_conflict_count"),
            "role_coverage_status": feat.get("role_gap_status") or p265_decision.get("role_gap_status"),
            "longitudinal_coverage_status": p265_decision.get("longitudinal_coverage") or COVER_LAYER,
            "role_gap_status": p265_decision.get("role_gap_status"),
            "role_gap_reason": p265_decision.get("role_gap_reason"),
            "unmatched_longitudinal_count": feat.get("unmatched_longitudinal_count"),
            "rejected_annotation_count": feat.get("rejected_annotation_count"),
            "coverage_rows": strip_eval_fields(cov_rows),
        },
        "annotation_context": strip_eval_fields(anns if anns else cov_rows),
        "spatial_context": {
            "label": "SUPPORTING_EVIDENCE_ONLY",
            "do_not_treat_as_skip_rule": True,
            "top_bottom_zone_available": {
                "top": spat.get("top_zone_available"),
                "bottom": spat.get("bottom_zone_available"),
            },
            "leader_tip_zone_votes": spat.get("tip_layer_votes"),
            "cross_layer_evidence": "CROSS_LAYER_SEPARATION"
            in (p265_decision.get("context_evidence_codes") or []),
            "repeated_separate_location": spat.get("repeated_separate_location"),
            "annotation_cluster_separation": spat.get("annotation_cluster_separation"),
            "physical_bar_proximity": spat.get("min_object_distance"),
            "physical_bar_availability": spat.get("physical_bar_geometry_available"),
            "spatial_context_status": p265_decision.get("context_status"),
            "context_evidence_codes": p265_decision.get("context_evidence_codes"),
            "context_score": p265_decision.get("context_score"),
            "populated_layer": spat.get("populated_layer") or feat.get("populated_layer"),
        },
        "frozen_vision_longitudinal_observations": long_cands,
        "crop_path": p265_decision.get("crop_path"),
    }
    return strip_eval_fields(context)


__all__ = ["build_semantic_context", "strip_eval_fields"]
