"""
metadata_builder.py — Build per-beam metadata for the vision dataset.

Metadata supports future benchmarking, filtering, and dataset statistics.
Each beam's metadata record is self-contained and traceable to its source.

MODEL_VERSION: 9.0.0
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "9.0.0"
SCHEMA_VERSION = "M.1.0"


def build_beam_metadata(
    beam_id:         str,
    beam_entry:      Dict[str, Any],
    axis_entry:      Optional[Dict[str, Any]],
    annotation_json: Dict[str, Any],
    image_file:      str,
    drawing_file:    str,
    dxf_source:      str,
    dxf_bbox:        Optional[Tuple[float, float, float, float]],
    pixel_bbox:      Optional[Tuple[int,   int,   int,   int  ]],
    image_size_px:   Optional[Tuple[int, int]],
) -> Dict[str, Any]:
    """
    Build the metadata record for one beam.

    Parameters
    ----------
    beam_entry      : entry from beam_registry.json
    axis_entry      : entry from BeamAxis.json (may be None)
    annotation_json : output of annotation_builder.build_annotation_json()
    image_file      : filename of the beam crop PNG (relative to images/)
    drawing_file    : DXF drawing name (for reference)
    dxf_source      : absolute or relative path to the DXF file
    dxf_bbox        : (x1, y1, x2, y2) in DXF mm
    pixel_bbox      : (left, upper, right, lower) in pixels
    image_size_px   : (width, height) of the cropped image
    """
    section  = beam_entry.get("section") or {}
    width_mm = float(
        beam_entry.get("width_mm") or section.get("width_mm") or 0.0
    )
    depth_mm = float(
        beam_entry.get("depth_mm") or section.get("depth_mm") or 0.0
    )
    span_mm  = float(
        beam_entry.get("clear_span_mm")
        or (axis_entry or {}).get("beam_length_mm")
        or 0.0
    )
    orientation = (
        (axis_entry or {}).get("orientation")
        or beam_entry.get("orientation")
        or "HORIZONTAL"
    )

    annotations: List[Dict[str, Any]] = annotation_json.get("annotations") or []
    data_source = annotation_json.get("data_source") or "unknown"

    # Roles discovered
    roles_found: List[str] = sorted(
        {a["role"] for a in annotations if a.get("role") and a["role"] != "UNKNOWN"}
    )

    # Unique diameters
    diameters: List[float] = sorted(
        {float(a.get("diameter_mm") or 0.0)
         for a in annotations if a.get("diameter_mm")}
    )

    stirrup_present = any(a.get("role") == "STIRRUP" for a in annotations)

    # Engineering phases that contributed
    phases_used: List[str] = [data_source]
    if axis_entry:
        phases_used.append("R.3_geometry")

    def _bbox_dict(b: Optional[tuple]) -> Optional[Dict[str, Any]]:
        if b is None:
            return None
        if len(b) == 4:
            return {"x1": b[0], "y1": b[1], "x2": b[2], "y2": b[3]}
        return None

    return {
        "schema_version":       SCHEMA_VERSION,
        "model_version":        MODEL_VERSION,
        "beam_id":              beam_id,
        "beam_mark":            beam_entry.get("beam_mark") or beam_id,
        "drawing_file":         drawing_file,
        "dxf_source":           dxf_source,
        "image_file":           image_file,
        "beam_dimensions": {
            "width_mm":      width_mm,
            "depth_mm":      depth_mm,
            "clear_span_mm": span_mm,
        },
        "beam_orientation":     orientation,
        "bbox_dxf":             _bbox_dict(dxf_bbox),
        "bbox_pixels":          _bbox_dict(pixel_bbox),
        "image_size_pixels":    (
            {"width": image_size_px[0], "height": image_size_px[1]}
            if image_size_px else None
        ),
        "annotation_count":     len(annotations),
        "roles_discovered":     roles_found,
        "diameters_mm":         diameters,
        "stirrup_present":      stirrup_present,
        "engineering_phases":   phases_used,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
    }
