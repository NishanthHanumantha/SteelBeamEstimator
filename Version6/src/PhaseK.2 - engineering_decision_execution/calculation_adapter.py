"""Adapt Engineering Decisions to existing production calculation engines."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class CalculationAdapter:
    """Reuse IntegrationEngine without modifying engineering formulas."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def adapt(
        self,
        mapping: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        if not config.get("enable", True):
            return {
                "status": "DISABLED",
                "reason": "Decision execution disabled — Version5-compatible path.",
                "calculation_engine_invoked": False,
                "engine": None,
                "duplicated_formulas": False,
            }

        if not config.get("invoke_calculation_engine", True):
            return {
                "status": "SKIPPED",
                "reason": "invoke_calculation_engine=false",
                "calculation_engine_invoked": False,
                "engine": "IntegrationEngine",
                "duplicated_formulas": False,
                "execution_intent_count": len(mapping.get("execution_intent_ids") or []),
            }

        if not mapping.get("executable_decision_count"):
            return {
                "status": "SKIPPED",
                "reason": "No executable engineering decisions.",
                "calculation_engine_invoked": False,
                "engine": "IntegrationEngine",
                "duplicated_formulas": False,
            }

        from src.engineering_calculation_integration.integration_engine import IntegrationEngine

        calc_result = IntegrationEngine(self._project_root).run()
        return {
            "status": "SUCCESS",
            "reason": "Existing IntegrationEngine reused for decision-driven execution.",
            "calculation_engine_invoked": True,
            "engine": "src.engineering_calculation_integration.IntegrationEngine",
            "duplicated_formulas": False,
            "formulas_modified": False,
            "integration_status": calc_result.get("integration_status"),
            "integration_validation": (calc_result.get("integration_validation") or {}).get("status"),
            "integration_mode": (calc_result.get("production_pipeline_integration") or {}).get(
                "integration_mode"
            ),
            "execution_intent_count": len(mapping.get("execution_intent_ids") or []),
            "executable_bar_count": len(mapping.get("executable_bar_ids") or []),
            "executable_beam_count": len(mapping.get("executable_beam_ids") or []),
        }
