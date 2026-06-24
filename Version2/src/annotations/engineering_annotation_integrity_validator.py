"""Phase D.1.7C — validation for engineering annotation integrity audit."""

from typing import Any, Dict, Literal, TypedDict

from src.annotations.engineering_annotation_integrity_auditor import (
    AuditResult,
    IntegritySummary,
    ParserReadiness,
)

ValidationStatus = Literal["PASS", "WARN", "FAIL"]


class IntegrityValidation(TypedDict):
    truncated_fragments_found: int
    suspicious_fragments_found: int
    incomplete_stirrups_found: int
    invalid_stirrups_found: int
    invalid_anchorage_entries_found: int
    suspicious_anchorage_entries_found: int
    invalid_sfr_entries_found: int
    partial_sfr_entries_found: int
    duplicate_ownership_issues: int
    type_mismatches: int
    false_rejections: int
    parser_readiness_score: str
    recommendation: str
    checks: Dict[str, bool]
    status: ValidationStatus


class EngineeringAnnotationIntegrityValidator:
    """Summarize audit outcomes into PASS / WARN / FAIL."""

    def validate(self, audit_result: AuditResult) -> IntegrityValidation:
        summary = audit_result["summary"]
        readiness = audit_result["parser_readiness"]
        rejected = audit_result["rejected_review"]

        checks = {
            "engineering_annotations_audited": readiness["total_engineering_annotations"] > 0,
            "no_suspicious_fragments": summary["suspicious_fragments_found"] == 0,
            "no_incomplete_stirrups": summary["incomplete_stirrups_found"] == 0,
            "no_invalid_stirrups": summary["invalid_stirrups_found"] == 0,
            "no_suspicious_anchorage": summary["suspicious_anchorage_entries_found"] == 0,
            "no_invalid_sfr": summary["invalid_sfr_entries_found"] == 0,
            "no_type_mismatches": summary["type_mismatches"] == 0,
            "no_false_rejections": summary["false_rejections"] == 0,
            "no_duplicate_ownership": summary["duplicate_ownership_issues"] == 0,
            "parser_readiness_pass": readiness["readiness_score"] == "PASS",
            "rejected_review_complete": rejected["total_rejected"] > 0,
        }

        if readiness["readiness_score"] == "FAIL":
            status: ValidationStatus = "FAIL"
        elif readiness["readiness_score"] == "WARN" or summary["false_rejections"] > 0:
            status = "WARN"
        elif all(checks.values()):
            status = "PASS"
        else:
            status = "WARN"

        return IntegrityValidation(
            truncated_fragments_found=summary["truncated_fragments_found"],
            suspicious_fragments_found=summary["suspicious_fragments_found"],
            incomplete_stirrups_found=summary["incomplete_stirrups_found"],
            invalid_stirrups_found=summary["invalid_stirrups_found"],
            invalid_anchorage_entries_found=summary["invalid_anchorage_entries_found"],
            suspicious_anchorage_entries_found=summary["suspicious_anchorage_entries_found"],
            invalid_sfr_entries_found=summary["invalid_sfr_entries_found"],
            partial_sfr_entries_found=summary["partial_sfr_entries_found"],
            duplicate_ownership_issues=summary["duplicate_ownership_issues"],
            type_mismatches=summary["type_mismatches"],
            false_rejections=summary["false_rejections"],
            parser_readiness_score=summary["parser_readiness_score"],
            recommendation=summary["recommendation"],
            checks=checks,
            status=status,
        )
