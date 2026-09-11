"""
annotation_builder.py — Build annotation JSON from deterministic pipeline outputs.

Labels come exclusively from the engineering pipeline (R.1 / R.1.3).
No manual annotation.  No AI inference.  No invented labels.

Priority for annotation data:
  1. beam_reinforcement_models_production.json  (R.1.3) — richest, role-assigned bars.
  2. reinforcement_annotations.json            (R.1)   — raw, classified annotations.

Every annotation entry includes full engineering traceability:
  source_phase, source_object, engineering_confidence.

MODEL_VERSION: 9.0.0
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "9.0.0"
SCHEMA_VERSION = "M.1.0"

# ── Canonical role → display name ────────────────────────────────────────────
ROLE_DISPLAY: Dict[str, str] = {
    "TOP_MAIN":                "Top Main",
    "BOTTOM_MAIN":             "Bottom Main",
    "TOP_EXTRA":               "Top Extra",
    "BOTTOM_EXTRA":            "Bottom Extra",
    "STIRRUP":                 "Stirrup",
    "SIDE_FACE_REINFORCEMENT": "Side Face",
    "SPACER_BAR":              "Spacer",
    "DEVELOPMENT":             "Development",
    "LAP":                     "Lap",
    "BENT_UP":                 "Bent Up",
    "ANCHORAGE":               "Anchorage",
    "UNKNOWN":                 "Unknown",
}

# ── R.1.3 bar-role field names → canonical role ──────────────────────────────
_PROD_FIELD_ROLES: Dict[str, str] = {
    "top_main_bars":     "TOP_MAIN",
    "bottom_main_bars":  "BOTTOM_MAIN",
    "top_extra_bars":    "TOP_EXTRA",
    "bottom_extra_bars": "BOTTOM_EXTRA",
    "stirrups":          "STIRRUP",
    "side_face_bars":    "SIDE_FACE_REINFORCEMENT",
    "development_bars":  "DEVELOPMENT",
    "lap_bars":          "LAP",
}


def _normalise_confidence(raw: Any) -> float:
    """Normalise any confidence representation to a float in [0.0, 1.0]."""
    if isinstance(raw, (float, int)):
        return float(min(1.0, max(0.0, raw)))
    if isinstance(raw, str):
        return {"HIGH": 0.95, "MEDIUM": 0.75, "LOW": 0.50, "UNKNOWN": 0.0}.get(
            raw.upper(), 0.5
        )
    return 0.5


def _position_dxf(ann: Dict[str, Any]) -> List[float]:
    return [float(ann.get("x") or 0.0), float(ann.get("y") or 0.0)]


# ── R.1 raw annotation builder ────────────────────────────────────────────────

def _from_r1_annotations(
    beam_id:  str,
    ann_list: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build annotation list from reinforcement_annotations.json (Phase R.1).
    Includes all entries flagged is_reinforcement=True plus classified ones.
    """
    result = []
    for ann in ann_list:
        if not isinstance(ann, dict):
            continue
        text = ann.get("clean_text") or ann.get("raw_text") or ""
        if not text:
            continue
        role = ann.get("role") or "UNKNOWN"
        result.append({
            "annotation_id":         ann.get("annotation_id") or "",
            "text":                  text,
            "role":                  role,
            "role_display":          ROLE_DISPLAY.get(role, role),
            "quantity":              int(ann.get("quantity")   or 0),
            "diameter_mm":           float(ann.get("diameter_mm") or 0.0),
            "steel_grade":           ann.get("steel_grade") or "Y460",
            "spacing_mm":            ann.get("spacing_mm"),
            "position_dxf":          _position_dxf(ann),
            "position_zone":         ann.get("position_zone") or "UNKNOWN_ZONE",
            "is_reinforcement":      bool(ann.get("is_reinforcement", False)),
            "source":                "Deterministic",
            "source_phase":          "R.1",
            "source_object":         (
                f"reinforcement_annotations.json"
                f"::{beam_id}"
                f"::{ann.get('annotation_id', '')}"
            ),
            "engineering_confidence": _normalise_confidence(
                ann.get("association_confidence")
                or ann.get("confidence")
                or "LOW"
            ),
        })
    return result


# ── R.1.3 production bar builder ──────────────────────────────────────────────

