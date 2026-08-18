"""Attach spatial/context shadow evidence to a frozen P2.6.4 decision. Does not change routing."""
from __future__ import annotations

from typing import Any, Dict, Optional

from PhaseP264_selective_role_gap_gate.gate_decision import build_gate_decision as p264_build

from .config import COVER_LAYER, GATE_VERSION
from .context_classifier import classify_spatial_context
from .spatial_features import extract_spatial_features


def build_shadow_record(
    *,
    beam_id: str,
    region_id: str,
    rec: Dict[str, Any],
    model: Optional[Dict[str, Any]],
    scoped: Optional[Dict[str, Any]] = None,
    association: str = "TARGET_BEAM",
    set_key: str = "",
    source_set: str = "",
    crop_path: Optional[str] = None,
) -> Dict[str, Any]:
    decision = p264_build(
        beam_id=beam_id,
        region_id=region_id,
        rec=rec,
        model=model,
        association=association,
        set_key=set_key,
        source_set=source_set,
        crop_path=crop_path,
    )
    feat = decision.get("production_features") or {}
    spatial = extract_spatial_features(rec=rec, scoped=scoped, production_features=feat)
    context = classify_spatial_context(
        spatial=spatial,
        production_features=feat,
        longitudinal_coverage=decision.get("longitudinal_coverage"),
    )
    decision["spatial_features"] = {k: spatial[k] for k in spatial if k != "per_annotation"}
    decision["per_annotation_spatial"] = spatial.get("per_annotation") or []
    decision["context_status"] = context["context_status"]
    decision["context_evidence_codes"] = context["evidence_codes"]
    decision["context_score"] = context["context_score"]
    decision["context_call_votes"] = context["call_votes"]
    decision["context_skip_votes"] = context["skip_votes"]
    decision["shadow_gate_version"] = GATE_VERSION
    decision["observed_decision"] = decision.get("decision")
    decision["production_routing_changed"] = False
    decision["target_population"] = (
        "ROLE_COVERAGE_GAP"
        if decision.get("longitudinal_coverage") == COVER_LAYER
        else decision.get("longitudinal_coverage")
    )
    return decision


__all__ = ["build_shadow_record"]
