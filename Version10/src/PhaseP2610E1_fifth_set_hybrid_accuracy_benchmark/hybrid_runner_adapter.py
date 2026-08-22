"""Execute the current D.1–D.4 hybrid path. No Claude. No production writes."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.vision_normalizer import (
    extract_deterministic_groups,
    extract_vision_payload,
)
from PhaseP2610D2_shadow_hybrid_semantic_resolver.resolver import resolve_hybrid_beam
from PhaseP2610D3_hybrid_engineering_binding_compatibility.hybrid_binding_engine import bind_beam
from PhaseP2610D4_shadow_hybrid_engineering_calculation_accuracy_benchmark.beam_calculator import calculate_beam
from PhaseP269_reinforcement_group_interpretation.extractor import extract_detected_groups


def build_deterministic_payload(model: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    detected = extract_detected_groups(model if isinstance(model, dict) else {})
    return extract_deterministic_groups(detected)


def build_vision_payload(vision_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(vision_row, dict) or not vision_row.get("usable"):
        return extract_vision_payload(
            {
                "usable": False,
                "unusable_reason": (vision_row or {}).get("unusable_reason") or "VISION_UNAVAILABLE_OFFLINE",
                "target_identified": False,
                "groups": [],
                "stirrups": [],
            }
        )
    if isinstance(vision_row.get("extracted"), dict):
        return vision_row["extracted"]
    parsed = vision_row.get("parsed") if isinstance(vision_row.get("parsed"), dict) else {}
    return extract_vision_payload(parsed)


def execute_hybrid_beam(
    *,
    beam_id: str,
    model: Optional[Dict[str, Any]],
    vision_row: Optional[Dict[str, Any]],
    catalog: Dict[str, Any],
) -> Dict[str, Any]:
    vision = build_vision_payload(vision_row)
    deterministic = build_deterministic_payload(model)
    vision_used = bool(vision.get("usable") and (vision.get("groups") or vision.get("stirrups") or vision.get("target_identified")))
    provenance_kind = "HYBRID" if vision_used else "FALLBACK"
    hybrid = resolve_hybrid_beam(
        beam_id=beam_id,
        vision=vision,
        deterministic=deterministic,
        source_provenance={
            "kind": provenance_kind,
            "vision_used": vision_used,
            "vision_source": (vision_row or {}).get("source"),
            "mode": "OFFLINE_REPLAY",
        },
    )
    bound = bind_beam(hybrid=hybrid, catalog=catalog)
    calc = calculate_beam(bound=bound, r13_model=model or {})
    calc["provenance_kind"] = provenance_kind
    calc["vision_used"] = vision_used
    calc["hybrid_semantic"] = hybrid
    calc["engineering_bindings"] = bound
    return calc


def execute_population(
    *,
    beam_ids: List[str],
    catalog: Dict[str, Any],
    vision_by_id: Dict[str, Any],
) -> List[Dict[str, Any]]:
    rows = []
    for bid in beam_ids:
        model = catalog.get(bid)
        rows.append(
            execute_hybrid_beam(
                beam_id=bid,
                model=model if isinstance(model, dict) else None,
                vision_row=vision_by_id.get(bid),
                catalog=catalog,
            )
        )
    rows.sort(key=lambda r: str(r.get("beam_id") or ""))
    return rows


__all__ = ["build_deterministic_payload", "build_vision_payload", "execute_hybrid_beam", "execute_population"]
