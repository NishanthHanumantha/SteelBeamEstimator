"""Integration repair reporting and health metrics."""

from __future__ import annotations

from typing import Any, Dict


class IntegrationReporting:
    """Build summary, statistics, and health metrics."""

    def build_statistics(self, result: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        contribution = result.get("contribution") or {}
        recovered_count = len(snapshot.get("recovered_bar_ids") or [])
        return {
            "recovered_bars": recovered_count,
            "registered_identities": contribution.get("identity_success_count", 0),
            "ready_bars": (result.get("readiness_registry") or {}).get("ready_bars", 0),
            "calculated_bars": contribution.get("cut_length_count", 0),
            "steel_generated": contribution.get("steel_count", 0),
            "bbs_generated": contribution.get("bbs_count", 0),
            "excel_generated": recovered_count if result.get("integration_status") == "SUCCESS" else 0,
            "integration_failures": max(
                0,
                recovered_count - contribution.get("identity_success_count", 0),
            ),
        }

    def build_health(self, statistics: dict[str, Any]) -> dict[str, Any]:
        recovered = max(statistics.get("recovered_bars", 1), 1)
        identity = round((statistics.get("registered_identities", 0) / recovered) * 100, 2)
        steel = round((statistics.get("steel_generated", 0) / recovered) * 100, 2)
        bbs = round((statistics.get("bbs_generated", 0) / recovered) * 100, 2)
        excel = round((statistics.get("excel_generated", 0) / recovered) * 100, 2)
        overall = round((identity * 0.35) + (steel * 0.25) + (bbs * 0.2) + (excel * 0.2), 2)
        return {
            "identity_integration_health": identity,
            "steel_integration_health": steel,
            "bbs_integration_health": bbs,
            "excel_integration_health": excel,
            "overall_integration_health": overall,
        }

    def build_summary(
        self,
        statistics: dict[str, Any],
        health: dict[str, Any],
        validation: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            **statistics,
            "integration_success_percent": round(
                (validation.get("summary", {}).get("passed", 0) / max(validation.get("summary", {}).get("total_checks", 1), 1))
                * 100,
                2,
            ),
            "integration_health": health,
            "recovery_contribution": result.get("contribution") or {},
            "no_regression_status": (result.get("regression") or {}).get("status"),
        }

    def build_report(self, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": result.get("phase"),
            "model_version": result.get("model_version"),
            "engine_version": result.get("engine_version"),
            "run_timestamp": result.get("run_timestamp"),
            "summary": result.get("integration_summary"),
            "statistics": result.get("integration_statistics"),
            "health": result.get("integration_health"),
            "validation": result.get("integration_validation"),
            "export_paths": result.get("export_paths"),
        }
