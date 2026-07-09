"""Integrate reconstructed intent objects into production pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


class ProductionIntegrator:
    """Reuse J.1 production merge and J.1.3 calculation integration."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def integrate(
        self,
        snapshot: dict[str, Any],
        built: dict[str, Any],
        normalized_bars: List[dict[str, Any]],
        normalized_groups: List[dict[str, Any]],
    ) -> dict[str, Any]:
        from src.engineering_calculation_integration.integration_engine import IntegrationEngine
        from src.engineering_intent.intent_collector import IntentCollector
        from src.engineering_recovery.recovery_pipeline_integrator import RecoveryPipelineIntegrator

        if not normalized_bars:
            existing_registry = snapshot.get("intent_registry_entries") or []
            if existing_registry:
                fresh_snapshot = IntentCollector(self._project_root).collect()
                integrator = RecoveryPipelineIntegrator(self._project_root)
                pipeline_result = integrator.complete_pipeline(fresh_snapshot)
                return {
                    "status": "IDEMPOTENT_SKIP",
                    "reason": "Existing intent objects preserved",
                    "production_merge": {
                        "status": pipeline_result.get("status"),
                        "reason": pipeline_result.get("reason"),
                    },
                    "calculation_integration": {"status": "SKIPPED", "validation": "SKIPPED"},
                }
            return {"status": "SKIPPED", "reason": "No reconstructed intent bars"}

        recovery_built = {
            "engineering_objects": built.get("engineering_objects") or [],
            "specifications": built.get("specifications") or [],
            "contexts": built.get("contexts") or [],
            "registry": built.get("registry"),
        }
        fresh_snapshot = IntentCollector(self._project_root).collect()
        integrator = RecoveryPipelineIntegrator(self._project_root)
        production_merge = integrator.integrate(
            fresh_snapshot,
            recovery_built,
            normalized_bars,
            normalized_groups,
        )
        calc_result = IntegrationEngine(self._project_root).run()
        return {
            "status": "SUCCESS",
            "production_merge": {
                "status": production_merge.get("status"),
                "reason": production_merge.get("reason"),
            },
            "normalized_bars": normalized_bars,
            "normalized_groups": normalized_groups,
            "reconstructed_count": len(normalized_bars),
            "calculation_integration": {
                "status": calc_result.get("integration_status"),
                "validation": calc_result.get("integration_validation", {}).get("status"),
                "integration_mode": (calc_result.get("production_pipeline_integration") or {}).get(
                    "integration_mode"
                ),
            },
        }

    @staticmethod
    def _to_recovery_built(
        registry_entries: List[dict[str, Any]],
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "existing_objects": snapshot.get("existing_objects") or [],
            "existing_specs": snapshot.get("existing_specs") or [],
            "existing_contexts": snapshot.get("existing_contexts") or [],
            "existing_bars": snapshot.get("existing_bars") or [],
            "existing_groups": snapshot.get("existing_groups") or [],
            "intent_registry_entries": registry_entries,
        }
