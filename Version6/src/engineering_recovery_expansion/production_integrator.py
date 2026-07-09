"""Integrate approved expansion recoveries through existing J.1 production engines."""

from __future__ import annotations

from typing import Any, Dict, List


class ProductionIntegrator:
    """Reuse J.1 recovery builders and J.1.3 calculation integration."""

    def integrate(
        self,
        snapshot: dict[str, Any],
        approved: List[dict[str, Any]],
        recovery_decisions: List[dict[str, Any]],
    ) -> dict[str, Any]:
        from src.engineering_calculation_integration.integration_engine import IntegrationEngine
        from src.engineering_recovery.recovery_collector import RecoveryCollector
        from src.engineering_recovery.recovery_object_builder import RecoveryObjectBuilder
        from src.engineering_recovery.recovery_pipeline_integrator import RecoveryPipelineIntegrator
        from src.engineering_recovery_expansion.expansion_builder import ExpansionBuilder

        if not approved:
            existing_expansion = snapshot.get("expansion_registry_entries") or []
            if existing_expansion:
                recovery_snapshot = RecoveryCollector(self._project_root).collect()
                integrator = RecoveryPipelineIntegrator(self._project_root)
                pipeline_result = integrator.complete_pipeline(recovery_snapshot)
                return {
                    "status": "IDEMPOTENT_SKIP",
                    "reason": "Existing expansion recoveries preserved",
                    "production_merge": {
                        "status": pipeline_result.get("status"),
                        "reason": pipeline_result.get("reason"),
                    },
                    "calculation_integration": {
                        "status": "SKIPPED",
                        "validation": "SKIPPED",
                        "integration_mode": "IDEMPOTENT_SKIP",
                    },
                }
            return {"status": "SKIPPED", "reason": "No approved expansion recoveries"}

        object_builder = RecoveryObjectBuilder(dict(snapshot.get("id_counters") or {}))
        built = object_builder.build_all(
            recovery_decisions,
            snapshot.get("contexts_by_beam") or {},
            snapshot.get("project_workspace") or {},
        )
        normalized_bars, normalized_groups, registry = object_builder.normalize_recovered(
            built.get("specifications") or [],
            built.get("contexts") or [],
        )
        built["registry"] = registry
        self._patch_expansion_metadata(
            built.get("recovered_objects") or [],
            built.get("specifications") or [],
            built.get("contexts") or [],
            normalized_bars,
            normalized_groups,
            approved,
        )

        recovery_snapshot = RecoveryCollector(self._project_root).collect()
        integrator = RecoveryPipelineIntegrator(self._project_root)
        production_merge = integrator.integrate(
            recovery_snapshot,
            built,
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
            "recovered_objects": built.get("recovered_objects") or [],
            "recovered_count": len(built.get("recovered_objects") or []),
            "calculation_integration": {
                "status": calc_result.get("integration_status"),
                "validation": calc_result.get("integration_validation", {}).get("status"),
                "integration_mode": (calc_result.get("production_pipeline_integration") or {}).get(
                    "integration_mode"
                ),
            },
        }

    def __init__(self, project_root) -> None:
        self._project_root = project_root

    @staticmethod
    def _patch_expansion_metadata(
        recovered_objects: List[dict[str, Any]],
        specifications: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        normalized_bars: List[dict[str, Any]],
        normalized_groups: List[dict[str, Any]],
        approved: List[dict[str, Any]],
    ) -> None:
        approved_by_id = {str(item.get("discovery_id")): item for item in approved}
        for obj in recovered_objects:
            discovery_id = str(obj.get("source_discovery_id") or "")
            approved_item = approved_by_id.get(discovery_id, {})
            obj["recovery_source"] = "Phase J.2"
            obj["recovery_version"] = "5.28.0"
            obj["expansion_class"] = approved_item.get("expansion_class")
            obj["expansion_similarity"] = approved_item.get("similarity_score")

        for spec in specifications:
            trace = dict(spec.get("traceability") or {})
            discovery_id = str(trace.get("discovery_id") or "")
            approved_item = approved_by_id.get(discovery_id, {})
            trace.update(
                {
                    "recovery_source": "Phase J.2",
                    "expansion_class": approved_item.get("expansion_class"),
                    "expansion_similarity": approved_item.get("similarity_score"),
                    "qa_coverage_4_rejection": approved_item.get("primary_rejection_code"),
                }
            )
            spec["traceability"] = trace

        for context in contexts:
            context["recovery_source"] = "Phase J.2"

        for bar in normalized_bars:
            trace = dict(bar.get("traceability") or {})
            discovery_id = str(trace.get("discovery_id") or "")
            approved_item = approved_by_id.get(discovery_id, {})
            trace.update(
                {
                    "recovery_source": "Phase J.2",
                    "expansion_class": approved_item.get("expansion_class"),
                    "expansion_similarity": approved_item.get("similarity_score"),
                }
            )
            bar["traceability"] = trace

        for group in normalized_groups:
            trace = dict(group.get("traceability") or {})
            trace["recovery_source"] = "Phase J.2"
            group["traceability"] = trace