def _from_prod_bars(
    beam_id:    str,
    prod_entry: Dict[str, Any],
    ann_lookup: Dict[str, Dict[str, Any]],   # annotation_id → R.1 annotation dict
) -> List[Dict[str, Any]]:
    """
    Build annotation list from beam_reinforcement_models_production.json (R.1.3).
    Enriches bar records with DXF positions from the R.1 annotation lookup.
    """
    result = []
    for field, role in _PROD_FIELD_ROLES.items():
        bars = prod_entry.get(field) or []
        if isinstance(bars, dict):
            bars = [bars]
        for bar in bars:
            if not isinstance(bar, dict):
                continue
            ann_id  = (bar.get("annotation_id")
                       or bar.get("source_annotation_id") or "")
            raw_ann = ann_lookup.get(ann_id) or {}
            text    = (
                bar.get("label")
                or bar.get("bar_label")
                or raw_ann.get("clean_text")
                or raw_ann.get("raw_text")
                or ""
            )
            pos = _position_dxf(raw_ann) if raw_ann else [
                float(bar.get("dxf_x") or 0.0),
                float(bar.get("dxf_y") or 0.0),
            ]
            result.append({
                "annotation_id":         ann_id or bar.get("bar_id") or "",
                "text":                  text,
                "role":                  role,
                "role_display":          ROLE_DISPLAY.get(role, role),
                "quantity":              int(
                    bar.get("quantity")
                    or raw_ann.get("quantity") or 0
                ),
                "diameter_mm":           float(
                    bar.get("diameter_mm")
                    or raw_ann.get("diameter_mm") or 0.0
                ),
                "steel_grade":           (
                    bar.get("steel_grade")
                    or raw_ann.get("steel_grade") or "Y460"
                ),
                "spacing_mm":            (
                    bar.get("spacing_mm") or raw_ann.get("spacing_mm")
                ),
                "position_dxf":          pos,
                "position_zone":         bar.get("position_zone") or "UNKNOWN_ZONE",
                "is_reinforcement":      True,
                "source":                "Deterministic",
                "source_phase":          "R.1.3",
                "source_object":         (
                    f"beam_reinforcement_models_production.json"
                    f"::{beam_id}::{field}"
                ),
                "engineering_confidence": _normalise_confidence(
                    bar.get("confidence") or 0.95
                ),
            })
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def build_annotation_json(
    beam_id:      str,
    ann_list:     List[Dict[str, Any]],       # R.1 annotations for this beam
    prod_entry:   Optional[Dict[str, Any]],   # R.1.3 production model (may be None)
    dxf_bbox:     Tuple[float, float, float, float],
    pixel_bbox:   Tuple[int,   int,   int,   int  ],
    image_file:   str,
    drawing_file: str,
    transform:    Any,                         # CoordTransform | None
) -> Dict[str, Any]:
    """
    Build the complete annotation JSON for one beam image.

    Chooses R.1.3 production bars when available; falls back to R.1 annotations.
    Enriches every entry with pixel positions when a CoordTransform is provided.
    """
    # Index R.1 annotations for position lookup
    ann_lookup: Dict[str, Dict[str, Any]] = {}
    for a in ann_list:
        aid = a.get("annotation_id") or ""
        if aid:
            ann_lookup[aid] = a

    # Select data source
    if prod_entry:
        annotations = _from_prod_bars(beam_id, prod_entry, ann_lookup)
        data_source = "R.1.3_production"
        if not annotations:
            annotations = _from_r1_annotations(beam_id, ann_list)
            data_source = "R.1_annotations_fallback"
    else:
        annotations = _from_r1_annotations(beam_id, ann_list)
        data_source = "R.1_annotations"

    # Enrich with pixel positions
    if transform is not None:
        for ann in annotations:
            dx, dy = ann["position_dxf"]
            if dx != 0.0 or dy != 0.0:
                px, py = transform.dxf_to_pixel(dx, dy)
                ann["position_pixels"] = [px, py]

    return {
        "schema_version":       SCHEMA_VERSION,
        "model_version":        MODEL_VERSION,
        "beam_id":              beam_id,
        "drawing_file":         drawing_file,
        "image_file":           image_file,
        "bbox_dxf":             list(dxf_bbox),
        "bbox_pixels":          list(pixel_bbox),
        "annotation_count":     len(annotations),
        "data_source":          data_source,
        "annotations":          annotations,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
    }
