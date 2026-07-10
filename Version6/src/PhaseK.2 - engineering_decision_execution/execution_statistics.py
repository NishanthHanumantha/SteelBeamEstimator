"""Statistics for Engineering Decision Execution."""

from __future__ import annotations

from typing import Any, Dict, List


class ExecutionStatistics:
    """Compute execution KPIs and health."""

    @staticmethod
    def build(
        decisions: List[dict[str, Any]],
        selection: List[dict[str, Any]],
        registry: dict[str, Any],
        mapping: dict[str, Any],
        adapter_result: dict[str, Any],
        bridge_result: dict[str, Any],
    ) -> dict[str, Any]:
        executable = [item for item in selection if item.get("executable")]
        blocked = [item for item in selection if not item.get("executable")]
        lifecycle_counts: Dict[str, int] = {}
        for entry in registry.get("entries") or []:
            state = str(entry.get("lifecycle") or "UNKNOWN")
            lifecycle_counts[state] = lifecycle_counts.get(state, 0) + 1

        return {
            "engineering_decisions": len(decisions),
            "executable_decisions": len(executable),
            "not_executable_decisions": len(blocked),
            "execution_registry_count": registry.get("registry_count", 0),
            "execution_intent_count": len(mapping.get("execution_intent_ids") or []),
            "suppressed_intent_count": len(mapping.get("suppressed_intent_ids") or []),
            "executable_bar_count": len(mapping.get("executable_bar_ids") or []),
            "executable_beam_count": len(mapping.get("executable_beam_ids") or []),
            "lifecycle_counts": lifecycle_counts,
            "calculation_engine_invoked": bool(adapter_result.get("calculation_engine_invoked")),
            "formulas_modified": bool(adapter_result.get("formulas_modified")),
            "duplicated_calculations": bool(mapping.get("duplicated_calculations")),
            "production_bridge_status": bridge_result.get("status"),
            "decision_mapping_coverage_percent": (
                round((len(selection) / len(decisions)) * 100, 2) if decisions else 100.0
            ),
        }

    @staticmethod
    def build_health(statistics: dict[str, Any], bridge_result: dict[str, Any]) -> dict[str, Any]:
        coverage = float(statistics.get("decision_mapping_coverage_percent") or 0.0)
        health = "HEALTHY"
        if coverage < 100.0:
            health = "ATTENTION"
        if bridge_result.get("status") == "FAILED":
            health = "DEGRADED"
        return {
            "execution_health": health,
            "decision_mapping_coverage_percent": coverage,
            "calculation_engine_reused": not bool(statistics.get("duplicated_calculations")),
            "formulas_unchanged": not bool(statistics.get("formulas_modified")),
            "production_bridge_status": bridge_result.get("status"),
        }

    @staticmethod
    def build_summary(
        statistics: dict[str, Any],
        health: dict[str, Any],
        validation_status: str,
    ) -> dict[str, Any]:
        return {
            "engineering_decisions": statistics.get("engineering_decisions", 0),
            "executable_decisions": statistics.get("executable_decisions", 0),
            "not_executable_decisions": statistics.get("not_executable_decisions", 0),
            "execution_registry_count": statistics.get("execution_registry_count", 0),
            "decision_mapping_coverage_percent": statistics.get("decision_mapping_coverage_percent", 0.0),
            "calculation_engine_invoked": statistics.get("calculation_engine_invoked", False),
            "formulas_modified": statistics.get("formulas_modified", False),
            "duplicated_calculations": statistics.get("duplicated_calculations", False),
            "execution_health": health.get("execution_health"),
            "validation_status": validation_status,
        }
