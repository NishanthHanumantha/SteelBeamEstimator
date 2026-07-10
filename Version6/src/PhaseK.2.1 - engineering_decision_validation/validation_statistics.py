"""Statistics for Engineering Decision Validation."""

from __future__ import annotations

from typing import Any, List

from decision_validation_types import ValidationStatus


class ValidationStatistics:
    """Compute validation KPIs and health."""

    @staticmethod
    def build(
        decisions: List[dict[str, Any]],
        validations: List[dict[str, Any]],
        duration_s: float,
    ) -> dict[str, Any]:
        valid = [
            item
            for item in validations
            if item.get("validation_status") == ValidationStatus.VALID.value
        ]
        invalid = [
            item
            for item in validations
            if item.get("validation_status") == ValidationStatus.INVALID.value
        ]
        warning = [
            item
            for item in validations
            if item.get("validation_status") == ValidationStatus.WARNING.value
            or (
                item.get("validation_warnings")
                and item.get("validation_status") == ValidationStatus.VALID.value
            )
        ]
        allowed = [item for item in validations if item.get("execution_allowed")]
        blocked = [item for item in validations if not item.get("execution_allowed")]
        scores = [float(item.get("validation_score") or 0.0) for item in validations]
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        broken_refs = sum(
            1
            for item in validations
            for err in (item.get("validation_errors") or [])
            if "exists" in str(err.get("message") or "").lower()
            or "reference" in str(err.get("message") or "").lower()
            or "lineage" in str(err.get("message") or "").lower()
        )
        broken_trace = sum(
            1
            for item in validations
            for err in (item.get("validation_errors") or [])
            if str(err.get("group") or "") == "TRACEABILITY"
        )
        duplicate_targets = sum(
            1
            for item in validations
            for err in (item.get("validation_errors") or [])
            if "duplicate" in str(err.get("message") or "").lower()
        )
        missing_targets = sum(
            1
            for item in validations
            for err in (item.get("validation_errors") or [])
            if "missing" in str(err.get("message") or "").lower()
            or "target exists" in str(err.get("message") or "").lower()
        )
        coverage = round((len(validations) / len(decisions)) * 100, 2) if decisions else 100.0
        return {
            "engineering_decisions": len(decisions),
            "validated_decisions": len(valid),
            "invalid_decisions": len(invalid),
            "warning_decisions": len(warning),
            "average_validation_score": avg_score,
            "validation_coverage_percent": coverage,
            "execution_allowed": len(allowed),
            "execution_blocked": len(blocked),
            "broken_references": broken_refs,
            "duplicate_execution_targets": duplicate_targets,
            "duplicate_targets": duplicate_targets,
            "missing_targets": missing_targets,
            "broken_traceability": broken_trace,
            "average_validation_time_s": round(duration_s / max(len(validations), 1), 6),
            "validation_time_s": round(duration_s, 3),
            "overall_validation_health": "HEALTHY" if not invalid and coverage == 100.0 else "ATTENTION",
        }

    @staticmethod
    def build_health(statistics: dict[str, Any]) -> dict[str, Any]:
        invalid = int(statistics.get("invalid_decisions") or 0)
        coverage = float(statistics.get("validation_coverage_percent") or 0.0)
        avg = float(statistics.get("average_validation_score") or 0.0)
        health = "HEALTHY"
        if invalid > 0 or coverage < 100.0 or avg < 100.0:
            health = "ATTENTION"
        if invalid > 0 and avg < 90.0:
            health = "DEGRADED"
        return {
            "validation_health": health,
            "execution_health": "HEALTHY" if invalid == 0 else "BLOCKED",
            "validation_coverage_percent": coverage,
            "average_validation_score": avg,
            "invalid_decisions": invalid,
            "broken_traceability": statistics.get("broken_traceability", 0),
            "overall_validation_health": statistics.get("overall_validation_health"),
        }

    @staticmethod
    def build_summary(
        statistics: dict[str, Any],
        health: dict[str, Any],
        validation_status: str,
    ) -> dict[str, Any]:
        return {
            "engineering_decisions": statistics.get("engineering_decisions", 0),
            "validated_decisions": statistics.get("validated_decisions", 0),
            "invalid_decisions": statistics.get("invalid_decisions", 0),
            "warning_decisions": statistics.get("warning_decisions", 0),
            "average_validation_score": statistics.get("average_validation_score", 0.0),
            "validation_coverage_percent": statistics.get("validation_coverage_percent", 0.0),
            "execution_allowed": statistics.get("execution_allowed", 0),
            "execution_blocked": statistics.get("execution_blocked", 0),
            "broken_references": statistics.get("broken_references", 0),
            "duplicate_execution_targets": statistics.get("duplicate_execution_targets", 0),
            "missing_targets": statistics.get("missing_targets", 0),
            "broken_traceability": statistics.get("broken_traceability", 0),
            "validation_health": health.get("validation_health"),
            "execution_health": health.get("execution_health"),
            "overall_validation_health": health.get("overall_validation_health"),
            "validation_status": validation_status,
        }
