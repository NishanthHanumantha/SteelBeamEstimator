"""Estimator audit reporting — Phase QA.1."""

from __future__ import annotations

from typing import Any, List


class AuditReporting:
    @staticmethod
    def build(audit_result: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
        root_entries = audit_result.get("root_cause_report", {}).get("entries", [])
        ranked = sorted(
            root_entries,
            key=lambda item: {
                "CRITICAL": 0,
                "HIGH": 1,
                "MEDIUM": 2,
                "LOW": 3,
                "INFO": 4,
            }.get(item.get("severity", "MEDIUM"), 2),
        )
        return {
            "phase": audit_result.get("phase"),
            "summary": summary,
            "top_discrepancies": ranked[:20],
            "validation_status": audit_result.get("validation_report", {}).get("status", "PENDING"),
        }
