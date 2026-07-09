"""Recovery Statistics Consistency orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.recovery_statistics_validation.artifact_cross_checker import ArtifactCrossChecker
from src.recovery_statistics_validation.export import EXPORT_FILES, ConsistencyExporter
from src.recovery_statistics_validation.health_analyzer import HealthAnalyzer
from src.recovery_statistics_validation.lineage_validator import LineageValidator
from src.recovery_statistics_validation.metric_verifier import MetricVerifier
from src.recovery_statistics_validation.production_snapshot import ProductionSnapshot
from src.recovery_statistics_validation.reconciliation_engine import ReconciliationEngine
from src.recovery_statistics_validation.reporting import ConsistencyReporting
from src.recovery_statistics_validation.root_cause_analyzer import RootCauseAnalyzer
from src.recovery_statistics_validation.statistics_collector import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
    StatisticsCollector,
    default_paths,
)
from src.recovery_statistics_validation.validation import ConsistencyValidator


class ConsistencyEngine:
    """Run read-only recovery statistics consistency validation."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        snapshot = StatisticsCollector(self._project_root).collect()
        authoritative = ProductionSnapshot.build(snapshot)

        reconciliation = ReconciliationEngine().reconcile(snapshot, authoritative)
        cross_artifact = ArtifactCrossChecker().check(snapshot, authoritative)
        lineage = LineageValidator().validate(snapshot, authoritative)
        metric_checks = MetricVerifier().verify(snapshot, authoritative)
        root_causes = RootCauseAnalyzer().analyze(reconciliation, snapshot, authoritative)
        health = HealthAnalyzer().analyze(reconciliation, cross_artifact, lineage, metric_checks)

        result: dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "read_only_analysis": True,
            "load_status": snapshot.get("load_status"),
            "production_snapshot": authoritative,
            "statistics_reconciliation": reconciliation,
            "cross_artifact_validation": cross_artifact,
            "lineage_consistency": lineage,
            "metric_verification_checks": metric_checks,
            "root_cause_analysis": root_causes,
            "consistency_health": health,
        }

        reporting = ConsistencyReporting()
        result["statistics_summary"] = reporting.build_summary(
            authoritative,
            reconciliation,
            health,
            {"status": "PENDING"},
            root_causes,
        )
        result["statistics_report"] = reporting.build_report(result)
        result["statistics_validation"] = ConsistencyValidator().validate(result)
        result["statistics_summary"]["validation_status"] = result["statistics_validation"].get("status")

        output_dir = self._paths["output_dir"]
        ConsistencyExporter.export_all(output_dir, result)
        result["export_validation"] = ConsistencyValidator().validate_exports(output_dir, EXPORT_FILES)
        ConsistencyExporter.print_summary(result)
        return result
