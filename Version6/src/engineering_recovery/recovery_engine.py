"""Engineering Object Recovery orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.engineering_recovery.export import (
    EXPORT_FILES,
    RecoveryExporter,
    RecoveryExportValidator,
)
from src.engineering_recovery.recovery_candidate_builder import RecoveryCandidateBuilder
from src.engineering_recovery.recovery_collector import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
    RecoveryCollector,
    default_paths,
)
from src.engineering_recovery.recovery_decision_engine import RecoveryDecisionEngine
from src.engineering_recovery.recovery_object_builder import RecoveryObjectBuilder
from src.engineering_recovery.recovery_registry import RecoveryRegistry
from src.engineering_recovery.recovery_reporting import RecoveryReporting
from src.engineering_recovery.recovery_traceability import RecoveryTraceabilityBuilder
from src.engineering_recovery.recovery_validator import RecoveryValidator


class RecoveryEngine:
    """Run deterministic engineering object recovery."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        snapshot = RecoveryCollector(self._project_root).collect()
        existing_bars = snapshot.get("existing_bars") or []
        existing_recovery_bars = [
            bar
            for bar in existing_bars
            if (bar.get("traceability") or {}).get("recovery_source")
        ]
        existing_recovery_ids = {
            str((bar.get("traceability") or {}).get("discovery_id"))
            for bar in existing_recovery_bars
            if (bar.get("traceability") or {}).get("discovery_id")
        }

        candidates = RecoveryCandidateBuilder().build(snapshot)
        decisions = RecoveryDecisionEngine().evaluate_all(candidates)
        approved = [item for item in decisions if item.get("recover")]
        rejected = [item for item in decisions if not item.get("recover")]
        approved = [item for item in approved if item.get("discovery_id") not in existing_recovery_ids]

        existing_bar_count = len([bar for bar in existing_bars if not (bar.get("traceability") or {}).get("recovery_source")])
        inventory_count = len(snapshot.get("inventory") or [])
        reporting = RecoveryReporting()
        steel_before = reporting.compute_steel_coverage(
            len([bar for bar in existing_bars if not (bar.get("traceability") or {}).get("recovery_source")]),
            inventory_count,
        )

        recovered_objects: List[dict[str, Any]] = []
        normalized_bars: List[dict[str, Any]] = []
        normalized_groups: List[dict[str, Any]] = []
        production_merge: dict[str, Any] = {"status": "SKIPPED", "reason": "No approved recoveries"}

        if approved:
            object_builder = RecoveryObjectBuilder(dict(snapshot.get("id_counters") or {}))
            built = object_builder.build_all(
                approved,
                snapshot.get("contexts_by_beam") or {},
                snapshot.get("project_workspace") or {},
            )
            recovered_objects = built.get("recovered_objects") or []
            normalized_bars, normalized_groups, registry = object_builder.normalize_recovered(
                built.get("specifications") or [],
                built.get("contexts") or [],
            )
            built["registry"] = registry
            from src.engineering_recovery.recovery_pipeline_integrator import RecoveryPipelineIntegrator

            integrator = RecoveryPipelineIntegrator(self._project_root)
            production_merge = integrator.integrate(snapshot, built, normalized_bars, normalized_groups)
        elif existing_recovery_bars:
            recovered_objects = self._recovered_objects_from_bars(existing_recovery_bars, decisions)
            normalized_bars = existing_recovery_bars
            normalized_groups = [
                group
                for group in (snapshot.get("existing_groups") or [])
                if str(group.get("group_id")) in {str(bar.get("group_id")) for bar in existing_recovery_bars if bar.get("group_id")}
            ]
            from src.engineering_recovery.recovery_pipeline_integrator import RecoveryPipelineIntegrator

            integrator = RecoveryPipelineIntegrator(self._project_root)
            production_merge = integrator.complete_pipeline(snapshot)

        recovered_for_validation = recovered_objects or self._recovered_objects_from_bars(existing_recovery_bars, decisions)
        approved_decisions = [item for item in decisions if item.get("recover")]
        registry_entries = RecoveryRegistry().build_entries(
            recovered_for_validation,
            approved_decisions,
            normalized_bars or existing_recovery_bars,
        )
        traceability = RecoveryTraceabilityBuilder().build_all(
            recovered_for_validation,
            registry_entries,
            normalized_bars or existing_recovery_bars,
        )
        statistics = reporting.build_statistics(
            candidates,
            decisions,
            recovered_objects or self._recovered_objects_from_bars(existing_recovery_bars, decisions),
            rejected,
            normalized_bars or existing_recovery_bars,
            existing_bar_count,
        )
        steel_after = reporting.compute_steel_coverage(
            existing_bar_count + len(normalized_bars or existing_recovery_bars),
            inventory_count,
        )
        health = reporting.build_health(statistics, steel_before, steel_after)
        summary = reporting.build_summary(statistics, health, rejected)

        result: dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "read_only_analysis": False,
            "production_enhancement": True,
            "parser_executed": False,
            "discovery_rerun": False,
            "load_status": snapshot.get("load_status"),
            "candidates": candidates,
            "decisions": decisions,
            "recovered_objects": recovered_objects or self._recovered_objects_from_bars(existing_recovery_bars, decisions),
            "recovery_registry": RecoveryRegistry.build_registry_payload(registry_entries),
            "traceability": traceability,
            "statistics": statistics,
            "health": health,
            "summary": summary,
            "production_merge": production_merge,
            "normalized_bars": normalized_bars or existing_recovery_bars,
            "normalized_groups": normalized_groups,
            "existing_recovery_bars": existing_recovery_bars,
        }

        validator = RecoveryValidator()
        recovered_for_validation = recovered_objects or self._recovered_objects_from_bars(existing_recovery_bars, decisions)
        approved_decisions = [item for item in decisions if item.get("recover")]
        result["candidate_validation"] = validator.validate_candidates(candidates, decisions)
        result["recovery_validation"] = validator.validate_recovery(
            approved_decisions,
            recovered_for_validation,
            registry_entries,
            traceability,
            existing_bar_count,
            existing_bar_count + len(normalized_bars or existing_recovery_bars),
        )

        output_dir = self._paths["output_dir"]
        RecoveryExporter.export_all(output_dir, result)
        result["export_validation"] = validator.validate_exports(output_dir, EXPORT_FILES)
        scope_validation = RecoveryExportValidator().validate_scope(result)

        validation_checks = (
            (result["candidate_validation"].get("checks") or [])
            + (result["recovery_validation"].get("checks") or [])
            + (result["export_validation"].get("checks") or [])
            + (scope_validation.get("checks") or [])
        )
        failed = [item for item in validation_checks if item.get("status") == "FAIL"]
        result["validation_report"] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "status": "PASS" if not failed else "FAIL",
            "checks": validation_checks,
            "summary": {
                "total_checks": len(validation_checks),
                "passed": len(validation_checks) - len(failed),
                "failed": len(failed),
            },
        }
        RecoveryExporter.print_summary(result)
        return result

    @staticmethod
    def _recovered_objects_from_bars(
        bars: List[dict[str, Any]],
        decisions: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        decision_by_id = {str(item.get("discovery_id")): item for item in decisions}
        objects: List[dict[str, Any]] = []
        for bar in bars:
            trace = bar.get("traceability") or {}
            discovery_id = str(trace.get("discovery_id") or "")
            decision = decision_by_id.get(discovery_id, {})
            objects.append(
                {
                    "recovered_object_id": trace.get("engineering_object_id") or bar.get("specification_id"),
                    "recovery_id": trace.get("recovery_id") or f"RECOVERY::{bar.get('bar_id')}",
                    "source_discovery_id": discovery_id,
                    "beam": bar.get("beam_id"),
                    "role": bar.get("role"),
                    "diameter_mm": bar.get("diameter_mm"),
                    "quantity": bar.get("quantity"),
                    "specification_id": bar.get("specification_id"),
                    "recovery_source": trace.get("recovery_source") or "QA.COVERAGE.5",
                    "recovery_confidence": trace.get("recovery_confidence") or decision.get("confidence_score"),
                    "recovery_version": "5.26.0",
                    "original_suppression_reason": trace.get("original_suppression_reason") or decision.get("primary_rejection_code"),
                    "recovery_justification": trace.get("recovery_reason") or decision.get("recovery_reason"),
                    "legitimacy_class": trace.get("qa_coverage_5_legitimacy") or decision.get("legitimacy_class"),
                    "context_id": bar.get("context_id"),
                    "coordinates": trace.get("coordinates"),
                    "engineering_region": trace.get("engineering_region"),
                    "support": trace.get("support"),
                    "station": trace.get("beam_station"),
                }
            )
        return objects
