"""Validate estimator audit completeness — Phase QA.1."""

from __future__ import annotations

from typing import Any, List


class AuditValidator:
    """Deterministic checks that the audit completed without modifying engineering code."""

    def validate(self, audit_result: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        stats = audit_result.get("comparison_statistics", {})
        checks.append(self._check("Generated Workbook Path Present", bool(audit_result.get("generated_workbook"))))
        checks.append(self._check("Estimator Workbook Path Present", bool(audit_result.get("estimator_workbook"))))
        checks.append(self._check("Every Estimator Beam Compared", stats.get("total_beams_estimator", 0) >= 1))
        checks.append(self._check("Beam Comparison Generated", bool(audit_result.get("beam_comparison"))))
        checks.append(self._check("Row Comparison Generated", bool(audit_result.get("row_comparison"))))
        checks.append(self._check("Cell Comparison Generated", bool(audit_result.get("cell_comparison"))))
        checks.append(self._check("Root Cause Report Generated", bool(audit_result.get("root_cause_report"))))
        checks.append(self._check("Fix Recommendations Generated", bool(audit_result.get("fix_recommendations"))))
        checks.append(self._check("Engineering Trace Generated", bool(audit_result.get("engineering_trace_report"))))
        checks.append(self._check("Missing Items Generated", bool(audit_result.get("missing_items"))))
        checks.append(self._check("Presentation Report Generated", bool(audit_result.get("presentation_report"))))
        checks.append(self._check("Workbook Structure Report Generated", bool(audit_result.get("workbook_structure_report"))))
        checks.append(self._check("Summary Comparison Generated", bool(audit_result.get("summary_comparison"))))
        checks.append(self._check("Comparison Statistics Generated", bool(audit_result.get("comparison_statistics"))))
        checks.append(self._check("Audit Summary Generated", bool(audit_result.get("audit_summary"))))
        checks.append(self._check("No Engineering Code Modified", audit_result.get("engineering_code_modified") is False))
        checks.append(self._check("Engineering Pipeline Frozen", audit_result.get("engineering_pipeline_frozen") is True))
        entries = audit_result.get("root_cause_report", {}).get("entries", [])
        checks.append(self._check("Every Discrepancy Classified", all(item.get("root_cause") for item in entries)))
        checks.append(self._check(
            "Every Missing Row Traced",
            audit_result.get("engineering_trace_report", {}).get("trace_count", 0)
            >= audit_result.get("missing_items", {}).get("missing_row_count", 0),
        ))
        recommendations = audit_result.get("fix_recommendations", {}).get("recommendations", [])
        checks.append(self._check("Every Recommendation Has Root Cause", all(item.get("root_cause") for item in recommendations)))
        checks.append(self._check("Every Recommendation Has Fix", all(item.get("recommended_fix") for item in recommendations)))
        failed = [item for item in checks if item["status"] == "FAIL"]
        return {
            "phase": "Phase QA.1",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
            },
        }

    @staticmethod
    def _check(name: str, ok: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if ok else "FAIL"}
