"""
T1.8.3 — Assign SharedEngineeringAnnotation → many beams.
MODEL_VERSION: 9.5.3
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

MODEL_VERSION = "9.5.3"


@dataclass
class SharedEngineeringAnnotation:
    annotation_id: str
    annotation_text: str
    leader_ids: List[str]
    scope_type: str
    owner_beams: List[str]
    confidence: float
    reason: str
    scope_id: str
    primary_beam: str
    shared: bool = True
    model_version: str = MODEL_VERSION
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


def assign_multi_owners(
    scopes: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
) -> List[SharedEngineeringAnnotation]:
    by_id = {c["annotation_id"]: c for c in candidates}
    out: List[SharedEngineeringAnnotation] = []
    for sc in scopes:
        if not sc.get("shared"):
            continue
        for aid in sc.get("member_annotations") or []:
            cand = by_id.get(aid) or {}
            out.append(
                SharedEngineeringAnnotation(
                    annotation_id=aid,
                    annotation_text=str(
                        sc.get("annotation_text")
                        or cand.get("annotation_text")
                        or ""
                    ),
                    leader_ids=list(cand.get("leader_ids") or []),
                    scope_type=str(sc.get("scope_type")),
                    owner_beams=list(sc.get("member_beams") or []),
                    confidence=float(sc.get("confidence") or 0.0),
                    reason=str(sc.get("reason") or ""),
                    scope_id=str(sc.get("scope_id")),
                    primary_beam=str(sc.get("primary_beam") or ""),
                    shared=True,
                    extra={
                        "rules_passed": sc.get("rules_passed") or [],
                        "x": cand.get("x"),
                        "y": cand.get("y"),
                    },
                )
            )
    return out
