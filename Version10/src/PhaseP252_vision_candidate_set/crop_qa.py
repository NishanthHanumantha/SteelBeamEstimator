"""Crop / visual evidence QA for Vision candidates."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import EXTREME_CROP_HEIGHT_MM, EXTREME_CROP_WIDTH_MM

PASS = "PASS"
FAIL = "FAIL"
PARTIAL = "PARTIAL"
NA = "NOT_APPLICABLE"


def _gate(ok: Optional[bool], *, applicable: bool = True) -> str:
    if not applicable:
        return NA
    if ok is None:
        return NA
    return PASS if ok else FAIL


def evaluate_candidate_crop_qa(
    *,
    selection: Dict[str, Any],
    evidence: Optional[Dict[str, Any]],
    local_crop_path: Optional[Path],
    beam_context_path: Optional[Path],
) -> Dict[str, Any]:
    beam_id = selection.get("beam_id")
    aid = selection.get("annotation_id")
    flags: List[str] = []

    if evidence is None:
        gates = {
            "TARGET_BEAM_PRESENT": FAIL,
            "TARGET_ANNOTATION_PRESENT": FAIL,
            "LEADER_PRESENT_WHEN_EXPECTED": NA,
            "RELEVANT_REINFORCEMENT_PRESENT_WHEN_EXPECTED": NA,
            "NO_REJECTED_PHYSICAL_BAR": FAIL,
            "NO_EXTREME_EXPANSION": FAIL,
            "NO_CLIPPED_SELECTED_EVIDENCE": FAIL,
            "VALID_IMAGE": FAIL,
            "READABLE_DIMENSIONS": FAIL,
        }
        return {
            "overall": FAIL,
            "gates": gates,
            "flags": ["MISSING_EVIDENCE_PACKAGE"],
            "image_width_px": None,
            "image_height_px": None,
            "crop_width_mm": None,
            "crop_height_mm": None,
        }

    target = evidence.get("target_beam") or {}
    anns = evidence.get("annotations") or []
    leaders = evidence.get("leaders") or []
    bars = evidence.get("reinforcement") or []
    owned = evidence.get("owned_geometry") or []
    excluded = evidence.get("excluded_rejected_evidence") or {}
    rejected_bars = set(excluded.get("bars") or [])
    win = (evidence.get("evidence_window") or {}).get("bbox") or []
    base = (evidence.get("evidence_window") or {}).get("base_bbox") or []
    expansion = (evidence.get("evidence_window") or {}).get("expansion") or {}

    ann_hit = next((a for a in anns if str(a.get("annotation_id")) == str(aid)), None)
    leader_expected = bool(leaders) or any(
        str(aid) == str((c.get("annotation_id")))
        and (c.get("leaders") or [])
        for c in ((evidence.get("leader_chains") or {}).get("accepted") or [])
    )
    reinf_ids = {str(b.get("reinforcement_id")) for b in bars}
    rejected_included = bool(rejected_bars & reinf_ids)

    crop_w = crop_h = None
    if win and len(win) >= 4:
        crop_w = float(win[2]) - float(win[0])
        crop_h = float(win[3]) - float(win[1])
    beam_w = beam_h = None
    if base and len(base) >= 4:
        beam_w = float(base[2]) - float(base[0])
        beam_h = float(base[3]) - float(base[1])

    extreme = False
    if crop_h is not None and crop_h >= EXTREME_CROP_HEIGHT_MM:
        extreme = True
        flags.append("EXTREME_CROP_HEIGHT")
    if crop_w is not None and crop_w >= EXTREME_CROP_WIDTH_MM:
        extreme = True
        flags.append("EXTREME_CROP_WIDTH")

    img_w = img_h = None
    valid_image = False
    if local_crop_path and Path(local_crop_path).exists():
        try:
            from PIL import Image

            with Image.open(local_crop_path) as im:
                img_w, img_h = im.size
            valid_image = bool(img_w and img_h and img_w > 10 and img_h > 10)
        except Exception:
            valid_image = False
            flags.append("IMAGE_READ_ERROR")
    else:
        flags.append("MISSING_LOCAL_CROP")

    still_clipped = int(expansion.get("still_clipped_count") or 0) > 0
    if still_clipped:
        flags.append("EVIDENCE_CLIPPED")

    # Annotation visibility heuristic
    ann_bbox = (ann_hit or {}).get("bbox") if ann_hit else None
    if ann_bbox and len(ann_bbox) >= 4:
        aw = abs(float(ann_bbox[2]) - float(ann_bbox[0]))
        ah = abs(float(ann_bbox[3]) - float(ann_bbox[1]))
        if aw < 5 and ah < 5:
            flags.append("TINY_ANNOTATION")

    if crop_w and crop_h and beam_w and beam_h:
        ratio = (crop_w * crop_h) / max(beam_w * beam_h, 1.0)
        if ratio > 40:
            flags.append("CROP_TOO_LARGE")
        if crop_w / max(crop_h, 1.0) > 8 or crop_h / max(crop_w, 1.0) > 8:
            flags.append("EXTREME_ASPECT_RATIO")

    if beam_context_path and Path(beam_context_path).exists():
        # same verified crop is OK; flag if path missing only
        pass
    else:
        flags.append("MISSING_BEAM_CONTEXT_CROP")

    reinf_expected = bool(owned) or bool(bars) or any(
        str((a.get("raw_text") or "")).upper().find("Y") >= 0 for a in anns
    )

    gates = {
        "TARGET_BEAM_PRESENT": _gate(
            bool(target.get("in_ownership") or target.get("in_envelope") or beam_id)
        ),
        "TARGET_ANNOTATION_PRESENT": _gate(ann_hit is not None),
        "LEADER_PRESENT_WHEN_EXPECTED": _gate(
            (len(leaders) > 0) if leader_expected else None,
            applicable=leader_expected,
        ),
        "RELEVANT_REINFORCEMENT_PRESENT_WHEN_EXPECTED": _gate(
            (len(owned) > 0 or len(bars) > 0) if reinf_expected else None,
            applicable=reinf_expected and selection.get("outcome") == "VISION_CANDIDATE",
        ),
        "NO_REJECTED_PHYSICAL_BAR": _gate(not rejected_included),
        "NO_EXTREME_EXPANSION": _gate(not extreme),
        "NO_CLIPPED_SELECTED_EVIDENCE": _gate(not still_clipped),
        "VALID_IMAGE": _gate(valid_image),
        "READABLE_DIMENSIONS": _gate(
            bool(crop_w and crop_h and crop_w > 0 and crop_h > 0)
        ),
    }

    hard = {
        "TARGET_BEAM_PRESENT",
        "TARGET_ANNOTATION_PRESENT",
        "NO_REJECTED_PHYSICAL_BAR",
        "NO_EXTREME_EXPANSION",
        "VALID_IMAGE",
    }
    hard_fails = [k for k, v in gates.items() if v == FAIL and k in hard]
    soft_fails = [k for k, v in gates.items() if v == FAIL and k not in hard]
    if hard_fails:
        overall = FAIL
    elif soft_fails or flags:
        overall = PARTIAL if soft_fails or any(
            f in flags for f in ("TINY_ANNOTATION", "CROP_TOO_LARGE", "EVIDENCE_CLIPPED")
        ) else PASS
        if not soft_fails and not hard_fails:
            overall = PASS if not any(
                f.startswith("EXTREME") or f.startswith("MISSING") for f in flags
            ) else PARTIAL
    else:
        overall = PASS
    # simplify overall
    if hard_fails:
        overall = FAIL
    elif soft_fails:
        overall = PARTIAL
    elif any(f in ("MISSING_LOCAL_CROP", "MISSING_BEAM_CONTEXT_CROP", "IMAGE_READ_ERROR") for f in flags):
        overall = FAIL
    else:
        overall = PASS if not hard_fails else FAIL
        if flags and overall == PASS:
            # advisory flags only → still PASS unless extreme
            if any(f.startswith("EXTREME_CROP") for f in flags):
                overall = FAIL
            elif any(f in ("TINY_ANNOTATION", "CROP_TOO_LARGE", "EXTREME_ASPECT_RATIO") for f in flags):
                overall = PARTIAL

    crop_to_beam = None
    if crop_w and crop_h and beam_w and beam_h:
        crop_to_beam = round((crop_w * crop_h) / max(beam_w * beam_h, 1.0), 4)

    return {
        "overall": overall,
        "gates": gates,
        "hard_fails": hard_fails,
        "soft_fails": soft_fails,
        "flags": sorted(set(flags)),
        "image_width_px": img_w,
        "image_height_px": img_h,
        "crop_width_mm": crop_w,
        "crop_height_mm": crop_h,
        "beam_width_mm": beam_w,
        "beam_height_mm": beam_h,
        "crop_to_beam_ratio": crop_to_beam,
        "annotation_bbox_size": (
            [
                abs(float(ann_bbox[2]) - float(ann_bbox[0])),
                abs(float(ann_bbox[3]) - float(ann_bbox[1])),
            ]
            if ann_bbox and len(ann_bbox) >= 4
            else None
        ),
        "annotation_visibility_status": "PRESENT" if ann_hit else "MISSING",
        "rejected_bars_in_reinforcement": sorted(rejected_bars & reinf_ids),
        "excluded_rejected_bars_count": len(rejected_bars),
    }
