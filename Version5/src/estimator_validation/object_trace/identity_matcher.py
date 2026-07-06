"""Engineering identity construction and matching — Phase QA.2."""

from __future__ import annotations

import re
from typing import Any, Iterable, List, Optional, Tuple

from src.estimator_validation.comparison_utils import ScheduleRow, normalize_description
from src.estimator_validation.object_trace.trace_types import (
    CONFIDENCE_EXACT,
    CONFIDENCE_NO_FAB_MARK,
    CONFIDENCE_NO_SHAPE,
    CONFIDENCE_ROLE_DIAMETER,
    CONFIDENCE_UNMATCHED,
    EngineeringIdentity,
    MIN_MATCH_CONFIDENCE,
)


def role_from_description(description: str) -> str:
    text = normalize_description(description)
    mapping = {
        "top bars": "TOP_MAIN",
        "top bars - extra": "TOP_EXTRA",
        "top bars-extra": "TOP_EXTRA",
        "top bars -extra": "TOP_EXTRA",
        "bottom bars": "BOTTOM_MAIN",
        "bottom bars -extra": "BOTTOM_EXTRA",
        "bottom bars - extra": "BOTTOM_EXTRA",
        "stirupps": "STIRRUP",
        "stirrups": "STIRRUP",
        "sfr": "SFR",
        "spacer bars": "SPACER_BAR",
        "side bars": "SIDE_BAR",
    }
    return mapping.get(text, "UNKNOWN")


def identity_from_estimator_row(
    beam_mark: str,
    row: ScheduleRow,
    steel_grade: Optional[str] = None,
) -> EngineeringIdentity:
    role = row.role_hint if row.role_hint != "UNKNOWN" else role_from_description(row.description)
    return EngineeringIdentity(
        beam_mark=beam_mark,
        role=role,
        diameter_mm=row.diameter_mm,
        fabrication_mark=row.fabrication_mark,
        shape_code=row.shape_code,
        description=row.description,
        steel_grade=steel_grade,
        bar_count=row.bar_count,
        development_length_m=row.development_length_m,
    )


def identity_from_pipeline_row(
    beam_mark: str,
    record: dict[str, Any],
    steel_grade: Optional[str] = None,
) -> EngineeringIdentity:
    role = str(record.get("role") or record.get("reinforcement_role") or "UNKNOWN")
    diameter = record.get("diameter_mm") or record.get("diameter") or record.get("bar_diameter_mm")
    dev_mm = record.get("development_length_mm")
    return EngineeringIdentity(
        beam_mark=beam_mark,
        role=role,
        diameter_mm=float(diameter) if diameter is not None else None,
        fabrication_mark=_clean_str(record.get("fabrication_mark")),
        shape_code=_clean_str(record.get("shape_code")),
        description=_clean_str(record.get("description")),
        steel_grade=steel_grade or _clean_str(record.get("steel_grade")),
        bar_count=float(record["bar_count"]) if record.get("bar_count") is not None else None,
        development_length_m=float(dev_mm) / 1000.0 if dev_mm is not None else None,
    )


def identity_from_bar_identity(record: dict[str, Any]) -> EngineeringIdentity:
    beam_mark = str(record.get("beam_id") or record.get("beam_mark") or "")
    return EngineeringIdentity(
        beam_mark=beam_mark,
        role=str(record.get("reinforcement_role") or "UNKNOWN"),
        diameter_mm=float(record["bar_diameter_mm"]) if record.get("bar_diameter_mm") is not None else None,
        fabrication_mark=_clean_str(record.get("fabrication_mark")),
        shape_code=_clean_str(record.get("shape_code")),
        description=_clean_str(record.get("description")),
        bar_count=None,
        development_length_m=None,
    )


def compute_match_confidence(
    estimator: EngineeringIdentity,
    candidate: EngineeringIdentity,
) -> int:
    if estimator.beam_mark != candidate.beam_mark:
        return CONFIDENCE_UNMATCHED
    if estimator.role != candidate.role or estimator.role == "UNKNOWN":
        return CONFIDENCE_UNMATCHED
    if not _diameters_compatible(estimator.diameter_mm, candidate.diameter_mm):
        return CONFIDENCE_UNMATCHED

    score = CONFIDENCE_ROLE_DIAMETER
    if _optional_match(estimator.description, candidate.description):
        score = CONFIDENCE_NO_SHAPE
    if _optional_match(estimator.shape_code, candidate.shape_code):
        score = CONFIDENCE_NO_FAB_MARK
    if _optional_match(estimator.fabrication_mark, candidate.fabrication_mark):
        score = CONFIDENCE_EXACT
    if (
        score >= CONFIDENCE_NO_FAB_MARK
        and _numeric_compatible(estimator.bar_count, candidate.bar_count)
        and _numeric_compatible(estimator.development_length_m, candidate.development_length_m)
    ):
        score = CONFIDENCE_EXACT
    return score


class IdentityMatcher:
    """Match estimator identities against pipeline records by engineering identity."""

    def find_best_match(
        self,
        target: EngineeringIdentity,
        candidates: Iterable[tuple[str, EngineeringIdentity, dict[str, Any]]],
    ) -> Tuple[Optional[str], Optional[dict[str, Any]], int]:
        best_id: Optional[str] = None
        best_record: Optional[dict[str, Any]] = None
        best_score = CONFIDENCE_UNMATCHED
        for record_id, candidate, raw in candidates:
            score = compute_match_confidence(target, candidate)
            if score > best_score:
                best_score = score
                best_id = record_id
                best_record = raw
        if best_score < MIN_MATCH_CONFIDENCE:
            return None, None, CONFIDENCE_UNMATCHED
        return best_id, best_record, best_score

    def match_rows(
        self,
        target: EngineeringIdentity,
        rows: List[dict[str, Any]],
        beam_mark: str,
        id_field: str,
    ) -> Tuple[Optional[str], Optional[dict[str, Any]], int]:
        candidates = []
        for row in rows:
            identity = identity_from_pipeline_row(beam_mark, row)
            candidates.append((str(row.get(id_field) or row.get("row_id") or ""), identity, row))
        return self.find_best_match(target, candidates)

    def match_records(
        self,
        target: EngineeringIdentity,
        records: List[dict[str, Any]],
        beam_field: str,
        id_field: str,
        identity_builder,
    ) -> Tuple[Optional[str], Optional[dict[str, Any]], int]:
        candidates = []
        for record in records:
            beam = str(record.get(beam_field) or record.get("beam_mark") or "")
            if beam != target.beam_mark:
                continue
            identity = identity_builder(record)
            candidates.append((str(record.get(id_field) or ""), identity, record))
        return self.find_best_match(target, candidates)


def _clean_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _diameters_compatible(left: Optional[float], right: Optional[float], tolerance: float = 0.001) -> bool:
    if left is None or right is None:
        return True
    return abs(float(left) - float(right)) <= tolerance


def _numeric_compatible(left: Optional[float], right: Optional[float], tolerance: float = 0.001) -> bool:
    if left is None or right is None:
        return True
    return abs(float(left) - float(right)) <= tolerance


def _optional_match(left: Optional[str], right: Optional[str]) -> bool:
    if not left or not right:
        return True
    return re.sub(r"\s+", " ", left.strip().lower()) == re.sub(r"\s+", " ", right.strip().lower())
