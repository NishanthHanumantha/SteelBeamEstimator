"""
Localized beam-region packages for Claude Vision.

Reuses frozen QA.3.0 / P250 Fifth Set engineering crops. Does not re-render DXF
and does not read GT / estimator workbooks.
"""
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
    CROP_CONTEXT_NOTE,
    CROP_EVIDENCE_PAD_MM,
    CROP_RENDER_MAX_DIM_PX,
    CROP_SOURCE,
    PRIMARY_DRAWING_SET,
)
from .vision_prompt import assert_no_truth_leak


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ann_payload(rec: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for a in rec.get("accepted_annotations") or []:
        out.append(
            {
                "annotation_id": a.get("id") or a.get("annotation_id"),
                "text": a.get("text") or "",
                "ownership": "ACCEPTED",
                "ownership_reason": a.get("ownership_reason"),
            }
        )
    for a in rec.get("rejected_annotations") or []:
        out.append(
            {
                "annotation_id": a.get("id") or a.get("annotation_id"),
                "text": a.get("text") or "",
                "ownership": "REJECTED",
                "ownership_reason": a.get("ownership_reason") or a.get("rejected_rule"),
            }
        )
    return out


def _r13_compact(model: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not model:
        return {
            "present": False,
            "top_main": [],
            "bottom_main": [],
            "stirrups": [],
            "side_face": [],
            "spacers": [],
            "total_classified_bars": 0,
        }

    def _bars(key: str) -> List[Dict[str, Any]]:
        rows = []
        for b in model.get(key) or []:
            if not isinstance(b, dict):
                continue
            rows.append(
                {
                    "bar_id": b.get("bar_id"),
                    "semantic_role": b.get("semantic_role"),
                    "diameter_mm": b.get("diameter_mm"),
                    "quantity": b.get("quantity"),
                    "bar_label": b.get("bar_label"),
                    "spacing_mm": b.get("spacing_mm"),
                }
            )
        return rows

    return {
        "present": True,
        "top_main": _bars("top_main_bars") + _bars("top_extra_bars"),
        "bottom_main": _bars("bottom_main_bars") + _bars("bottom_extra_bars"),
        "stirrups": _bars("stirrups"),
        "side_face": _bars("side_face_reinforcement"),
        "spacers": _bars("spacer_bars"),
        "total_classified_bars": model.get("total_classified_bars"),
    }


def crop_config() -> Dict[str, Any]:
    return {
        "source": CROP_SOURCE,
        "reuse_p250_p252_infrastructure": True,
        "base_margin_mm": CROP_BASE_MARGIN_MM,
        "evidence_pad_mm": CROP_EVIDENCE_PAD_MM,
        "render_max_dim_px": CROP_RENDER_MAX_DIM_PX,
        "context_note": CROP_CONTEXT_NOTE,
        "regenerate_dxf": False,
    }


def build_region_package(
    *,
    beam_id: str,
    region_id: str,
    ownership_rec: Dict[str, Any],
    r13_model: Optional[Dict[str, Any]],
    crop_path: Path,
    gap_reasons: List[str],
) -> Dict[str, Any]:
    crop = Path(crop_path)
    env = ownership_rec.get("envelope") or {}
    bbox = env.get("crop_extent") or env.get("concrete_envelope")
    image = encode_image(crop) if crop.exists() else None
    if image:
        image["role"] = "beam_region_crop"
    metadata = {
        "region_id": region_id,
        "beam_id": beam_id,
        "source_set": PRIMARY_DRAWING_SET,
        "target_beam": beam_id,
        "gap_reasons": list(gap_reasons or []),
        "accepted_and_nearby_annotations": _ann_payload(ownership_rec),
        "deterministic_reinforcement": _r13_compact(r13_model),
        "beam_depth_mm": env.get("depth_mm"),
        "region_bbox": bbox,
        "crop_config": crop_config(),
        "instruction": (
            "Image 1 is a localized crop of the TARGET beam with surrounding context. "
            "Neighbouring beams, slabs, columns, and notes may appear. Do not assume "
            "nearby text belongs to the TARGET beam."
        ),
    }
    for banned in BANNED_KEYS:
        metadata.pop(banned, None)
    leaks = assert_no_truth_leak(metadata)
    image_hash = image.get("sha256") if image else None
    region_hash = _sha256_bytes(
        json.dumps(
            {"metadata": metadata, "image_hash": image_hash, "crop": str(crop)},
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    )
    drawing_hash = _sha256_bytes(f"{PRIMARY_DRAWING_SET}|{beam_id}".encode("utf-8"))
    return {
        "region_id": region_id,
        "beam_id": beam_id,
        "crop_path": str(crop) if crop.exists() else None,
        "region_bbox": bbox,
        "metadata": metadata,
        "images": [image] if image else [],
        "image_hash": image_hash,
        "region_hash": region_hash,
        "drawing_hash": drawing_hash,
        "truth_leak_keys": leaks,
        "crop_config": crop_config(),
    }


__all__ = ["build_region_package", "crop_config"]
