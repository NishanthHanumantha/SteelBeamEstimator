"""Production-signal features. Runtime: no GT / estimator / benchmark answers."""
from __future__ import annotations

from typing import Any, Dict, Optional

from PhaseP26_vision_candidate_recovery.candidate_gap_analyzer import score_beam

from .config import CROP_SOURCE, P26_PILOT_BEAMS
from .set_artefacts import drawing_set_name


def feature_row(
    *,
    set_key: str,
    beam_id: str,
    rec: Dict[str, Any],
    model: Optional[Dict[str, Any]],
    crop_exists: bool,
    crop_path: Optional[str],
) -> Dict[str, Any]:
    scored = score_beam(beam_id=beam_id, rec=rec, model=model, crop_exists=crop_exists)
    reasons = list(scored.get("gap_reasons") or [])
    counts = scored.get("r13_summary") or {}
    ann_n = int(scored.get("annotation_count") or 0)
    rej_n = int(scored.get("rejected_annotation_count") or 0)
    features = {
        "OCR_CORRUPTION_SIGNAL": "OCR_CORRUPTION" in reasons,
        "STIRRUP_TEXT_NO_OBJECT": "STIRRUP_TEXT_NO_OBJECT" in reasons,
        "INCOMPLETE_PARSE_SIGNAL": "INCOMPLETE_PARSE" in reasons,
        "SPARSE_REINFORCEMENT_SIGNAL": "SPARSE_REINFORCEMENT" in reasons,
        "UNASSOCIATED_REINFORCEMENT_TEXT": "UNASSOCIATED_REINF_TEXT" in reasons,
        "DIFFICULT_NOTATION_SIGNAL": ("TRUNCATED_SPACING" in reasons) or ("OCR_CORRUPTION" in reasons),
        "MULTI_ANNOTATION_SIGNAL": ann_n >= 4,
        "COMPLETE_PARSE_SIGNAL": "INCOMPLETE_PARSE" not in reasons and "OCR_CORRUPTION" not in reasons,
        "REINFORCEMENT_DENSITY": int(counts.get("total") or 0),
        "NUMBER_OF_DETERMINISTIC_OBJECTS": int(counts.get("total") or 0),
        "NUMBER_OF_UNASSOCIATED_ANNOTATIONS": rej_n,
        "HAS_TOP": int(counts.get("top") or 0) > 0,
        "HAS_BOTTOM": int(counts.get("bottom") or 0) > 0,
        "HAS_STIRRUPS": int(counts.get("stirrups") or 0) > 0,
    }
    return {
        "set_key": set_key,
        "source_set": drawing_set_name(set_key),
        "source_drawing": drawing_set_name(set_key),
        "beam_id": beam_id,
        "region_id": f"P261::{set_key}::{beam_id}",
        "score": int(scored.get("score") or 0),
        "gap_reasons": reasons,
        "features": features,
        "r13_summary": counts,
        "annotation_count": ann_n,
        "rejected_annotation_count": rej_n,
        "ocr_flags": bool(scored.get("ocr_flags")),
        "has_crop": crop_exists,
        "crop_path": crop_path,
        "crop_source": CROP_SOURCE,
        "drawing_visibility": "UNSEEN",
        "p26_pilot_overlap": set_key == "Fifth" and beam_id in P26_PILOT_BEAMS,
    }


__all__ = ["feature_row"]
