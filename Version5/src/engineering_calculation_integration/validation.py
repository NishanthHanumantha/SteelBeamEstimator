"""Deterministic validation for calculation integration repair."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from src.engineering_calculation_integration.integration_helpers import (
    index_calc_results,
    is_production_calc_success,
)


class IntegrationValidator:
    """Validate recovered bar integration through production pipeline."""

    def validate(self, result: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        recovered_bar_ids = set(snapshot.get("recovered_bar_ids") or [])
        model = result.get("model") or {}
        bars = model.get("reinforcement_bars") or []
        contribution = result.get("contribution") or {}
        records = contribution.get("records") or []
        regression = result.get("regression") or {}

        checks = [
            self._check("Model Version 5.27.0", result.get("model_version") == "5.27.0"),
            self._check("Production Integration Executed", result.get("integration_status") == "SUCCESS"),
            self._check("Every Recovered Bar Registered", len(records) == len(recovered_bar_ids)),
            self._check(
                "BAR_IDENTITY Created",
                contribution.get("identity_success_count", 0) == len(recovered_bar_ids),
            ),
            self._check(
                "Readiness Registry Updated",
                (result.get("readiness_registry") or {}).get("bar_count") == len(bars),
            ),
            self._check(
                "Dependency Graph Updated",
                bool((result.get("dependency_graph_integration") or {}).get("dependency_graph")),
            ),
            self._check(
                "Calculation Context Present",
                bool(result.get("calculation_context_integration")),
            ),
            self._check(
                "Cut Length Generated",
                contribution.get("cut_length_count", 0) == len(recovered_bar_ids),
            ),
            self._check(
                "Steel Weight Generated",
                contribution.get("steel_count", 0) == len(recovered_bar_ids),
            ),
            self._check(
                "BBS Updated",
                contribution.get("bbs_count", 0) == len(recovered_bar_ids),
            ),
            self._check("Excel Updated", bool(model.get("excel_export_registry") or model.get("excel_export_statistics"))),
            self._check(
                "Calculation Index Assigned",
                all((bar.get("calculation_index") or {}).get("references") for bar in bars if bar.get("bar_id") in recovered_bar_ids),
            ),
            self._check("No Duplicate Identities", self._no_duplicate_identities(model, recovered_bar_ids)),
            self._check("Existing Production Outputs Preserved", regression.get("status") == "PASS"),
            self._check("Append-Only Integration Verified", len(bars) >= len(snapshot.get("bars") or [])),
            self._check("Full Traceability Preserved", self._traceability_preserved(bars, recovered_bar_ids)),
        ]
        failed = [item for item in checks if item["status"] == "FAIL"]
        return {
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
            },
        }

    @staticmethod
    def _no_duplicate_identities(model: dict[str, Any], recovered_bar_ids: Set[str]) -> bool:
        marks: set[str] = set()
        identity_calc = index_calc_results(model.get("engineering_calculation_results") or [], "BAR_IDENTITY")
        for bar_id in recovered_bar_ids:
            calc_result = identity_calc.get(bar_id)
            if is_production_calc_success(calc_result):
                mark = str(calc_result.get("result_value") or "")
            else:
                record = next(
                    (item for item in model.get("bar_identity_results") or [] if item.get("bar_id") == bar_id),
                    {},
                )
                mark = str(record.get("engineering_bar_mark") or record.get("engineering_bar_id") or "")
            if not mark:
                return False
            if mark in marks:
                return False
            marks.add(mark)
        return len(marks) == len(recovered_bar_ids)

    @staticmethod
    def _traceability_preserved(bars: List[dict[str, Any]], recovered_bar_ids: Set[str]) -> bool:
        for bar in bars:
            if str(bar.get("bar_id") or "") not in recovered_bar_ids:
                continue
            trace = bar.get("traceability") or {}
            if not trace.get("recovery_source") or not trace.get("discovery_id"):
                return False
        return True

    @staticmethod
    def _check(name: str, passed: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
