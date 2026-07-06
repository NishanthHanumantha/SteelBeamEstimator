"""Cross-layer identity matching — Phase QA.2."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.estimator_validation.comparison_utils import ScheduleRow
from src.estimator_validation.object_trace.identity_matcher import (
    IdentityMatcher,
    identity_from_bar_identity,
    identity_from_estimator_row,
    identity_from_pipeline_row,
)
from src.estimator_validation.object_trace.trace_types import (
    CONFIDENCE_UNMATCHED,
    EngineeringIdentity,
    LayerMatch,
)


class TraceMatcher:
    """Match a single estimator identity across all pipeline layers."""

    def __init__(self) -> None:
        self.matcher = IdentityMatcher()

    def match_excel_row(
        self,
        target: EngineeringIdentity,
        generated_rows: List[ScheduleRow],
    ) -> LayerMatch:
        candidates = []
        for row in generated_rows:
            identity = identity_from_estimator_row(target.beam_mark, row)
            candidates.append((str(row.row_number), identity, {"row_number": row.row_number}))
        record_id, _, score = self.matcher.find_best_match(target, candidates)
        if record_id is None:
            return LayerMatch(layer="excel", status="FAIL", confidence=CONFIDENCE_UNMATCHED)
        return LayerMatch(layer="excel", status="PASS", confidence=score, matched_id=record_id)

    def match_schedule_table(
        self,
        target: EngineeringIdentity,
        rows: List[dict[str, Any]],
        layer: str,
        id_field: str = "row_id",
    ) -> LayerMatch:
        record_id, _, score = self.matcher.match_rows(target, rows, target.beam_mark, id_field)
        if record_id is None:
            return LayerMatch(layer=layer, status="FAIL", confidence=CONFIDENCE_UNMATCHED)
        return LayerMatch(layer=layer, status="PASS", confidence=score, matched_id=record_id)

    def match_member_group(
        self,
        target: EngineeringIdentity,
        records: List[dict[str, Any]],
        layer: str,
        id_field: str,
    ) -> LayerMatch:
        candidates = []
        for record in records:
            member_beams = [str(item) for item in (record.get("member_beams") or [])]
            if target.beam_mark not in member_beams:
                continue
            roles = [str(item) for item in (record.get("member_roles") or [])]
            diameter = record.get("diameter") or record.get("diameter_mm")
            identity = EngineeringIdentity(
                beam_mark=target.beam_mark,
                role=roles[0] if len(roles) == 1 else target.role,
                diameter_mm=float(diameter) if diameter is not None else None,
                fabrication_mark=_clean(record.get("fabrication_mark")),
                shape_code=_clean(record.get("shape_code")),
            )
            if target.role not in roles and roles:
                continue
            candidates.append((str(record.get(id_field) or ""), identity, record))
        record_id, _, score = self.matcher.find_best_match(target, candidates)
        if record_id is None:
            return LayerMatch(layer=layer, status="FAIL", confidence=CONFIDENCE_UNMATCHED)
        return LayerMatch(layer=layer, status="PASS", confidence=score, matched_id=record_id)

    def match_beam_level(
        self,
        target: EngineeringIdentity,
        records: List[dict[str, Any]],
        layer: str,
        beam_field: str,
        id_field: str,
        role_field: str,
    ) -> LayerMatch:
        beam_records = [
            item for item in records
            if str(item.get(beam_field) or item.get("beam_mark")) == target.beam_mark
        ]
        if not beam_records:
            return LayerMatch(layer=layer, status="FAIL", confidence=CONFIDENCE_UNMATCHED)

        if layer in {"beam_summary", "quantity", "material"}:
            roles: set[str] = set()
            for item in beam_records:
                raw_roles = item.get("roles") or item.get("member_roles") or []
                if isinstance(raw_roles, list):
                    roles.update(str(role) for role in raw_roles)
                elif raw_roles:
                    roles.add(str(raw_roles))
                if item.get(role_field):
                    value = item.get(role_field)
                    if isinstance(value, list):
                        roles.update(str(role) for role in value)
                    else:
                        roles.add(str(value))
            if target.role in roles or any(
                target.role in [str(role) for role in (item.get("member_roles") or [])]
                for item in beam_records
            ):
                record_id = str(beam_records[0].get(id_field) or "")
                return LayerMatch(layer=layer, status="PASS", confidence=80, matched_id=record_id)
            return LayerMatch(layer=layer, status="FAIL", confidence=CONFIDENCE_UNMATCHED)

        candidates = []
        for record in beam_records:
            identity = identity_from_pipeline_row(target.beam_mark, record)
            if role_field and record.get(role_field):
                identity = EngineeringIdentity(
                    beam_mark=target.beam_mark,
                    role=str(record.get(role_field)),
                    diameter_mm=identity.diameter_mm,
                    fabrication_mark=identity.fabrication_mark,
                    shape_code=identity.shape_code,
                    description=identity.description,
                )
            candidates.append((str(record.get(id_field) or ""), identity, record))
        record_id, _, score = self.matcher.find_best_match(target, candidates)
        if record_id is None:
            return LayerMatch(layer=layer, status="FAIL", confidence=CONFIDENCE_UNMATCHED)
        return LayerMatch(layer=layer, status="PASS", confidence=score, matched_id=record_id)

    def match_bar_identities(
        self,
        target: EngineeringIdentity,
        records: List[dict[str, Any]],
    ) -> LayerMatch:
        record_id, _, score = self.matcher.match_records(
            target,
            records,
            beam_field="beam_id",
            id_field="bar_identity_id",
            identity_builder=identity_from_bar_identity,
        )
        if record_id is None:
            return LayerMatch(layer="identity", status="FAIL", confidence=CONFIDENCE_UNMATCHED)
        return LayerMatch(layer="identity", status="PASS", confidence=score, matched_id=record_id)

    def match_drawing_objects(
        self,
        target: EngineeringIdentity,
        records: List[dict[str, Any]],
    ) -> LayerMatch:
        candidates = []
        for record in records:
            beam = str(record.get("beam_id") or record.get("beam_mark") or "")
            if beam != target.beam_mark:
                continue
            role = str(record.get("reinforcement_role") or record.get("role") or "UNKNOWN")
            diameter = record.get("bar_diameter_mm") or record.get("diameter_mm")
            identity = EngineeringIdentity(
                beam_mark=beam,
                role=role,
                diameter_mm=float(diameter) if diameter is not None else None,
                description=_clean(record.get("description")),
            )
            obj_id = str(record.get("engineering_object_id") or record.get("object_id") or "")
            candidates.append((obj_id, identity, record))
        record_id, _, score = self.matcher.find_best_match(target, candidates)
        if record_id is None:
            return LayerMatch(layer="drawing", status="FAIL", confidence=CONFIDENCE_UNMATCHED)
        return LayerMatch(layer="drawing", status="PASS", confidence=score, matched_id=record_id)


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
