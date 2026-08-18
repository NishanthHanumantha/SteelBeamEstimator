"""Production-signal gate features. Runtime: no GT / estimator / stratum decisions."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional

from PhaseP26_vision_candidate_recovery.candidate_gap_analyzer import score_beam
from PhaseP26_vision_candidate_recovery.deterministic_comparator import flatten_r13, _norm_text
from PhaseP251_quantity_intent_schema.intent_builder import build_intent_for_annotation

_OCR_RE = re.compile(r"\\X|\x00")
_STIRRUP_RE = re.compile(r"(?:\d+\s*L\s*-?\s*Y)|(?:@\s*\d)|(?:C\s*/\s*C)", re.IGNORECASE)
_LONG_RE = re.compile(r"(?<![A-Z])\d+\s*-?\s*Y\s*\d{1,2}", re.IGNORECASE)
_SIDE_RE = re.compile(r"S\.?F\.?R", re.IGNORECASE)
_DIA_RE = re.compile(r"Y\s*(\d{1,2})", re.IGNORECASE)


def _dia(text: str) -> Optional[int]:
    m = _DIA_RE.search(text or "")
    if not m:
        return None
    n = int(m.group(1))
    return n if n > 0 else None


def _family_from_text(text: str) -> str:
    t = text or ""
    if _STIRRUP_RE.search(t):
        return "STIRRUP"
    if _SIDE_RE.search(t):
        return "SIDE"
    if _LONG_RE.search(t):
        return "LONGITUDINAL"
    if _DIA_RE.search(t):
        return "LONGITUDINAL"
    return "UNKNOWN"


def _match_object(text: str, family: str, dia: Optional[int], bars: List[Dict[str, Any]]) -> bool:
    norm = _norm_text(text)
    for b in bars:
        bf = str(b.get("family") or "")
        bd = b.get("diameter_mm")
        if family == "STIRRUP" and bf == "STIRRUP":
            if dia is None or bd is None or dia == bd:
                return True
        elif family == "LONGITUDINAL" and bf in ("TOP", "BOTTOM"):
            if dia is None or bd == dia:
                return True
        elif family == "SIDE" and bf == "SIDE":
            if dia is None or bd == dia:
                return True
        if norm and norm == (b.get("norm_label") or "") and len(norm) >= 4:
            return True
    return False


def _intent_incomplete(beam_id: str, rec: Dict[str, Any], text: str) -> bool:
    env = rec.get("envelope") or {}
    evidence = {
        "beam_id": beam_id,
        "phase_id": "P2.6.2_GATE_EVIDENCE",
        "annotations": [{"annotation_id": "A", "raw_text": text, "normalized_text": text}],
        "leader_chains": {"accepted": list(rec.get("accepted_chains") or [])},
        "beam_depth_mm": env.get("depth_mm"),
        "beam_orientation": "HORIZONTAL",
    }
    try:
        intent = build_intent_for_annotation(
            beam_id=beam_id,
            annotation={"annotation_id": "A", "raw_text": text, "normalized_text": text},
            evidence=evidence,
        )
    except Exception:
        return False
    if intent is None:
        return False
    return intent.quantity_status in ("UNRESOLVED", "INVALID")


def extract_gate_features(
    *,
    beam_id: str,
    rec: Dict[str, Any],
    model: Optional[Dict[str, Any]],
    association: str = "TARGET_BEAM",
) -> Dict[str, Any]:
    scored = score_beam(beam_id=beam_id, rec=rec, model=model, crop_exists=True)
    bars = flatten_r13(model)
    accepted = list(rec.get("accepted_annotations") or [])
    rejected = list(rec.get("rejected_annotations") or [])
    counts = scored.get("r13_summary") or {}

    stirrup_text = 0
    long_text = 0
    side_text = 0
    ocr_n = 0
    incomplete_n = 0
    matched_n = 0
    unmatched_stirrup = 0
    unmatched_long = 0
    ocr_stirrup_unmatched = 0
    reinf_ann_n = 0
    long_ann_by_dia: Counter = Counter()

    for a in accepted:
        text = str(a.get("text") or "")
        if not text.strip():
            continue
        fam = _family_from_text(text)
        if fam == "UNKNOWN":
            continue
        reinf_ann_n += 1
        dia = _dia(text)
        ocr = bool(_OCR_RE.search(text))
        if ocr:
            ocr_n += 1
        if _intent_incomplete(beam_id, rec, text):
            incomplete_n += 1
        matched = _match_object(text, fam, dia, bars)
        if matched:
            matched_n += 1
        if fam == "STIRRUP":
            stirrup_text += 1
            if not matched:
                unmatched_stirrup += 1
                if ocr:
                    ocr_stirrup_unmatched += 1
        elif fam == "LONGITUDINAL":
            long_text += 1
            if dia is not None:
                long_ann_by_dia[dia] += 1
            if not matched:
                unmatched_long += 1
        elif fam == "SIDE":
            side_text += 1

    unassociated_n = 0
    unassociated_strong = 0
    for a in rejected:
        text = str(a.get("text") or "")
        fam = _family_from_text(text)
        if fam == "UNKNOWN":
            continue
        unassociated_n += 1
        if fam == "STIRRUP" or _OCR_RE.search(text):
            unassociated_strong += 1

    long_obj_by_dia: Counter = Counter()
    for b in bars:
        if b.get("family") in ("TOP", "BOTTOM") and b.get("diameter_mm") is not None:
            long_obj_by_dia[int(b["diameter_mm"])] += 1
    long_shortfall = 0
    for dia, n_ann in long_ann_by_dia.items():
        n_obj = int(long_obj_by_dia.get(dia, 0) or 0)
        long_shortfall += max(0, int(n_ann) - n_obj)
    unmatched_long = unmatched_long + long_shortfall

    assoc = str(association or "TARGET_BEAM").upper()
    return {
        "beam_id": beam_id,
        "annotation_count": len(accepted),
        "rejected_annotation_count": len(rejected),
        "reinforcement_annotation_count": reinf_ann_n,
        "deterministic_object_count": int(counts.get("total") or 0),
        "matching_object_count": matched_n,
        "incomplete_parse_count": incomplete_n,
        "OCR_corruption_count": ocr_n,
        "unassociated_annotation_count": unassociated_n,
        "stirrup_text_present": stirrup_text > 0,
        "stirrup_object_present": int(counts.get("stirrups") or 0) > 0,
        "stirrup_text_no_object": stirrup_text > 0 and int(counts.get("stirrups") or 0) == 0,
        "unmatched_stirrup_count": unmatched_stirrup,
        "ocr_corrupted_stirrup_unmatched": ocr_stirrup_unmatched,
        "longitudinal_text_present": long_text > 0,
        "unmatched_longitudinal_count": unmatched_long,
        "longitudinal_object_shortfall": long_shortfall,
        "side_text_present": side_text > 0,
        "side_object_present": int(counts.get("side") or 0) > 0,
        "unassociated_strong_count": unassociated_strong,
        "parse_complete": incomplete_n == 0 and ocr_n == 0,
        "association": assoc,
        "has_top": int(counts.get("top") or 0) > 0,
        "has_bottom": int(counts.get("bottom") or 0) > 0,
        "r13_summary": counts,
        "score_beam_reasons": list(scored.get("gap_reasons") or []),
    }


__all__ = ["extract_gate_features"]
