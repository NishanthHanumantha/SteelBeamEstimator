"""
T1.8.3 — Registry of shared annotations indexed by beam.
MODEL_VERSION: 9.5.3
"""
from __future__ import annotations

from typing import Any, Dict, List

from .multi_owner_assignment import SharedEngineeringAnnotation

MODEL_VERSION = "9.5.3"


def build_registry(
    shared_anns: List[SharedEngineeringAnnotation],
) -> Dict[str, Any]:
    by_beam: Dict[str, List[Dict[str, Any]]] = {}
    by_ann: Dict[str, Dict[str, Any]] = {}
    for sa in shared_anns:
        d = sa.to_dict()
        by_ann[sa.annotation_id] = d
        for bid in sa.owner_beams:
            by_beam.setdefault(bid, []).append(d)
    return {
        "model_version": MODEL_VERSION,
        "shared_annotation_count": len(shared_anns),
        "by_annotation": by_ann,
        "by_beam": by_beam,
    }
