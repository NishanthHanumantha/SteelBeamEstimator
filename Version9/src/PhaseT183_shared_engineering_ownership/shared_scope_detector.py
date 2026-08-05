"""
T1.8.3 — Detect shared-capable engineering annotations (SFR).
MODEL_VERSION: 9.5.3

Reuses T1.7 classify_annotation_text — no duplicated parsing rules.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from PhaseT17_annotation_graph.semantic_classifier import classify_annotation_text

MODEL_VERSION = "9.5.3"


class EngineeringScopeType(str, Enum):
    SIDE_FACE_REINFORCEMENT = "SIDE_FACE_REINFORCEMENT"
    # Future (declared, not assigned in 9.5.3)
    DEVELOPMENT_LENGTH = "DEVELOPMENT_LENGTH"
    CONTINUATION_REINFORCEMENT = "CONTINUATION_REINFORCEMENT"
    CURTAILMENT = "CURTAILMENT"
    SUPPORT_REINFORCEMENT = "SUPPORT_REINFORCEMENT"
    SHARED_BARS = "SHARED_BARS"


def _scope_type_from_semantic(sem: Dict[str, Any]) -> Optional[EngineeringScopeType]:
    st = str(sem.get("semantic_type") or "")
    meaning = str(sem.get("engineering_meaning") or "")
    if st == "SideFaceReinforcement" or meaning == "SIDE_FACE_REINFORCEMENT":
        return EngineeringScopeType.SIDE_FACE_REINFORCEMENT
    return None


def is_side_face_text(text: str) -> bool:
    sem = classify_annotation_text(text or "")
    return _scope_type_from_semantic(sem) == EngineeringScopeType.SIDE_FACE_REINFORCEMENT


def detect_shared_candidates(
    *,
    graph: Dict[str, Any],
    ownership_by_beam: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Find annotations that may participate in multi-beam engineering scope.
    T1.8.3: SIDE_FACE_REINFORCEMENT only.
    """
    nodes = {n["id"]: n for n in (graph.get("nodes") or [])}
    edges = list(graph.get("edges") or [])
    out_edges: Dict[str, List[Dict[str, Any]]] = {}
    for e in edges:
        out_edges.setdefault(e["source_id"], []).append(e)

    # Index accepted annotation ids per beam (from T1.8 — read only)
    accepted_ids: Dict[str, set] = {}
    accepted_texts: Dict[str, List[str]] = {}
    for bid, own in (ownership_by_beam or {}).items():
        ids = set()
        texts = []
        for a in own.get("accepted_annotations") or []:
            if a.get("id"):
                ids.add(a["id"])
            texts.append(str(a.get("text") or ""))
        accepted_ids[str(bid)] = ids
        accepted_texts[str(bid)] = texts

    found: List[Dict[str, Any]] = []
    seen = set()

    for n in nodes.values():
        if n.get("type") != "Annotation":
            continue
        attrs = n.get("attributes") or {}
        text = str(attrs.get("clean_text") or "")
        sem = classify_annotation_text(text, r1_role=attrs.get("r1_role"))
        scope_type = _scope_type_from_semantic(sem)
        if scope_type is None:
            continue
        # Only SFR in this phase
        if scope_type != EngineeringScopeType.SIDE_FACE_REINFORCEMENT:
            continue

        aid = n["id"]
        if aid in seen:
            continue
        seen.add(aid)

        primary = str(n.get("beam_id") or "")
        leaders = []
        for e in out_edges.get(aid, []):
            if e.get("type") == "ATTACHED_TO":
                leaders.append(e["target_id"])

        leader_tips = []
        for lid in leaders:
            L = nodes.get(lid) or {}
            la = L.get("attributes") or {}
            try:
                leader_tips.append(
                    {
                        "leader_id": lid,
                        "tip_x": float(la["tip_x"]),
                        "tip_y": float(la["tip_y"]),
                        "tail_x": float(la.get("tail_x")),
                        "tail_y": float(la.get("tail_y")),
                    }
                )
            except Exception:
                continue

        found.append(
            {
                "annotation_id": aid,
                "annotation_text": text,
                "primary_beam": primary,
                "scope_type": scope_type.value,
                "leader_ids": leaders,
                "leader_tips": leader_tips,
                "x": attrs.get("x"),
                "y": attrs.get("y"),
                "accepted_on_primary": aid in accepted_ids.get(primary, set()),
                "semantic": sem,
                "node": n,
            }
        )

    return found
