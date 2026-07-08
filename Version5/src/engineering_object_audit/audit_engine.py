"""Engineering Object Creation Audit orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.engineering_object_audit.audit_collector import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
    AuditCollector,
    default_paths,
)
from src.engineering_object_audit.dependency_analysis import DependencyAnalyzer
from src.engineering_object_audit.duplicate_analysis import DuplicateAnalyzer
from src.engineering_object_audit.engineering_object_trace import EngineeringObjectTraceBuilder
from src.engineering_object_audit.export import AuditExporter, AuditValidator
from src.engineering_object_audit.readiness_analysis import ReadinessAnalyzer
from src.engineering_object_audit.recommendation_engine import RecommendationEngine
from src.engineering_object_audit.rejection_classifier import RejectionClassifier
from src.engineering_object_audit.rejection_statistics import RejectionStatistics


class EngineeringObjectAuditEngine:
    """Run read-only engineering object creation audit."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        snapshot = AuditCollector(self._project_root).collect()
        inventory = snapshot.get("inventory") or []
        indexes = snapshot.get("indexes") or {}

        dependency_analyzer = DependencyAnalyzer()
        dependency_analysis = dependency_analyzer.analyze_all(inventory, indexes)

        readiness_analyzer = ReadinessAnalyzer()
        readiness_analysis = readiness_analyzer.analyze_all(inventory, dependency_analysis)

        duplicate_analyzer = DuplicateAnalyzer()
        duplicate_analysis = duplicate_analyzer.analyze(inventory, indexes)

        classifier = RejectionClassifier()
        trace_builder = EngineeringObjectTraceBuilder()
        recommendation_engine = RecommendationEngine()

        audits: List[dict[str, Any]] = []
        decision_matrix: List[dict[str, Any]] = []
        root_cause_chains: List[dict[str, Any]] = []
        recommendations_by_id: Dict[str, dict[str, Any]] = {}

        dep_by_id = dependency_analysis.get("by_discovery_id") or {}
        readiness_by_id = readiness_analysis.get("by_discovery_id") or {}
        duplicate_by_id = duplicate_analysis.get("by_discovery_id") or {}

        for item in inventory:
            dependencies = dep_by_id.get(item.get("discovery_id"), {})
            readiness = readiness_by_id.get(item.get("discovery_id"), {})
            duplicate_info = duplicate_by_id.get(item.get("discovery_id"))
            decision = classifier.classify(item, indexes, dependencies, readiness, duplicate_info)
            trace = trace_builder.build_trace(item, dependencies, readiness, decision)
            chain = trace_builder.build_root_cause_chain(item, decision, dependencies)
            audits.append(
                {
                    **trace,
                    **decision,
                    "decision": decision,
                    "dependencies": dependencies,
                    "duplicate_info": duplicate_info,
                }
            )
            root_cause_chains.append(chain)

        rejection_statistics = RejectionStatistics().build(audits, len(inventory))
        recommendations = recommendation_engine.build(rejection_statistics, audits)
        recommendations_by_id = {
            item["root_cause"]: item for item in recommendations.get("recommendations") or []
        }

        for item in inventory:
            discovery_id = item.get("discovery_id")
            dependencies = dep_by_id.get(discovery_id, {})
            readiness = readiness_by_id.get(discovery_id, {})
            audit = next(record for record in audits if record.get("discovery_id") == discovery_id)
            decision = audit.get("decision") or {}
            recommendation = recommendations_by_id.get(decision.get("primary_rejection_code"))
            decision_matrix.append(
                trace_builder.build_decision_matrix_record(
                    item,
                    dependencies,
                    readiness,
                    decision,
                    recommendation,
                )
            )

        engineering_object_health = recommendation_engine.build_health(
            len(inventory),
            rejection_statistics,
            dependency_analysis,
            duplicate_analysis,
            readiness_analysis,
        )

        summary = {
            "total_annotations": len(inventory),
            "engineering_objects_created": rejection_statistics.get("accepted_count", 0),
            "rejected_count": rejection_statistics.get("rejected_count", 0),
            "acceptance_rate_percent": rejection_statistics.get("acceptance_rate_percent", 0.0),
            "top_rejection_codes": (rejection_statistics.get("primary_rejection_codes") or [])[:5],
            "top_dependency_failures": (dependency_analysis.get("top_dependency_failures") or [])[:5],
            "duplicate_summary": {
                "duplicate_group_count": duplicate_analysis.get("duplicate_group_count", 0),
                "valid_duplicate_groups": duplicate_analysis.get("valid_duplicate_groups", 0),
                "suspicious_duplicate_groups": duplicate_analysis.get("suspicious_duplicate_groups", 0),
            },
            "overall_object_creation_health": engineering_object_health.get("overall_object_creation_health", 0),
        }

        result: dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "engineering_code_modified": False,
            "engineering_pipeline_frozen": True,
            "parser_executed": False,
            "dxf_accessed": False,
            "read_only_analysis": True,
            "load_status": snapshot.get("load_status"),
            "inventory": inventory,
            "audits": audits,
            "decision_matrix": decision_matrix,
            "rejection_statistics": rejection_statistics,
            "dependency_analysis": dependency_analysis,
            "duplicate_analysis": duplicate_analysis,
            "readiness_analysis": readiness_analysis,
            "engineering_object_health": engineering_object_health,
            "recommendations": recommendations,
            "root_cause_chains": root_cause_chains,
            "summary": summary,
        }

        output_dir = self._paths["output_dir"]
        AuditExporter.export_all(output_dir, result)
        validation = AuditValidator().validate(result)
        export_validation = AuditValidator().validate_exports(output_dir, result)
        result["validation_report"] = validation
        result["export_validation"] = export_validation
        AuditExporter.print_summary(result)
        return result
