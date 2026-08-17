"""
Production-signal region selection. Runtime: no GT / estimator / benchmark answers.

Signals are limited to DXF ownership, R1.3 objects, and P2.5.1 parse status.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PhaseP251_quantity_intent_schema.intent_builder import build_intent_for_annotation
from PhaseP257_unseen_drawing_controlled_vision_validation.regression import (
    fifth_set_production_paths,
)

from .config import (
    CROP_SOURCE,
    PILOT_MAX_REGIONS,
    PILOT_MIN_REGIONS,
    PILOT_SET,
    PILOT_TARGET_REGIONS,
    PRIMARY_SET_KEY,
)
from .policy import assert_runtime_context

_OCR_RE = re.compile(r"\\X|\x00")
_STIRRUP_RE = re.compile(r"(?:\d+\s*L\s*-?\s*Y)|(?:@\s*\d)|(?:C\s*/\s*C)", re.IGNORECASE)
_REINF_RE = re.compile(r"(?:\d+\s*-?\s*Y\s*\d)|(?:Y\s*\d{1,2})|(?:S\.?F\.?R)", re.IGNORECASE)


def _ownership_path(version10_root: Path) -> Path:
    return (
        Path(version10_root)
        / "data"
        / "output"
        / "PhaseQA30_unseen_benchmark"
        / "Fifth_Set_Drawings"
        / "EngineeringSummaries"
        / "BeamOwnership.json"
    )


def _crop_path(version10_root: Path, beam_id: str) -> Path:
    return (
        Path(version10_root)
        / "data"
        / "output"
        / "PhaseQA30_unseen_benchmark"
        / "Fifth_Set_Drawings"
        / "RenderedCrops"
        / "shared_renders"
        / f"{beam_id}_render.png"
    )


def _load_r13_index(version10_root: Path) -> Dict[str, Dict[str, Any]]:
    paths = fifth_set_production_paths(version10_root)
    r13_path = paths.get("fifth_r13_models")
    if r13_path is None or not Path(r13_path).exists():
        return {}
    doc = json.loads(Path(r13_path).read_text(encoding="utf-8"))
    return {m.get("beam_id"): m for m in (doc.get("models") or []) if isinstance(m, dict)}


def _ann_texts(rec: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for key in ("accepted_annotations", "rejected_annotations"):
        for a in rec.get(key) or []:
            t = str(a.get("text") or "")
            if t:
                out.append(t)
    return out


def _accepted_texts(rec: Dict[str, Any]) -> List[str]:
    return [str(a.get("text") or "") for a in (rec.get("accepted_annotations") or []) if a.get("text")]


def _count_bars(model: Optional[Dict[str, Any]]) -> Dict[str, int]:
    if not model:
        return {
            "total": 0,
            "top": 0,
            "bottom": 0,
            "stirrups": 0,
            "side": 0,
            "spacer": 0,
        }
    top = len(model.get("top_main_bars") or []) + len(model.get("top_extra_bars") or [])
    bot = len(model.get("bottom_main_bars") or []) + len(model.get("bottom_extra_bars") or [])
    sti = len(model.get("stirrups") or [])
    side = len(model.get("side_face_reinforcement") or [])
    spa = len(model.get("spacer_bars") or [])
    total = int(model.get("total_classified_bars") or (top + bot + sti + side + spa))
    return {"total": total, "top": top, "bottom": bot, "stirrups": sti, "side": side, "spacer": spa}


def _spacing_truncated(text: str, stirrup_count: int) -> bool:
    if "@" not in (text or "") or stirrup_count <= 0:
        return False
    toks = re.findall(r"\d+", (text or "").split("@", 1)[1])
    return len(toks) >= 3


def _beam_evidence(beam_id: str, rec: Dict[str, Any]) -> Dict[str, Any]:
    anns = []
    for a in rec.get("accepted_annotations") or []:
        aid = a.get("id") or a.get("annotation_id")
        anns.append(
            {
                "annotation_id": aid,
                "raw_text": a.get("text") or "",
                "normalized_text": a.get("text") or "",
            }
        )
    env = rec.get("envelope") or {}
    return {
        "beam_id": beam_id,
        "phase_id": "P2.6_FIFTH_SET_EVIDENCE",
        "annotations": anns,
        "leader_chains": {"accepted": list(rec.get("accepted_chains") or [])},
        "beam_depth_mm": env.get("depth_mm"),
        "beam_orientation": "HORIZONTAL",
    }


def score_beam(
    *,
    beam_id: str,
    rec: Dict[str, Any],
    model: Optional[Dict[str, Any]],
    crop_exists: bool,
) -> Dict[str, Any]:
    reasons: List[str] = []
    score = 0
    texts = _ann_texts(rec)
    accepted = _accepted_texts(rec)
    counts = _count_bars(model)
    ocr = any(_OCR_RE.search(t) for t in texts)
    stirrup_like = any(_STIRRUP_RE.search(t) for t in accepted)
    reinf_like_rejected = any(
        _REINF_RE.search(str(a.get("text") or ""))
        for a in (rec.get("rejected_annotations") or [])
    )

    if ocr:
        reasons.append("OCR_CORRUPTION")
        score += 3
    if stirrup_like and counts["stirrups"] == 0:
        reasons.append("STIRRUP_TEXT_NO_OBJECT")
        score += 4
    if counts["total"] <= 2:
        reasons.append("SPARSE_REINFORCEMENT")
        score += 3
    if accepted and counts["top"] == 0:
        reasons.append("MISSING_TOP_WHILE_ANNS")
        score += 2
    if accepted and counts["bottom"] == 0:
        reasons.append("MISSING_BOTTOM_WHILE_ANNS")
        score += 2
    if reinf_like_rejected:
        reasons.append("UNASSOCIATED_REINF_TEXT")
        score += 2

    incomplete = 0
    evidence = _beam_evidence(beam_id, rec)
    for ann in evidence["annotations"]:
        intent = build_intent_for_annotation(
            beam_id=beam_id, annotation=ann, evidence=evidence
        )
        if intent is None:
            continue
        if intent.quantity_status in ("UNRESOLVED", "INVALID"):
            incomplete += 1
        if _spacing_truncated(ann.get("raw_text") or "", counts["stirrups"]):
            if "TRUNCATED_SPACING" not in reasons:
                reasons.append("TRUNCATED_SPACING")
                score += 2
    if incomplete:
        reasons.append("INCOMPLETE_PARSE")
        score += 3

    if not crop_exists:
        reasons.append("MISSING_CROP")
        score = 0

    return {
        "beam_id": beam_id,
        "score": score,
        "gap_reasons": reasons,
        "ocr_flags": ocr,
        "r13_summary": counts,
        "annotation_count": len(accepted),
        "rejected_annotation_count": len(rec.get("rejected_annotations") or []),
        "has_crop": crop_exists,
        "crop_source": CROP_SOURCE,
    }


def select_pilot_regions(
    *,
    version10_root: Path,
    target: int = PILOT_TARGET_REGIONS,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Select 10–20 beams using production-available signals only."""
    v10 = Path(version10_root)
    own = json.loads(_ownership_path(v10).read_text(encoding="utf-8"))
    r13 = _load_r13_index(v10)
    scored: List[Dict[str, Any]] = []
    for beam_id, rec in sorted((own.get("by_beam") or {}).items()):
        crop = _crop_path(v10, beam_id)
        row = score_beam(
            beam_id=beam_id,
            rec=rec,
            model=r13.get(beam_id),
            crop_exists=crop.exists(),
        )
        row["crop_path"] = str(crop) if crop.exists() else None
        row["region_id"] = f"P26::{PRIMARY_SET_KEY}::{beam_id}"
        scored.append(row)

    eligible = [r for r in scored if r["score"] > 0 and r["has_crop"]]
    eligible.sort(key=lambda r: (-int(r["score"]), r["beam_id"]))
    n = min(max(int(target), PILOT_MIN_REGIONS), PILOT_MAX_REGIONS)
    selected = eligible[:n]
    for row in selected:
        assert_runtime_context(
            {
                "beam_id": row["beam_id"],
                "region_id": row["region_id"],
                "crop_path": row["crop_path"],
                "accepted_annotations": [],
                "gap_reasons": row["gap_reasons"],
                "r13_summary": row["r13_summary"],
                "quantity_statuses": [],
                "ocr_flags": row["ocr_flags"],
            }
        )
    summary = {
        "pilot_set": PILOT_SET,
        "set_key": PRIMARY_SET_KEY,
        "beams_scored": len(scored),
        "eligible_with_crop": len(eligible),
        "selected": len(selected),
        "target": n,
        "selection_basis": "production_signals_only",
        "gt_used_for_selection": False,
        "estimator_used_for_selection": False,
        "crop_source": CROP_SOURCE,
        "reason_counts": _reason_counts(selected),
    }
    return selected, summary


def _reason_counts(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for r in rows:
        for reason in r.get("gap_reasons") or []:
            counts[reason] = counts.get(reason, 0) + 1
    return counts


__all__ = ["score_beam", "select_pilot_regions"]
