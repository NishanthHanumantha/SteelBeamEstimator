"""Reinforcement Discovery Coverage Engine orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.reinforcement_discovery_analysis.association_analysis import AssociationAnalyzer
from src.reinforcement_discovery_analysis.callout_classifier import CalloutClassifier
from src.reinforcement_discovery_analysis.discovery_collector import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
    DiscoveryCollector,
    default_paths,
)
from src.reinforcement_discovery_analysis.discovery_funnel import DiscoveryFunnelAnalyzer
from src.reinforcement_discovery_analysis.discovery_gap_analysis import DiscoveryGapAnalyzer
from src.reinforcement_discovery_analysis.export import DiscoveryExporter, DiscoveryValidator
from src.reinforcement_discovery_analysis.normalization_analysis import NormalizationAnalyzer
from src.reinforcement_discovery_analysis.reinforcement_inventory import ReinforcementInventoryBuilder
from src.reinforcement_discovery_analysis.statistics import DiscoveryStatistics
from src.reinforcement_discovery_analysis.traceability_report import TraceabilityReportBuilder


class DiscoveryEngine:
    """Run read-only reinforcement discovery coverage analysis."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        collector = DiscoveryCollector(self._project_root)
        snapshot = collector.collect()

        inventory_builder = ReinforcementInventoryBuilder()
        inventory = inventory_builder.build(snapshot)

        classifier = CalloutClassifier()
        classification_analysis = classifier.analyze(inventory)

        association_analyzer = AssociationAnalyzer()
        association_analysis = association_analyzer.analyze(inventory)

        normalization_analyzer = NormalizationAnalyzer()
        normalization_analysis = normalization_analyzer.analyze(inventory)

        funnel_analyzer = DiscoveryFunnelAnalyzer()
        discovery_funnel = funnel_analyzer.analyze(inventory)

        trace_builder = TraceabilityReportBuilder()
        traceability_matrix = trace_builder.build(inventory)

        gap_analyzer = DiscoveryGapAnalyzer()
        discovery_gap_analysis = gap_analyzer.analyze(
            inventory,
            classification_analysis,
            association_analysis,
            normalization_analysis,
            discovery_funnel,
        )
        unsupported_patterns = gap_analyzer.build_unsupported_patterns(inventory)

        statistics = DiscoveryStatistics()
        parser_health_metrics = statistics.build_parser_health(
            inventory,
            discovery_funnel,
            classification_analysis,
            association_analysis,
            normalization_analysis,
        )
        discovery_summary = statistics.build_summary(
            inventory,
            discovery_funnel,
            parser_health_metrics,
            discovery_gap_analysis,
            unsupported_patterns,
        )

        result: dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "generated_workbook": snapshot.get("generated_workbook"),
            "estimator_workbook": snapshot.get("estimator_workbook"),
            "engineering_code_modified": False,
            "engineering_pipeline_frozen": True,
            "parser_executed": False,
            "dxf_accessed": False,
            "read_only_analysis": True,
            "load_status": snapshot.get("load_status"),
            "inventory": inventory,
            "discovery_funnel": discovery_funnel,
            "traceability_matrix": traceability_matrix,
            "classification_analysis": classification_analysis,
            "association_analysis": association_analysis,
            "normalization_analysis": normalization_analysis,
            "parser_health_metrics": parser_health_metrics,
            "unsupported_patterns": unsupported_patterns,
            "discovery_gap_analysis": discovery_gap_analysis,
            "discovery_summary": discovery_summary,
        }

        output_dir = self._paths["output_dir"]
        DiscoveryExporter.export_all(output_dir, result)
        validation = DiscoveryValidator().validate(result)
        export_validation = DiscoveryValidator().validate_exports(output_dir, result)
        result["validation_report"] = validation
        result["export_validation"] = export_validation
        DiscoveryExporter.print_summary(result)
        return result
