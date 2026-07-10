"""Phase K.2 Engineering Decision Execution orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decision_collector import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
    DecisionCollector,
    default_paths,
)
from execution_config import load_execution_config
from execution_pipeline import ExecutionPipeline
from execution_reporting import ExecutionReporting
from execution_statistics import ExecutionStatistics
from execution_validator import ExecutionValidator
from export import EXPORT_FILES, ExecutionExporter
from validation import ExecutionValidation


class ExecutionEngine:
    """Run deterministic Engineering Decision Execution."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        snapshot = DecisionCollector(self._project_root).collect()
        config = load_execution_config(self._paths["config"])
        pipeline_result = ExecutionPipeline(self._project_root).run(snapshot, config)

        registry = pipeline_result.get("registry") or {}
        registry_entries = list(registry.get("entries") or [])
        decisions = list(snapshot.get("decisions") or [])
        selection = list(pipeline_result.get("selection") or [])
        mapping = pipeline_result.get("mapping") or {}
        adapter_result = pipeline_result.get("adapter_result") or {}
        bridge_result = pipeline_result.get("bridge_result") or {}

        execution_validations = ExecutionValidator().validate_all(registry_entries)
        traceability = ExecutionReporting.build_traceability(registry_entries, decisions)

        statistics = ExecutionStatistics.build(
            decisions,
            selection,
            registry,
            mapping,
            adapter_result,
            bridge_result,
        )
        health = ExecutionStatistics.build_health(statistics, bridge_result)

        result: dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "load_status": snapshot.get("load_status"),
            "config": {
                "enable": config.get("enable"),
                "invoke_calculation_engine": config.get("invoke_calculation_engine"),
            },
            "execution_contexts": pipeline_result.get("execution_contexts") or [],
            "selection": selection,
            "mapping": mapping,
            "execution_registry": {
                "registry_count": registry.get("registry_count", 0),
                "entries": registry_entries,
            },
            "execution_lifecycle": registry.get("lifecycles") or [],
            "pipeline_steps": pipeline_result.get("pipeline_steps") or [],
            "adapter_result": adapter_result,
            "production_bridge": bridge_result,
            "execution_validations": execution_validations,
            "traceability": traceability,
            "statistics": statistics,
            "health": health,
            "idempotent": bool(pipeline_result.get("idempotent")),
            "validation_gate": snapshot.get("validation_gate") or {},
        }

        output_dir = self._paths["output_dir"]
        export_validation = ExecutionExporter.validate_exports(
            output_dir,
            tuple(name for name in EXPORT_FILES if name != "execution_validation.json"),
        )
        validation = ExecutionValidation().validate(result, snapshot, export_validation)
        result["validation"] = validation
        result["summary"] = ExecutionStatistics.build_summary(
            statistics,
            health,
            validation.get("status", "FAIL"),
        )
        ExecutionExporter.export_all(output_dir, result)
        export_validation = ExecutionExporter.validate_exports(output_dir, EXPORT_FILES)
        result["export_validation"] = export_validation
        validation = ExecutionValidation().validate(result, snapshot, export_validation)
        result["validation"] = validation
        result["summary"] = ExecutionStatistics.build_summary(
            statistics,
            health,
            validation.get("status", "FAIL"),
        )
        ExecutionExporter._write_validation_bundle(output_dir, result)
        ExecutionExporter.print_summary(result)
        return result
