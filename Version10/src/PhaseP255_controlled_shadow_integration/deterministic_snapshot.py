"""
Capture the real P2.5.1 QuantityIntent BEFORE Claude is consulted.

This is the production deterministic authority for the experiment.
Do not invent a parallel parser.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, Optional

from PhaseP251_quantity_intent_schema.config import (
    STATUS_COMPOSITE,
    STATUS_EXPLICIT,
    STATUS_SPACING_BASED,
)
from PhaseP251_quantity_intent_schema.intent_builder import build_intent_for_annotation
from PhaseP251_quantity_intent_schema.models import QuantityIntent
from PhaseP254_semantic_reinforcement_vision_benchmark.candidate_loader import (
    load_p250_evidence,
)

RESOLVED_STATUSES = {STATUS_EXPLICIT, STATUS_SPACING_BASED, STATUS_COMPOSITE}


def _find_annotation(evidence: Dict[str, Any], annotation_id: str) -> Optional[Dict[str, Any]]:
    for ann in evidence.get("annotations") or []:
        if str(ann.get("annotation_id") or "") == annotation_id:
            return ann
    return None


def intent_to_snapshot(intent: QuantityIntent) -> Dict[str, Any]:
    """Immutable dict of deterministic fields used by the shadow contract."""
    return {
        "deterministic_result": copy.deepcopy(intent.to_dict()),
        "deterministic_status": intent.quantity_status,
        "deterministic_type": intent.semantic_type,
        "deterministic_role": intent.reinforcement_role,
        "deterministic_diameter": intent.diameter_value_mm,
        "deterministic_quantity": intent.quantity_value,
        "deterministic_legs": intent.leg_count,
        "deterministic_spacing": list(intent.spacing_values_mm or []),
        "deterministic_association": "TARGET_BEAM",
        "deterministic_zone": None,
        "deterministic_resolved": intent.quantity_status in RESOLVED_STATUSES,
        "deterministic_type_resolved": intent.semantic_type not in (None, "", "UNKNOWN"),
        "deterministic_role_resolved": intent.reinforcement_role not in (None, "", "UNKNOWN"),
        "intent_id": intent.intent_id,
        "raw_text": intent.raw_text,
        "normalized_text": intent.normalized_text,
    }


def snapshot_from_frozen_intent(row: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback snapshot from the frozen P2.5.1 matrix (still a real pipeline artefact)."""
    st = row.get("quantity_status")
    return {
        "deterministic_result": copy.deepcopy(row),
        "deterministic_status": st,
        "deterministic_type": row.get("semantic_type"),
        "deterministic_role": row.get("reinforcement_role"),
        "deterministic_diameter": row.get("diameter_value_mm"),
        "deterministic_quantity": row.get("quantity_value"),
        "deterministic_legs": row.get("leg_count"),
        "deterministic_spacing": list(row.get("spacing_values_mm") or []),
        "deterministic_association": "TARGET_BEAM",
        "deterministic_zone": None,
        "deterministic_resolved": st in RESOLVED_STATUSES,
        "deterministic_type_resolved": row.get("semantic_type") not in (None, "", "UNKNOWN"),
        "deterministic_role_resolved": row.get("reinforcement_role") not in (None, "", "UNKNOWN"),
        "intent_id": row.get("intent_id"),
        "raw_text": row.get("raw_text"),
        "normalized_text": row.get("normalized_text"),
    }


def capture_deterministic(
    *,
    version10_root,
    beam_id: str,
    annotation_id: str,
    frozen_intent: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run the real P2.5.1 entry point. Compare to the frozen matrix when provided.
    Never mutates the intent after return — callers must treat the snapshot as immutable.
    """
    evidence = load_p250_evidence(version10_root, beam_id)
    live_intent = None
    if evidence is not None:
        ann = _find_annotation(evidence, annotation_id)
        if ann is not None:
            live_intent = build_intent_for_annotation(
                beam_id=beam_id,
                annotation=ann,
                evidence=evidence,
            )
    if live_intent is None:
        if frozen_intent is None:
            raise FileNotFoundError(
                f"No P2.5.1 intent for {beam_id}/{annotation_id} and no frozen fallback"
            )
        snap = snapshot_from_frozen_intent(frozen_intent)
        snap["snapshot_source"] = "FROZEN_P251_MATRIX"
        snap["matches_frozen_matrix"] = True
        return snap

    snap = intent_to_snapshot(live_intent)
    snap["snapshot_source"] = "P251_BUILD_INTENT_FOR_ANNOTATION"
    if frozen_intent is not None:
        snap["matches_frozen_matrix"] = _matches_frozen(snap, frozen_intent)
    else:
        snap["matches_frozen_matrix"] = None
    return snap


def _matches_frozen(snap: Dict[str, Any], frozen: Dict[str, Any]) -> bool:
    checks = [
        (snap.get("deterministic_type"), frozen.get("semantic_type")),
        (snap.get("deterministic_role"), frozen.get("reinforcement_role")),
        (snap.get("deterministic_status"), frozen.get("quantity_status")),
        (snap.get("deterministic_quantity"), frozen.get("quantity_value")),
        (snap.get("deterministic_diameter"), frozen.get("diameter_value_mm")),
        (snap.get("deterministic_legs"), frozen.get("leg_count")),
        (list(snap.get("deterministic_spacing") or []), list(frozen.get("spacing_values_mm") or [])),
    ]
    return all(a == b for a, b in checks)


__all__ = [
    "RESOLVED_STATUSES",
    "capture_deterministic",
    "intent_to_snapshot",
    "snapshot_from_frozen_intent",
]
