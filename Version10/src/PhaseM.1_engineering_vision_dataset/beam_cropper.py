"""
beam_cropper.py — Crop per-beam images from a rendered full DXF drawing.

For every discovered beam:
  - Computes a DXF bounding box from beam axis / centroid + configurable padding.
  - Maps DXF bbox → pixel rect using CoordTransform.
  - Crops from the full rendered image using PIL.

The crop includes:
  - Beam geometry + section rectangle
  - Nearby annotations and leader lines
  - Support regions, stirrups, development / curtailment bars
  - Sufficient padding so text is never clipped

MODEL_VERSION: 9.0.0
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .dxf_renderer import CoordTransform

MODEL_VERSION = "9.0.0"

# Padding around the beam crop in DXF units (mm).
# 3 000 mm = 3 m — captures leaders, annotations and support zones.
DEFAULT_PADDING_MM = 3_000.0


@dataclass
class BeamCrop:
    """Complete crop metadata for one beam."""
    beam_id:    str
    dxf_bbox:   Tuple[float, float, float, float]   # (x1, y1, x2, y2) DXF mm
    pixel_bbox: Tuple[int,   int,   int,   int  ]   # (left, upper, right, lower) pixels
    image_path: Optional[Path] = None
    image_size: Optional[Tuple[int, int]] = None    # (width_px, height_px)


def compute_beam_dxf_bbox(
    beam_id:    str,
    beam_entry: Dict[str, Any],
    axis_entry: Optional[Dict[str, Any]] = None,
    padding_mm: float = DEFAULT_PADDING_MM,
) -> Optional[Tuple[float, float, float, float]]:
    """
    Compute the DXF bounding box (x1, y1, x2, y2) for a beam crop.

    Priority:
      1. BeamAxis.json (dxf_centroid_x/y + beam_length_mm) — most accurate.
      2. beam_registry (centroid_x/y + clear_span_mm)      — fallback.

    Returns None if no valid centroid coordinates are available.
    """
    cx = cy = span = depth = 0.0

    if axis_entry:
        cx    = float(axis_entry.get("dxf_centroid_x") or 0.0)
        cy    = float(axis_entry.get("dxf_centroid_y") or 0.0)
        span  = float(axis_entry.get("beam_length_mm") or 0.0)
        # depth from beam_registry
        sec   = beam_entry.get("section") or {}
        depth = float(beam_entry.get("depth_mm") or sec.get("depth_mm") or 600.0)
    elif beam_entry:
        cx    = float(beam_entry.get("centroid_x") or 0.0)
        cy    = float(beam_entry.get("centroid_y") or 0.0)
        span  = float(beam_entry.get("clear_span_mm") or 0.0) * 1.2
        depth = float(beam_entry.get("depth_mm") or 600.0)

    if cx == 0.0 and cy == 0.0:
        return None

    half_span  = span / 2.0 + padding_mm
    half_depth = max(depth / 2.0, 300.0) + padding_mm   # minimum ±300 mm

    return (cx - half_span, cy - half_depth, cx + half_span, cy + half_depth)


def dxf_bbox_to_pixel_rect(
    dxf_bbox:  Tuple[float, float, float, float],
    transform: CoordTransform,
) -> Tuple[int, int, int, int]:
    """
    Convert a DXF bbox (x1, y1, x2, y2) to PIL-compatible pixel rect
    (left, upper, right, lower).

    DXF: Y increases upward.
    PIL: Y increases downward.

    So:
      - DXF lower-left (x1, y1)  →  pixel (left,  lower)
      - DXF upper-right (x2, y2) →  pixel (right, upper)
    """
    x1, y1, x2, y2 = dxf_bbox

    px_left,  py_lower = transform.dxf_to_pixel(x1, y1)
    px_right, py_upper = transform.dxf_to_pixel(x2, y2)

    # Clamp to image bounds
    W, H = transform.img_w, transform.img_h
    left  = max(0, min(px_left,  W - 1))
    right = max(0, min(px_right, W    ))
    upper = max(0, min(py_upper, H - 1))
    lower = max(0, min(py_lower, H    ))

    # Ensure non-degenerate box (at least 1px in each dimension)
    if right <= left:
        right = min(left + 1, W)
    if lower <= upper:
        lower = min(upper + 1, H)

    return (left, upper, right, lower)


def crop_beam_image(
    full_image_path: Path,
    beam_id:         str,
    dxf_bbox:        Tuple[float, float, float, float],
    transform:       CoordTransform,
    output_path:     Path,
) -> BeamCrop:
    """
    Crop the beam region from the full rendered image and save as PNG.

    Parameters
    ----------
    full_image_path : path to the full DXF rendering (PNG).
    beam_id         : e.g. "B17".
    dxf_bbox        : (x1, y1, x2, y2) in DXF mm coordinates.
    transform       : CoordTransform returned by render_dxf_to_png().
    output_path     : where to save the beam crop PNG.

    Returns
    -------
    BeamCrop — includes image_path and pixel_bbox.
    """
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "Pillow is required for beam image cropping.\n"
            "Install with:  pip install Pillow"
        ) from exc

    pixel_rect = dxf_bbox_to_pixel_rect(dxf_bbox, transform)
    left, upper, right, lower = pixel_rect

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(str(full_image_path)) as img:
        crop = img.crop((left, upper, right, lower))
        crop.save(str(output_path), "PNG")
        crop_size = crop.size   # (width, height)

    return BeamCrop(
        beam_id    = beam_id,
        dxf_bbox   = dxf_bbox,
        pixel_bbox = pixel_rect,
        image_path = output_path,
        image_size = crop_size,
    )
