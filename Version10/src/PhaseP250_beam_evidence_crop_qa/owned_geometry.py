"""
Accepted OWN::* visual geometry for P2.5 evidence packages.
MODEL_VERSION: 10.6.2

Does NOT create PhysicalBars. Does NOT mutate T18/R.3.1.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import re

from .evidence_window import as_bbox

BBox = Tuple[float, float, float, float]

MODEL_VERSION = "10.6.2"


def _graph_nodes_by_id(graph: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(n.get("id")): n for n in (graph.get("nodes") or []) if n.get("id")}


def build_handle_index(msp: Any) -> Dict[str, Any]:
    """Map UPPER(handle) → entity once per DXF open."""
    idx: Dict[str, Any] = {}
    if msp is None:
        return idx
    for e in msp:
        try:
            idx[str(e.dxf.handle).upper()] = e
        except Exception:
            continue
    return idx


def _entity_geometry(e: Any) -> Optional[Dict[str, Any]]:
    if e is None:
        return None
    if e.dxftype() == "LWPOLYLINE":
        pts = [[float(p[0]), float(p[1])] for p in e.get_points("xy")]
        if not pts:
            return None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return {
            "entity_type": "LWPOLYLINE",
            "layer": str(e.dxf.layer),
            "points": pts,
            "bbox": [min(xs), min(ys), max(xs), max(ys)],
            "y_position": float(sum(ys) / len(ys)),
            "start_x": float(xs[0]),
            "end_x": float(xs[-1]),
        }
    if e.dxftype() == "LINE":
        s, en = e.dxf.start, e.dxf.end
        return {
            "entity_type": "LINE",
            "layer": str(e.dxf.layer),
            "points": [[float(s.x), float(s.y)], [float(en.x), float(en.y)]],
            "bbox": [
                min(float(s.x), float(en.x)),
                min(float(s.y), float(en.y)),
                max(float(s.x), float(en.x)),
                max(float(s.y), float(en.y)),
            ],
            "y_position": float((s.y + en.y) / 2.0),
            "start_x": float(s.x),
            "end_x": float(en.x),
        }
    return {"entity_type": e.dxftype(), "layer": str(e.dxf.layer), "found": True}


def _resolve_dxf_geometry(
    handle: str,
    *,
    handle_index: Optional[Dict[str, Any]] = None,
    msp: Any = None,
) -> Optional[Dict[str, Any]]:
    h = str(handle).upper()
    e = None
    if handle_index is not None:
        e = handle_index.get(h)
    elif msp is not None:
        for ent in msp:
            try:
                if str(ent.dxf.handle).upper() == h:
                    e = ent
                    break
            except Exception:
                continue
    return _entity_geometry(e)


def _chain_link_score(sem: str, text: str, role: str) -> int:
    """
    Prefer BarCallout / quantity-Y text when linking OWN::TOP_BAR.
    StirrupNote chains may incorrectly list the same OWN id — deprioritize them.
    """
    score = 0
    sem_u = (sem or "").strip()
    text_u = (text or "").upper().replace(" ", "")
    role_u = (role or "").upper()
    if sem_u == "BarCallout":
        score += 100
    elif sem_u == "StirrupNote":
        score -= 50
    if re.search(r"\d+\s*-?\s*Y\s*\d+", text or "", flags=re.I) and "@" not in text_u:
        score += 40
    if role_u == "TOP_BAR":
        score += 10
    return score


def collect_accepted_owned_geometry(
    *,
    beam_id: str,
    ownership: Dict[str, Any],
    annotation_graph: Dict[str, Any],
    msp: Any = None,
    handle_index: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    From accepted_chains describing OWN::* TOP_BAR via BarCallout,
    resolve actual DXF geometry. Visual evidence only — not PhysicalBars.
    """
    nodes = _graph_nodes_by_id(annotation_graph)
    # ownership_id -> best (score, record)
    best: Dict[str, Tuple[int, Dict[str, Any]]] = {}

    for ch in ownership.get("accepted_chains") or []:
        if not ch.get("accepted", True):
            continue
        aid = ch.get("annotation_id")
        text = ch.get("text") or ""
        leaders = list(ch.get("leaders") or [])
        leader_id = leaders[0] if leaders else None
        sem = str(ch.get("semantic_type") or "")
        for d in ch.get("describes") or []:
            did = str(d)
            if not did.startswith("OWN::"):
                continue
            gn = nodes.get(did) or {}
            attrs = gn.get("attributes") or {}
            role = str(attrs.get("role") or "").upper()

            # OWN TOP_BAR visual evidence must come from a bar callout chain.
            # StirrupNote may incorrectly list the same OWN id — skip those links.
            if role == "TOP_BAR":
                if sem and sem != "BarCallout":
                    # Allow only if no semantic typed, otherwise require BarCallout
                    continue
                if not sem:
                    # Untyped: require Y-bar quantity text without stirrup spacing
                    if not re.search(r"\d+\s*-?\s*Y\s*\d+", text or "", flags=re.I):
                        continue
                    if "@" in (text or "").upper():
                        continue
                evidence_type = "OWN_TOP_BAR"
                semantic_role = "TOP_BAR"
            elif sem == "BarCallout" and (not role or role in ("TOP_BAR", "BAR", "REINFORCEMENT")):
                evidence_type = "OWN_TOP_BAR" if (not role or role == "TOP_BAR") else f"OWN_{role}"
                semantic_role = role or "TOP_BAR"
            else:
                continue

            handle = str(attrs.get("handle") or did.split("::")[-1])
            geom = None
            if handle_index is not None or msp is not None:
                geom = _resolve_dxf_geometry(
                    handle, handle_index=handle_index, msp=msp
                )
            if geom is None:
                geom = {
                    "entity_type": attrs.get("entity_type") or "UNKNOWN",
                    "layer": attrs.get("layer"),
                    "points": None,
                    "bbox": None,
                    "y_position": None,
                    "dxf_resolved": False,
                }
            else:
                geom["dxf_resolved"] = True

            bb = as_bbox(geom.get("bbox") or [])
            evidence_id = f"OWNGEO::{beam_id}::{handle}"
            rec = {
                "evidence_id": evidence_id,
                "beam_id": beam_id,
                "ownership_id": did,
                "source_handle": handle,
                "entity_type": geom.get("entity_type"),
                "layer": geom.get("layer") or attrs.get("layer"),
                "geometry_type": geom.get("entity_type"),
                "geometry": {
                    "points": geom.get("points"),
                    "start_x": geom.get("start_x"),
                    "end_x": geom.get("end_x"),
                    "y_position": geom.get("y_position"),
                },
                "bbox": list(bb) if bb else None,
                "source": "T18.accepted_chains→AnnotationGraph.OwnedEntity→DXF",
                "reason": "accepted_semantic_owned_visual_evidence",
                "annotation_id": aid,
                "leader_id": leader_id,
                "annotation_text": text,
                "semantic_role": semantic_role,
                "accepted": True,
                "evidence_type": evidence_type,
                "dxf_resolved": bool(geom.get("dxf_resolved")),
                "t16_ownership": attrs.get("ownership"),
                "t16_confidence": attrs.get("confidence_score"),
                "chain_semantic_type": sem,
            }
            score = _chain_link_score(sem, text, role)
            prev = best.get(did)
            if prev is None or score > prev[0]:
                best[did] = (score, rec)

    # Deterministic order by ownership_id
    return [best[k][1] for k in sorted(best.keys())]


def owned_geometry_bboxes(items: Sequence[Dict[str, Any]]) -> List[BBox]:
    boxes: List[BBox] = []
    for it in items:
        bb = as_bbox(it.get("bbox") or [])
        if bb:
            boxes.append(bb)
    return boxes
