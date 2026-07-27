"""STEP 5 — Validate that recovered engineering text is complete."""
from __future__ import annotations

import re
from typing import List

from .mtext_models import MtextEntity, RecoveryRecord, ValidationRecord

_QTY_RX = re.compile(r"\b\d+\b")
_GRADE_DIA_RX = re.compile(r"[YyRrTt]\s*\d+")
_SPACING_RX = re.compile(r"@\s*\d+|\d+\s*/\s*\d+")
_ABBREV_RX = re.compile(r"S\.?F\.?R|O\.?E\.?F|\bLd\b|\bLap\b|\bHook\b", re.I)
_MODIFIER_RX = re.compile(r"\([^)]+\)")


class EngineeringTextValidator:

    def validate_all(
        self,
        records: List[RecoveryRecord],
    ) -> List[ValidationRecord]:
        return [self._validate(r) for r in records]

    def _validate(self, rec: RecoveryRecord) -> ValidationRecord:
        text = rec.new_clean_text
        issues = []

        has_qty = bool(_QTY_RX.search(text))
        has_dia = bool(_GRADE_DIA_RX.search(text))
        has_spacing = bool(_SPACING_RX.search(text))
        has_abbrev = bool(_ABBREV_RX.search(text))
        has_modifier = bool(_MODIFIER_RX.search(text))

        if not has_dia and not has_abbrev:
            issues.append("no_grade_diameter_or_abbreviation")
        if rec.new_status == "STILL_LOST":
            issues.append("text_still_empty_after_recovery")
        if rec.old_status == "LOST" and rec.new_status == "STILL_LOST":
            issues.append("engineering_text_still_lost")

        is_valid = has_dia or has_abbrev or has_spacing

        return ValidationRecord(
            entity_id=rec.entity_id,
            clean_text=text[:120],
            contains_quantity=has_qty,
            contains_diameter=has_dia,
            contains_spacing=has_spacing,
            contains_abbreviation=has_abbrev,
            contains_modifier=has_modifier,
            is_valid_engineering=is_valid,
            issues=issues,
        )
