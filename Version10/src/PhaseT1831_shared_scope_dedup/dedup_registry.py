"""
T1.8.3.1 — Rebuild SharedAnnotationRegistry from deduplicated scopes.
MODEL_VERSION: 9.5.4
"""
from __future__ import annotations

from typing import Any, Dict, List

from PhaseT183_shared_engineering_ownership.multi_owner_assignment import (
    SharedEngineeringAnnotation,
    assign_multi_owners,
)
from PhaseT183_shared_engineering_ownership.shared_annotation_registry import (
    build_registry,
)

MODEL_VERSION = "9.5.4"


def rebuild_registry_from_scopes(
    scopes: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Assign multi-owners from deduplicated scopes, then build registry.
    Guarantees one SharedEngineeringAnnotation per surviving shared scope
    (member_annotations kept canonical / singular by the deduplicator).
    """
    shared_anns = assign_multi_owners(scopes, candidates)
    reg = build_registry(shared_anns)
    reg["model_version"] = MODEL_VERSION
    reg["deduplicated"] = True
    reg["phase_id"] = "T1.8.3.1"
    return reg, shared_anns


def registry_sfr_entries(registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for aid, d in (registry.get("by_annotation") or {}).items():
        text = str(d.get("annotation_text") or "").upper()
        if "SIDE FACE" in text or "SIDE.FACE" in text:
            out.append(d)
    return out
