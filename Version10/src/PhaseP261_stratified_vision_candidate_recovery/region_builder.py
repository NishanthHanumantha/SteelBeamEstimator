"""Neutral localized region packages. No gap_reasons / stratum / R1.3 gap framing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP254_semantic_reinforcement_vision_benchmark.candidate_loader import (
    encode_image,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.vision_prompt import (
    BANNED_KEYS,
)

from .config import (
    CROP_BASE_MARGIN_MM,
    CROP_EVIDENCE_PAD_MM,
    CROP_RENDER_MAX_DIM_PX,
    CROP_SOURCE,
)
from .policy import assert_neutral_metadata
from .vision_prompt import assert_no_truth_leak


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _visible_texts(rec: Dict[str, Any]) -> List[str]:
    texts: List[str] = []
    for a in rec.get("accepted_annotations") or []:
        t = str(a.get("text") or "").strip()
        if t:
            texts.append(t)
    return texts[:20]


def build_region_package(
    *,
    beam_id: str,
    region_id: str,
    source_set: str,
    ownership_rec: Dict[str, Any],
    crop_path: Path,
) -> Dict[str, Any]:
    crop = Path(crop_path)
    env = ownership_rec.get("envelope") or {}
    bbox = env.get("crop_extent") or env.get("concrete_envelope")
    image = encode_image(crop) if crop.exists() else None
    if image:
        image["role"] = "beam_region_crop"
    crop_w = crop_h = None
    if crop.exists():
        try:
            from PIL import Image as _PILImage

            with _PILImage.open(crop) as im:
                crop_w, crop_h = im.size
        except Exception:
            crop_w = crop_h = None
    metadata = {
        "region_id": region_id,
        "beam_id": beam_id,
        "source_set": source_set,
        "target_beam": beam_id,
        "beam_depth_mm": env.get("depth_mm"),
        "region_bbox": bbox,
        "visible_callout_texts": _visible_texts(ownership_rec),
        "crop_config": {
            "source": CROP_SOURCE,
            "base_margin_mm": CROP_BASE_MARGIN_MM,
            "evidence_pad_mm": CROP_EVIDENCE_PAD_MM,
            "render_max_dim_px": CROP_RENDER_MAX_DIM_PX,
            "regenerate_dxf": False,
        },
        # visible_callout_texts are production-accepted drawing strings (drawing
        # evidence), not gap_reasons / stratum / expected-missing hints.
        "instruction": (
            "Image 1 is a localized crop of the TARGET beam with surrounding context. "
            "Neighbouring beams, slabs, columns, and notes may appear. Do not assume "
            "nearby text belongs to the TARGET beam."
        ),
    }
    for banned in BANNED_KEYS:
        metadata.pop(banned, None)
    assert_neutral_metadata(metadata)
    leaks = assert_no_truth_leak(metadata)
    image_hash = image.get("sha256") if image else None
    region_hash = _sha256_bytes(
        json.dumps(
            {"metadata": metadata, "image_hash": image_hash, "crop": str(crop)},
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    )
    drawing_hash = _sha256_bytes(f"{source_set}|{beam_id}".encode("utf-8"))
    return {
        "region_id": region_id,
        "beam_id": beam_id,
        "source_set": source_set,
        "crop_path": str(crop) if crop.exists() else None,
        "region_bbox": bbox,
        "metadata": metadata,
        "images": [image] if image else [],
        "image_hash": image_hash,
        "region_hash": region_hash,
        "drawing_hash": drawing_hash,
        "truth_leak_keys": leaks,
        "crop_width": crop_w,
        "crop_height": crop_h,
        "crop_source": CROP_SOURCE,
        "crop_hash": image_hash,
    }


__all__ = ["build_region_package"]
