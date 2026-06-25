"""Phase D.2 — validation for annotation parsing."""

from typing import Dict, List, Literal, TypedDict

from src.parsing.annotation_parsing_pipeline import ParsingResult, ParsedRecord

ValidationStatus = Literal["PASS", "WARN", "FAIL"]


class ParsingValidation(TypedDict):
    parser_ready_input_count: int
    parsed_successfully: int
    failed_parses: int
    unsupported_count: int
    coverage_pct: float
    bar_count: int
    stirrup_count: int
    anchorage_count: int
    side_face_reinf_count: int
    duplicate_annotation_id_count: int
    missing_mandatory_field_count: int
    status: ValidationStatus
    ready_for_phase_e: bool
    checks: Dict[str, bool]


_MANDATORY_BY_TYPE = {
    "BAR": ("quantity", "diameter_mm"),
    "STIRRUP": ("leg_count", "diameter_mm", "spacing_mm"),
    "ANCHORAGE": ("anchorage_type", "extension_db"),
    "SIDE_FACE_REINF": ("quantity", "diameter_mm"),
}


class AnnotationParsingValidator:
    """Validate parsed annotation coverage and field completeness."""

    def validate(self, result: ParsingResult) -> ParsingValidation:
        summary = result["summary"]
        master = result["master"]

        duplicate_ids = self._duplicate_annotation_ids(master)
        missing_fields = self._missing_mandatory_fields(
            [r for r in master if r.get("parser_status") == "PARSED"]
        )

        coverage = summary["coverage_pct"]
        if coverage >= 98.0:
            status: ValidationStatus = "PASS"
        elif coverage >= 95.0:
            status = "WARN"
        else:
            status = "FAIL"

        if missing_fields > 0 or duplicate_ids > 0:
            status = "FAIL"

        checks = {
            "parser_ready_count_recorded": summary["parser_ready_input_count"] > 0,
            "bar_present": summary["bar_count"] > 0,
            "stirrup_present": summary["stirrup_count"] > 0,
            "anchorage_present": summary["anchorage_count"] > 0,
            "coverage_pass": coverage >= 98.0,
            "no_duplicate_ids": duplicate_ids == 0,
            "no_missing_mandatory_fields": missing_fields == 0,
            "ready_for_phase_e": summary["ready_for_phase_e"],
        }

        return ParsingValidation(
            parser_ready_input_count=summary["parser_ready_input_count"],
            parsed_successfully=summary["parsed_successfully"],
            failed_parses=summary["failed_parses"],
            unsupported_count=summary["unsupported_count"],
            coverage_pct=summary["coverage_pct"],
            bar_count=summary["bar_count"],
            stirrup_count=summary["stirrup_count"],
            anchorage_count=summary["anchorage_count"],
            side_face_reinf_count=summary["side_face_reinf_count"],
            duplicate_annotation_id_count=duplicate_ids,
            missing_mandatory_field_count=missing_fields,
            status=status,
            ready_for_phase_e=summary["ready_for_phase_e"] and status != "FAIL",
            checks=checks,
        )

    def _duplicate_annotation_ids(self, records: List[ParsedRecord]) -> int:
        seen: set[str] = set()
        duplicates = 0
        for rec in records:
            aid = rec.get("annotation_id", "")
            if aid in seen:
                duplicates += 1
            seen.add(aid)
        return duplicates

    def _missing_mandatory_fields(self, parsed: list[ParsedRecord]) -> int:
        missing = 0
        for rec in parsed:
            fields = rec.get("parsed_fields", {})
            ann_type = rec.get("annotation_type", "")
            required = _MANDATORY_BY_TYPE.get(ann_type, ())
            for key in required:
                if key not in fields:
                    missing += 1
                    break
        return missing
