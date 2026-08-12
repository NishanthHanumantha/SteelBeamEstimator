"""Vision-crop health diagnostics (measurement only — not a hard gate)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .config import EXTREME_CROP_AREA_RATIO, EXTREME_CROP_HEIGHT_RATIO, EXTREME_Y_GAP_MM
from .spatial_metrics import as_bbox, bbox_area, bbox_wh, collect_beam_spatial_metrics


def classify_crop_health(spatial: Dict[str, Any]) -> str:
    ratios = spatial.get("ratios") or {}
    h_ratio = ratios.get("crop_height_to_beam_height_ratio") or 0.0
    a_ratio = ratios.get("crop_area_to_beam_area_ratio") or 0.0
    max_y = spatial.get("max_y_gap_mm") or 0.0
    if h_ratio >= EXTREME_CROP_HEIGHT_RATIO or a_ratio >= EXTREME_CROP_AREA_RATIO or max_y >= EXTREME_Y_GAP_MM:
        return "VISION_CROP_EXTREME"
    if h_ratio >= 4.0 or a_ratio >= 15.0 or max_y >= 2000.0:
        return "VISION_CROP_REQUIRES_REVIEW"
    return "VISION_CROP_HEALTHY"


def crop_sanity_for_beam(
    evidence: Dict[str, Any],
    *,
    engineering_png: Optional[Path] = None,
) -> Dict[str, Any]:
    spatial = collect_beam_spatial_metrics(evidence)
    ratios = spatial.get("ratios") or {}
    beam = as_bbox((evidence.get("target_beam") or {}).get("bbox"))
    crop = as_bbox(((evidence.get("evidence_window") or {}).get("bbox")))
    img_w = img_h = None
    beam_px = None
    if engineering_png and Path(engineering_png).exists() and beam and crop:
        try:
            from PIL import Image

            with Image.open(engineering_png) as im:
                img_w, img_h = im.size
            cw, ch = bbox_wh(crop)
            # Approximate beam pixel footprint assuming crop fills image
            if cw > 0 and ch > 0 and img_w and img_h:
                bw, bh = bbox_wh(beam)
                beam_px = {
                    "approx_beam_w_px": round(bw / cw * img_w, 1),
                    "approx_beam_h_px": round(bh / ch * img_h, 1),
                }
        except Exception as exc:  # noqa: BLE001
            beam_px = {"error": str(exc)}

    occupancy = None
    if beam and crop:
        occupancy = round(bbox_area(beam) / max(bbox_area(crop), 1.0), 4)

    health = classify_crop_health(spatial)
    return {
        "beam_id": evidence.get("beam_id"),
        "vision_crop_status": health,
        "crop_pixel_dimensions": {"img_w": img_w, "img_h": img_h},
        "approx_beam_pixel_dimensions": beam_px,
        "beam_occupancy_ratio": occupancy,
        "empty_space_ratio_approx": round(1.0 - (occupancy or 0.0), 4) if occupancy is not None else None,
        "crop_aspect_ratio": ratios.get("crop_aspect_wh"),
        "crop_height_to_beam_height_ratio": ratios.get("crop_height_to_beam_height_ratio"),
        "crop_area_to_beam_area_ratio": ratios.get("crop_area_to_beam_area_ratio"),
        "max_y_gap_mm": spatial.get("max_y_gap_mm"),
        "dominant_expander": spatial.get("dominant_expander"),
        "note": "Diagnostic only — not used as a Claude readiness hard gate.",
    }
