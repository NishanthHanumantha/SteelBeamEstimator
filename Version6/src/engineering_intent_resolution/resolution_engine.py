"""Phase K.1.1 Engineering Intent Resolution orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.engineering_intent_resolution.export import EXPORT_FILES, ResolutionExporter
from src.engineering_intent_resolution.intent_priority_engine import IntentPriorityEngine
from src.engineering_intent_resolution.intent_resolution_engine import IntentResolutionEngine
from src.engineering_intent_resolution.production_integrator import ProductionIntegrator
from src.engineering_intent_resolution.reporting import ResolutionReporting
from src.engineering_intent_resolution.resolution_collector import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
    ResolutionCollector,
    default_paths,
)
from src.engineering_intent_resolution.statistics import ResolutionStatistics
from src.engineering_intent_resolution.validation import ResolutionValidation


class ResolutionEngine:
    """Run deterministic engineering intent resolution."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        snapshot = ResolutionCollector(self._project_root).collect()
        priority_engine = IntentPriorityEngine(self._paths["priority_config"])
        resolution = IntentResolutionEngine(priority_engine).resolve(snapshot)

        decisions = list(resolution.get("decisions") or [])
        graphs = list(resolution.get("graphs") or [])
        conflicts = list(resolution.get("conflicts") or [])
        merges = list(resolution.get("merges") or [])
        overlaps = list(resolution.get("overlaps") or [])
        traces = list(resolution.get("traces") or [])
        registry_entries = list(resolution.get("registry_entries") or [])

        production_integration = ProductionIntegrator(self._project_root).integrate(
            snapshot,
            decisions,
        )

        statistics = ResolutionStatistics.build(
            snapshot.get("intent_objects") or [],
            decisions,
            merges,
            conflicts,
            graphs,
        )
        health = ResolutionStatistics.build_health(statistics)
        recommendations = ResolutionReporting.build_recommendations(decisions, conflicts)

        result: dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "load_status": snapshot.get("load_status"),
            "decision_contexts": resolution.get("decision_contexts") or [],
            "graphs": graphs,
            "overlaps": overlaps,
            "conflicts": conflicts,
            "merges": merges,
            "decisions": decisions,
            "decision_registry": {
                "registry_count": len(registry_entries),
                "entries": registry_entries,
            },
            "traceability": traces,
            "decision_validations": resolution.get("decision_validations") or [],
            "statistics": statistics,
            "health": health,
            "production_integration": production_integration,
            "resolution_rules": priority_engine.rules_export(),
            "recommendations": recommendations,
            "idempotent": bool(resolution.get("idempotent")),
        }

        output_dir = self._paths["output_dir"]
        export_validation = ResolutionExporter.validate_exports(
            output_dir,
            tuple(name for name in EXPORT_FILES if name != "engineering_decision_validation.json"),
        )
        validation = ResolutionValidation().validate(result, snapshot, export_validation)
        result["validation"] = validation
        result["summary"] = ResolutionStatistics.build_summary(
            statistics,
            health,
            validation.get("status", "FAIL"),
        )
        ResolutionExporter.export_all(output_dir, result)
        export_validation = ResolutionExporter.validate_exports(output_dir, EXPORT_FILES)
        result["export_validation"] = export_validation
        validation = ResolutionValidation().validate(result, snapshot, export_validation)
        result["validation"] = validation
        result["summary"] = ResolutionStatistics.build_summary(
            statistics,
            health,
            validation.get("status", "FAIL"),
        )
        ResolutionExporter._write_validation_bundle(output_dir, result)
        ResolutionExporter.print_summary(result)
        return result
