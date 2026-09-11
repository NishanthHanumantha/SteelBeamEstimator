"""Semantic comparison at the Hybrid authority boundary. No weights / BBS / cut length."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .paths import ensure_src_on_path

ensure_src_on_path()

from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.normalize import (
    map_layer,
    normalize_spec,
    parse_bar_count,
    parse_diameter,
)

from .config import (
    AGREE,
    BENIGN_DIFFERENCE,
    HYBRID_ERROR,
    HYBRID_UNAVAILABLE,
    MATERIAL_DISAGREEMENT,
    SEMANTIC_DISAGREEMENT,
)

_EMPTY = (None, "", "UNKNOWN")
_RANK = {
    AGREE: 0,
    BENIGN_DIFFERENCE: 1,
    SEMANTIC_DISAGREEMENT: 2,
    MATERIAL_DISAGREEMENT: 3,
    HYBRID_UNAVAILABLE: 4,
    HYBRID_ERROR: 5,
}


def _present(value: Any) -> bool:
    return value not in _EMPTY


def _norm_role(value: Any) -> Optional[str]:
    if not _present(value):
        return None
    role = str(value).strip().upper()
    if role in ("MAIN", "EXTRA"):
        return role
    if role in ("UNKNOWN",):
        return None
    return role


def _norm_scope(value: Any) -> Optional[str]:
    if not _present(value):
        return None
    return str(value).strip().upper()


def _field_pair(rec: Optional[Dict[str, Any]]) -> Tuple[Any, Any]:
    rec = rec or {}
    return rec.get("vision_value"), rec.get("deterministic_value")


def classify_field(
    *,
    name: str,
    vision_value: Any,
    deterministic_value: Any,
) -> Dict[str, Any]:
    vis_raw, det_raw = vision_value, deterministic_value
    if name == "layer":
        vis = map_layer(vis_raw) if _present(vis_raw) else None
        det = map_layer(det_raw) if _present(det_raw) else None
        if vis == "UNKNOWN":
            vis = None
        if det == "UNKNOWN":
            det = None
    elif name == "specification":
        vis = normalize_spec(vis_raw) if _present(vis_raw) else None
        det = normalize_spec(det_raw) if _present(det_raw) else None
        vis = vis or None
        det = det or None
    elif name == "bar_count":
        vis = parse_bar_count(vis_raw, vis_raw)
        det = parse_bar_count(det_raw, det_raw)
    elif name == "diameter":
        vis = parse_diameter(vis_raw, vis_raw)
        det = parse_diameter(det_raw, det_raw)
    elif name in ("role", "main_extra"):
        vis = _norm_role(vis_raw)
        det = _norm_role(det_raw)
    elif name == "support_scope":
        vis = _norm_scope(vis_raw)
        det = _norm_scope(det_raw)
        if vis == "UNKNOWN":
            vis = None
        if det == "UNKNOWN":
            det = None
    else:
        vis = vis_raw if _present(vis_raw) else None
        det = det_raw if _present(det_raw) else None

    if vis is None and det is None:
        return {"field": name, "classification": AGREE, "vision": vis_raw, "deterministic": det_raw}
    if vis is None or det is None:
        return {
            "field": name,
            "classification": BENIGN_DIFFERENCE,
            "vision": vis_raw,
            "deterministic": det_raw,
            "reason": "ONE_SIDE_UNKNOWN",
        }
    if vis == det:
        return {"field": name, "classification": AGREE, "vision": vis_raw, "deterministic": det_raw}

    material_fields = {"bar_count", "diameter"}
    if name in material_fields:
        return {
            "field": name,
            "classification": MATERIAL_DISAGREEMENT,
            "vision": vis_raw,
            "deterministic": det_raw,
            "normalized_vision": vis,
            "normalized_deterministic": det,
        }
    if name == "specification":
        vis_count = parse_bar_count(vis_raw, None)
        det_count = parse_bar_count(det_raw, None)
        vis_dia = parse_diameter(vis_raw, None)
        det_dia = parse_diameter(det_raw, None)
        if (
            vis_count is not None
            and det_count is not None
            and vis_count != det_count
        ) or (
            vis_dia is not None
            and det_dia is not None
            and vis_dia != det_dia
        ):
            return {
                "field": name,
                "classification": MATERIAL_DISAGREEMENT,
                "vision": vis_raw,
                "deterministic": det_raw,
            }
        return {
            "field": name,
            "classification": BENIGN_DIFFERENCE,
            "vision": vis_raw,
            "deterministic": det_raw,
            "reason": "SPEC_TEXT_ONLY",
        }
    return {
        "field": name,
        "classification": SEMANTIC_DISAGREEMENT,
        "vision": vis_raw,
        "deterministic": det_raw,
        "normalized_vision": vis,
        "normalized_deterministic": det,
    }


def worst(*classes: str) -> str:
    ranked = [c for c in classes if c in _RANK]
    if not ranked:
        return AGREE
    return max(ranked, key=lambda c: _RANK[c])


def classify_group(group: Dict[str, Any]) -> Dict[str, Any]:
    origin = str(group.get("origin") or "")
    fields = []
    for name in ("layer", "bar_count", "diameter", "specification", "role", "support_scope"):
        rec = group.get(name) if isinstance(group.get(name), dict) else {}
        vis, det = _field_pair(rec)
        fields.append(classify_field(name=name, vision_value=vis, deterministic_value=det))
    if origin == "VISION_ONLY_GROUP":
        cls = SEMANTIC_DISAGREEMENT
        count = classify_field(
            name="bar_count",
            vision_value=(group.get("bar_count") or {}).get("vision_value"),
            deterministic_value=None,
        )
        dia = classify_field(
            name="diameter",
            vision_value=(group.get("diameter") or {}).get("vision_value"),
            deterministic_value=None,
        )
        if _present((group.get("bar_count") or {}).get("vision_value")) or _present(
            (group.get("diameter") or {}).get("vision_value")
        ):
            cls = SEMANTIC_DISAGREEMENT
        reason = "VISION_ONLY_GROUP"
    elif origin == "DETERMINISTIC_ONLY_GROUP":
        cls = SEMANTIC_DISAGREEMENT
        reason = "DETERMINISTIC_ONLY_GROUP"
    else:
        cls = worst(*(f["classification"] for f in fields))
        reason = origin or "MATCHED"
    return {
        "group_id": group.get("group_id"),
        "origin": origin,
        "classification": cls,
        "reason": reason,
        "fields": fields,
    }


def classify_stirrup(item: Dict[str, Any]) -> Dict[str, Any]:
    ident = item.get("semantic_identification") if isinstance(item.get("semantic_identification"), dict) else {}
    field = classify_field(
        name="specification",
        vision_value=ident.get("vision_value"),
        deterministic_value=ident.get("deterministic_value"),
    )
    origin = str(item.get("origin") or "")
    if origin == "VISION_ONLY_GROUP" or origin.endswith("VISION_ONLY"):
        cls = SEMANTIC_DISAGREEMENT
    elif origin == "DETERMINISTIC_ONLY_GROUP" or origin.endswith("DETERMINISTIC_ONLY"):
        cls = BENIGN_DIFFERENCE if field["classification"] in (AGREE, BENIGN_DIFFERENCE) else SEMANTIC_DISAGREEMENT
    else:
        cls = field["classification"]
        if cls == MATERIAL_DISAGREEMENT:
            cls = SEMANTIC_DISAGREEMENT
    return {
        "origin": origin,
        "classification": cls,
        "field": field,
    }


def classify_beam(
    *,
    beam_id: str,
    hybrid: Optional[Dict[str, Any]],
    status: str,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    if status == HYBRID_ERROR or error:
        return {
            "beam_id": beam_id,
            "agreement_classification": HYBRID_ERROR,
            "error": error,
            "groups": [],
            "stirrups": [],
        }
    if status == HYBRID_UNAVAILABLE or not isinstance(hybrid, dict):
        return {
            "beam_id": beam_id,
            "agreement_classification": HYBRID_UNAVAILABLE,
            "groups": [],
            "stirrups": [],
        }
    groups = [classify_group(g) for g in (hybrid.get("reinforcement_groups") or []) if isinstance(g, dict)]
    stirrups_wrap = hybrid.get("stirrups") or {}
    stirrup_items = stirrups_wrap.get("items") if isinstance(stirrups_wrap, dict) else stirrups_wrap
    stirrups = [classify_stirrup(s) for s in (stirrup_items or []) if isinstance(s, dict)]
    cls = worst(
        *(g["classification"] for g in groups),
        *(s["classification"] for s in stirrups),
    )
    matching = hybrid.get("group_matching") or {}
    if int(matching.get("ambiguous") or 0) > 0:
        cls = worst(cls, SEMANTIC_DISAGREEMENT)
    return {
        "beam_id": beam_id,
        "agreement_classification": cls or AGREE,
        "groups": groups,
        "stirrups": stirrups,
        "matching": {
            "matched": matching.get("matched"),
            "vision_only": matching.get("vision_only"),
            "deterministic_only": matching.get("deterministic_only"),
            "ambiguous": matching.get("ambiguous"),
        },
    }


def summarize_classifications(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {
        AGREE: 0,
        BENIGN_DIFFERENCE: 0,
        SEMANTIC_DISAGREEMENT: 0,
        MATERIAL_DISAGREEMENT: 0,
        HYBRID_UNAVAILABLE: 0,
        HYBRID_ERROR: 0,
    }
    for row in rows:
        key = str(row.get("agreement_classification") or HYBRID_UNAVAILABLE)
        if key not in counts:
            counts[key] = 0
        counts[key] += 1
    counts["comparisons"] = len(rows)
    return counts
