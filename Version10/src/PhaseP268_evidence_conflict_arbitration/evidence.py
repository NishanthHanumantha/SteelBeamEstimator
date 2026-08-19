"""Normalize an EvidenceRecord from existing P2.6.4–P2.6.7 artefacts. No invented fields."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import (
    DET_ALREADY,
    DET_CONFLICT,
    DET_MISSING,
    LAYER_BOTTOM,
    LAYER_TOP,
    LAYER_UNKNOWN,
    PHYS_AMBIGUOUS,
    PHYS_DISTINCT,
    PHYS_DUPLICATE,
    PHYS_INSUFFICIENT,
    SEM_AMBIGUOUS,
    SEM_DISTINCT,
    SEM_DUPLICATE,
    SEM_UNUSABLE,
    SEM_UNSUPPORTED,
)
from .layer_resolver import resolve_candidate_layer


def _norm_spec(quantity: Any, diameter_mm: Any) -> Optional[str]:
    try:
        q = int(quantity)
        d = int(round(float(diameter_mm)))
    except (TypeError, ValueError):
        return None
    if q <= 0 or d <= 0:
        return None
    return f"{q}Y{d}"


def _first_ann(target: Dict[str, Any]) -> Dict[str, Any]:
    spatial = list(target.get("per_annotation_spatial") or [])
    if spatial:
        return dict(spatial[0])
    cov = list(target.get("per_annotation_coverage") or [])
    if cov:
        return dict(cov[0])
    ctx = (target.get("context") or {}).get("annotation_context") or []
    if ctx:
        return dict(ctx[0])
    return {}


def _frozen_rows(target: Dict[str, Any]) -> List[Dict[str, Any]]:
    ctx = target.get("context") or {}
    rows = list(ctx.get("frozen_vision_longitudinal_observations") or [])
    return [r for r in rows if isinstance(r, dict)]


def _existing_specs(target: Dict[str, Any]) -> List[Dict[str, Any]]:
    feat = target.get("production_features") or {}
    specs = list(feat.get("accepted_specs") or [])
    if specs:
        return specs
    det = (target.get("context") or {}).get("deterministic_reinforcement") or {}
    return list(det.get("accepted_specs") or [])


def _existing_on_layer(target: Dict[str, Any], layer: str) -> List[Dict[str, Any]]:
    det = (target.get("context") or {}).get("deterministic_reinforcement") or {}
    if layer == LAYER_TOP:
        return list(det.get("existing_top_reinforcement") or [])
    if layer == LAYER_BOTTOM:
        return list(det.get("existing_bottom_reinforcement") or [])
    if layer == "SIDE":
        return list(det.get("side_face_reinforcement") or [])
    return list(det.get("existing_longitudinal_objects") or [])


def _det_status(rows: List[Dict[str, Any]]) -> str:
    statuses = [str(r.get("deterministic_match_status") or "") for r in rows]
    if DET_MISSING in statuses:
        return DET_MISSING
    if DET_CONFLICT in statuses:
        return DET_CONFLICT
    if DET_ALREADY in statuses:
        return DET_ALREADY
    return ""


def _physical_identity(*, det_status: str, candidate_layer: str, populated_layer: str, represented_on_candidate_layer: bool) -> str:
    if det_status == DET_MISSING:
        return PHYS_DISTINCT
    if det_status == DET_ALREADY:
        return PHYS_DUPLICATE
    if det_status == DET_CONFLICT:
        return PHYS_AMBIGUOUS
    if (
        candidate_layer in (LAYER_TOP, LAYER_BOTTOM)
        and populated_layer in (LAYER_TOP, LAYER_BOTTOM)
        and candidate_layer != populated_layer
        and not represented_on_candidate_layer
    ):
        return PHYS_DISTINCT
    if (
        candidate_layer in (LAYER_TOP, LAYER_BOTTOM)
        and candidate_layer == populated_layer
        and represented_on_candidate_layer
    ):
        return PHYS_DUPLICATE
    return PHYS_INSUFFICIENT


def _semantic_from_p266(target: Dict[str, Any]) -> Dict[str, Any]:
    sem = dict(target.get("semantic") or {})
    decision = str(sem.get("decision") or "")
    if decision not in (SEM_DISTINCT, SEM_DUPLICATE, SEM_AMBIGUOUS, SEM_UNSUPPORTED):
        return {"decision": SEM_UNUSABLE, "usable": False, "source": "P266_MISSING"}
    return {
        "decision": decision,
        "confidence": sem.get("confidence"),
        "target_layer": sem.get("target_layer"),
        "existing_representation_assessment": sem.get("existing_representation_assessment"),
        "reason_codes": list(sem.get("semantic_reason_codes") or []),
        "source": sem.get("source") or "P266",
        "usable": True,
    }


def _semantic_from_p267(live: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(live, dict):
        return {"decision": SEM_UNUSABLE, "usable": False, "source": "P267_ABSENT"}
    prim = live.get("primary") or live
    if not prim.get("ok"):
        return {
            "decision": SEM_UNUSABLE,
            "usable": False,
            "source": prim.get("source") or "P267",
            "error_class": prim.get("error_class"),
        }
    payload = prim.get("payload") or {}
    decision = str(payload.get("decision") or prim.get("decision") or "")
    if decision not in (SEM_DISTINCT, SEM_DUPLICATE, SEM_AMBIGUOUS, SEM_UNSUPPORTED):
        return {"decision": SEM_UNUSABLE, "usable": False, "source": "P267_INVALID"}
    return {
        "decision": decision,
        "confidence": payload.get("confidence") if payload.get("confidence") is not None else prim.get("confidence"),
        "target_layer": payload.get("target_layer"),
        "existing_representation_assessment": payload.get("existing_representation_assessment"),
        "reason_codes": list(payload.get("reason_codes") or []),
        "source": prim.get("source") or "P267",
        "usable": True,
    }


def build_evidence_record(target: Dict[str, Any], *, live: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ann = _first_ann(target)
    frozen = _frozen_rows(target)
    feat = target.get("production_features") or {}
    spat = target.get("spatial_features") or {}
    det = (target.get("context") or {}).get("deterministic_reinforcement") or {}
    roles = det.get("role_assignments") or {}
    populated = str(roles.get("populated_layer") or feat.get("populated_layer") or spat.get("populated_layer") or "").upper()
    qty = ann.get("quantity")
    dia = ann.get("diameter_mm")
    cand_spec = _norm_spec(qty, dia)
    existing = _existing_specs(target)
    existing_specs = [_norm_spec(s.get("quantity"), s.get("diameter_mm")) for s in existing]
    existing_specs = [s for s in existing_specs if s]
    spec_match_any = bool(cand_spec and cand_spec in existing_specs)
    p266_sem = _semantic_from_p266(target)
    layer_info = resolve_candidate_layer(
        annotation=ann,
        p266_target_layer=(target.get("semantic") or {}).get("target_layer"),
        tip_votes=spat.get("tip_layer_votes"),
        frozen_role=(frozen[0].get("role") if frozen else None),
    )
    cand_layer = str(layer_info.get("resolved_layer") or LAYER_UNKNOWN)
    represented_on_cand = bool(_existing_on_layer(target, cand_layer))
    spec_match_same_layer = False
    if cand_spec and cand_layer in (LAYER_TOP, LAYER_BOTTOM):
        layer_bars = _existing_on_layer(target, cand_layer)
        layer_specs = [_norm_spec(b.get("quantity"), b.get("diameter_mm")) for b in layer_bars]
        spec_match_same_layer = cand_spec in [s for s in layer_specs if s]
    det_status = _det_status(frozen)
    physical = _physical_identity(
        det_status=det_status,
        candidate_layer=cand_layer,
        populated_layer=populated,
        represented_on_candidate_layer=represented_on_cand,
    )
    p267_sem = _semantic_from_p267(live)
    live_sem = p267_sem if p267_sem.get("usable") else p266_sem
    return {
        "candidate_id": (frozen[0].get("candidate_id") if frozen else None) or target.get("region_id"),
        "source_annotation_id": ann.get("ann_id"),
        "beam_id": target.get("beam_id"),
        "set_key": target.get("set_key"),
        "region_id": target.get("region_id"),
        "reinforcement_family": "LONGITUDINAL",
        "diameter": dia,
        "bar_count": qty,
        "spacing": None,
        "length": None,
        "semantic_role": ann.get("role") or (frozen[0].get("role") if frozen else None),
        "physical_target_hint": physical,
        "layer_hint": cand_layer,
        "z": None,
        "spatial_position": {
            "position_zone": ann.get("position_zone"),
            "tip_in_top_zone": ann.get("tip_in_top_zone"),
            "tip_in_bottom_zone": ann.get("tip_in_bottom_zone"),
            "leader_tip_direction": ann.get("leader_tip_direction"),
            "leader_association": ann.get("leader_association"),
        },
        "leader_association": ann.get("leader_association"),
        "source_layer": None,
        "text_representation": ann.get("text") or ann.get("normalized_text"),
        "normalized_specification": cand_spec,
        "deterministic_identity": {
            "match_status": det_status or None,
            "physical": physical,
            "populated_layer": populated or LAYER_UNKNOWN,
            "represented_on_candidate_layer": represented_on_cand,
            "has_top": roles.get("has_top") if "has_top" in roles else feat.get("has_top"),
            "has_bottom": roles.get("has_bottom") if "has_bottom" in roles else feat.get("has_bottom"),
            "existing_specs": existing_specs,
        },
        "semantic_identity": live_sem,
        "p266_semantic": p266_sem,
        "p267_semantic": p267_sem,
        "provenance": {
            "observed_decision": target.get("observed_decision") or target.get("decision"),
            "p265_context_status": target.get("context_status") or target.get("p265_context_status"),
            "p265_evidence_codes": list(target.get("context_evidence_codes") or []),
            "longitudinal_coverage": target.get("longitudinal_coverage"),
        },
        "evidence_quality": {
            "leader_geometry_available": bool(spat.get("leader_geometry_available")),
            "physical_bar_geometry_available": bool(spat.get("physical_bar_geometry_available")),
            "annotation_xy_available": bool(spat.get("annotation_xy_available")),
            "layer_evidence_incomplete": bool(layer_info.get("layer_evidence_incomplete")),
        },
        "layer": layer_info,
        "spec_match_any_layer": spec_match_any,
        "spec_match_same_layer": spec_match_same_layer,
        "production_routing_changed": False,
    }


__all__ = ["build_evidence_record"]
