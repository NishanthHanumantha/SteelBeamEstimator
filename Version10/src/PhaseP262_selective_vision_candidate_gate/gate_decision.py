"""Assemble VisionGateDecision records from production features + rules."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .config import GATE_VERSION
from .gate_features import extract_gate_features
from .gate_rules import decide_gate


def build_gate_decision(
    *,
    beam_id: str,
    region_id: str,
    rec: Dict[str, Any],
    model: Optional[Dict[str, Any]],
    association: str = "TARGET_BEAM",
    set_key: str = "",
    source_set: str = "",
    crop_path: Optional[str] = None,
) -> Dict[str, Any]:
    assoc = str(
        association
        or rec.get("beam_association")
        or rec.get("association")
        or "TARGET_BEAM"
    ).upper()
    feat = extract_gate_features(
        beam_id=beam_id, rec=rec, model=model, association=assoc
    )
    ruled = decide_gate(feat)
    return {
        "beam_id": beam_id,
        "region_id": region_id,
        "set_key": set_key,
        "source_set": source_set,
        "decision": ruled["decision"],
        "priority": ruled["priority"],
        "reason_codes": ruled["reason_codes"],
        "production_features": {
            k: feat[k]
            for k in feat
            if k not in ("score_beam_reasons", "r13_summary")
        },
        "evidence_strength": ruled["evidence_strength"],
        "candidate_class_hint": ruled["candidate_class_hint"],
        "deterministic_object_count": feat["deterministic_object_count"],
        "annotation_count": feat["annotation_count"],
        "matching_object_count": feat["matching_object_count"],
        "incomplete_parse_count": feat["incomplete_parse_count"],
        "OCR_corruption_count": feat["OCR_corruption_count"],
        "unassociated_annotation_count": feat["unassociated_annotation_count"],
        "gate_version": GATE_VERSION,
        "crop_path": crop_path,
    }


__all__ = ["build_gate_decision"]
