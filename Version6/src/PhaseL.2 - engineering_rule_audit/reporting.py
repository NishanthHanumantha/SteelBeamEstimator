"""Build all Phase L.2 report payloads."""

from __future__ import annotations

from typing import Any, Dict, List

from audit_loader import PHASE, MODEL_VERSION


class AuditReporting:
    """Assemble structured report payloads."""

    @staticmethod
    def build_implementation_matrix(
        role_audit: List[Dict[str, Any]],
        status_classifications: List[Dict[str, Any]],
        breaks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        status_by_role = {s["role"]: s for s in status_classifications}
        break_by_role = {b["role"]: b for b in breaks}
        rows: List[Dict[str, Any]] = []
        for row in role_audit:
            role = row["role"]
            st = status_by_role.get(role, {})
            brk = break_by_role.get(role, {})

            def _yn(v: Any) -> str:
                if v is True or (isinstance(v, int) and v > 0):
                    return "YES"
                if v == "PARTIAL":
                    return "PARTIAL"
                return "NO"

            rows.append({
                "role": role,
                "detected": _yn(row.get("detected")),
                "parsed": _yn(row.get("parsed")),
                "geometry": _yn(row.get("geometry")),
                "ownership": _yn(row.get("ownership")),
                "context": _yn(row.get("context")),
                "rule_exists": _yn(row.get("rule_exists")),
                "rule_executed": _yn(row.get("rule_executed")),
                "quantity": _yn(row.get("quantity")),
                "exported": _yn(row.get("exported")),
                "estimator_match": _yn(row.get("estimator_match")),
                "final_status": st.get("implementation_status", "UNKNOWN"),
                "break_stage": brk.get("break_stage"),
                "break_category": brk.get("break_category"),
            })
        return {"row_count": len(rows), "rows": rows}

    @staticmethod
    def build_beam_audit(pipeline_trace: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "per_beam_traces": pipeline_trace.get("per_beam_traces") or [],
            "stage_counts": pipeline_trace.get("stage_counts") or {},
        }

    @staticmethod
    def build_report(result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "run_timestamp": result.get("run_timestamp"),
            "data_source": result.get("data_source"),
            "validation_status": (result.get("validation") or {}).get("status"),
            "coverage_statistics": result.get("coverage_statistics"),
            "implementation_matrix_row_count": len((result.get("implementation_matrix") or {}).get("rows") or []),
            "rule_inventory_count": (result.get("rule_inventory") or {}).get("total_rules_discovered", 0),
            "dead_code_candidates": (result.get("rule_inventory") or {}).get("dead_code_candidates", 0),
        }

    @staticmethod
    def build_summary(
        coverage: Dict[str, Any],
        status_classifications: List[Dict[str, Any]],
        breaks: List[Dict[str, Any]],
        validation_status: str,
    ) -> Dict[str, Any]:
        return {
            "implemented_percent": coverage.get("implemented_percent"),
            "executed_percent": coverage.get("executed_percent"),
            "reachable_percent": coverage.get("reachable_percent"),
            "exported_percent": coverage.get("exported_percent"),
            "estimator_coverage_percent": coverage.get("estimator_coverage_percent"),
            "dead_code_percent": coverage.get("dead_code_percent"),
            "pipeline_completion_percent": coverage.get("pipeline_completion_percent"),
            "total_roles_audited": coverage.get("total_roles_audited"),
            "fully_implemented": coverage.get("fully_implemented"),
            "partially_executed": coverage.get("partially_executed"),
            "not_implemented": coverage.get("not_implemented"),
            "validation_status": validation_status,
        }
