"""
preview_generator.py — Generate visual preview images for dataset quality inspection.

For each beam crop, produces a Beam_<ID>_preview.png showing:
  - Beam bounding box outline
  - Annotation markers (colour-coded by role)
  - Role and text labels
  - Beam ID label

Previews are for HUMAN INSPECTION ONLY.
  - Original beam images remain clean (no overlays).
  - Previews are NOT used as training labels.
  - No bounding boxes are drawn on the original crop.

MODEL_VERSION: 9.0.0
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "9.0.0"

# ── Role → RGB colour ─────────────────────────────────────────────────────────
ROLE_COLOURS: Dict[str, Tuple[int, int, int]] = {
    "TOP_MAIN":                (220,  20,  60),   # crimson
    "BOTTOM_MAIN":             (  0, 100, 200),   # royal blue
    "TOP_EXTRA":               (255, 140,   0),   # dark orange
    "BOTTOM_EXTRA":            (  0, 180, 120),   # sea green
    "STIRRUP":                 (128,   0, 128),   # purple
    "SIDE_FACE_REINFORCEMENT": ( 70, 130, 180),   # steel blue
    "DEVELOPMENT":             (184, 134,  11),   # dark golden
    "LAP":                     (205, 133,  63),   # peru
    "ANCHORAGE":               ( 46, 139,  87),   # sea green dark
    "UNKNOWN":                 (128, 128, 128),   # grey
}
_DEFAULT_COLOUR: Tuple[int, int, int] = (100, 100, 100)

_DOT_RADIUS = 8    # px — marker circle radius
_LABEL_PAD  = 6    # px — gap between marker and label text
_ALPHA_FILL = 200  # 0-255 — marker fill opacity
_ALPHA_TEXT = 230  # 0-255 — label text opacity


def generate_preview(
    beam_crop_path:  Path,
    annotation_json: Dict[str, Any],
    output_path:     Path,
) -> None:
    """
    Generate a preview PNG with annotation overlays from *beam_crop_path*.

    Annotation pixel positions are stored in full-image pixel coordinates
    (position_pixels in annotation_json).  We subtract the crop origin
    (from annotation_json["bbox_pixels"]) to convert to crop-local coordinates.

    Parameters
    ----------
    beam_crop_path  : the clean beam crop PNG.
    annotation_json : output of annotation_builder.build_annotation_json().
    output_path     : destination preview PNG path.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise ImportError(
            "Pillow is required for preview generation.\n"
            "Install with:  pip install Pillow"
        ) from exc

    if not beam_crop_path.exists():
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    bbox_px: List[int] = annotation_json.get("bbox_pixels") or [0, 0, 0, 0]
    crop_x0 = bbox_px[0] if len(bbox_px) >= 2 else 0
    crop_y0 = bbox_px[1] if len(bbox_px) >= 2 else 0

    with Image.open(str(beam_crop_path)) as img:
        preview = img.copy().convert("RGB")

    w, h = preview.size
    # Use RGBA for alpha compositing of overlays
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    # Beam bounding box outline
    draw.rectangle(
        [2, 2, w - 3, h - 3],
        outline=(0, 0, 200, 160),
        width=3,
    )

    annotations: List[Dict[str, Any]] = annotation_json.get("annotations") or []
    for ann in annotations:
        pos_px: Optional[List[int]] = ann.get("position_pixels")
        if not pos_px or len(pos_px) < 2:
            continue

        # Convert full-image pixels → crop-local pixels
        cx = pos_px[0] - crop_x0
        cy = pos_px[1] - crop_y0

        if not (0 <= cx < w and 0 <= cy < h):
            continue   # annotation outside crop (shouldn't normally happen)

        role   = ann.get("role") or "UNKNOWN"
        colour = ROLE_COLOURS.get(role, _DEFAULT_COLOUR)

        # Filled circle marker
        draw.ellipse(
            [cx - _DOT_RADIUS, cy - _DOT_RADIUS,
             cx + _DOT_RADIUS, cy + _DOT_RADIUS],
            fill    = (*colour, _ALPHA_FILL),
            outline = (255, 255, 255, 255),
            width   = 2,
        )

        # Role + text label
        role_display = ann.get("role_display") or role
        text_val     = ann.get("text") or ""
        label        = f"{role_display}: {text_val}" if text_val else role_display

        lx = cx + _DOT_RADIUS + _LABEL_PAD
        ly = cy - 7   # vertically centred on marker
        draw.text((lx, ly), label, fill=(*colour, _ALPHA_TEXT))

    # Composite overlay onto preview
    preview_rgba = preview.convert("RGBA")
    preview_rgba.alpha_composite(overlay)
    preview_rgb  = preview_rgba.convert("RGB")

    # Beam ID label — dark badge in top-left corner
    beam_id = annotation_json.get("beam_id") or ""
    if beam_id:
        badge_w = 160
        badge_h = 26
        badge   = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 170))
        bd      = ImageDraw.Draw(badge)
        bd.text((6, 5), f"Beam {beam_id}", fill=(255, 220, 0, 255))
        preview_rgba2 = preview_rgb.convert("RGBA")
        preview_rgba2.paste(badge, (4, 4), badge)
        preview_rgb = preview_rgba2.convert("RGB")

    preview_rgb.save(str(output_path), "PNG")
