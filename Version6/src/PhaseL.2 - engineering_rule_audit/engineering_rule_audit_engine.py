"""Phase L.2 Engineering Rule Audit Engine — orchestrator."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from audit_loader import PHASE, MODEL_VERSION, ENGINE_VERSION, default_paths
from audit_collector import AuditCollector
from context_pipeline_auditor import ContextPipelineAuditor
from coverage_statistics import CoverageStatistics
from dependency_mapper import DependencyMapper
from estimator_trace_comparator import EstimatorTraceComparator
from execution_path_analyzer import ExecutionPathAnalyzer
from export import EXPORT_FILES, AuditExport
from export_pipeline_auditor import ExportPipelineAuditor
from geometry_pipeline_auditor import GeometryPipelineAuditor
from implementation_status_classifier import ImplementationStatusClassifier
from ownership_pipeline_auditor import OwnershipPipelineAuditor
from pipeline_break_detector import PipelineBreakDetector
from pipeline_tracer import PipelineTracer
from quantity_pipeline_auditor import QuantityPipelineAuditor
from reinforcement_role_auditor import ReinforcementRoleAuditor
from reporting import AuditReporting
from rule_registry_auditor import RuleRegistryAuditor
from validation import AuditValidation


class EngineeringRuleAuditEngine:
    """Run deterministic Phase L.2 Engineering Rule Audit."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._root = project_root or Path.cwd()
        self._paths = default_paths(self._root)

    def run(self) -> Dict[str, Any]:
        started = time.perf_counter()

        # 1. Collect inputs
        snapshot = AuditCollector(self._root).collect()
        config = snapshot.get("config") or {}
        src_root = Path(snapshot.get("src_root") or str(self._root / "src"))

        # 2. Engineering rule inventory (static source scan)
        registry_auditor = RuleRegistryAuditor(src_root)
        rule_inventory = registry_auditor.audit()

        # 3. Pipeline trace (per-role, per-stage)
        pipeline_trace = PipelineTracer().trace(snapshot)

        # 4. Sub-stage auditors
        geometry_audit = GeometryPipelineAuditor().audit(snapshot)
        ownership_audit = OwnershipPipelineAuditor().audit(snapshot)
        context_audit = ContextPipelineAuditor().audit(snapshot)
        quantity_audit = QuantityPipelineAuditor().audit(snapshot)
        export_audit = ExportPipelineAuditor().audit(snapshot)

        # 5. Break detection
        breaks = PipelineBreakDetector().detect(pipeline_trace)

        # 6. Implementation status classification
        status_classifications = ImplementationStatusClassifier().classify(
            pipeline_trace, breaks, rule_inventory
        )

        # 7. Execution path analysis
        execution_paths = ExecutionPathAnalyzer().analyze(
            status_classifications, rule_inventory
        )

        # 8. Role-level audit table
        role_audit = ReinforcementRoleAuditor().audit(
            pipeline_trace, breaks, status_classifications
        )

        # 9. Dependency mapping
        dependency_graph = DependencyMapper().build(status_classifications)

        # 10. Estimator trace comparison
        estimator_trace = EstimatorTraceComparator().compare(
            role_audit, status_classifications, snapshot
        )

        # 11. Coverage statistics
        coverage = CoverageStatistics().build(
            status_classifications, execution_paths, role_audit,
            rule_inventory, pipeline_trace, estimator_trace,
        )

        # 12. Implementation matrix + reports
        implementation_matrix = AuditReporting.build_implementation_matrix(
            role_audit, status_classifications, breaks
        )
        beam_audit = AuditReporting.build_beam_audit(pipeline_trace)

        duration_s = time.perf_counter() - started

        result: Dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "duration_s": round(duration_s, 3),
            "config": config,
            "data_source": snapshot.get("data_source", "V5_REFERENCE"),
            "load_status": snapshot.get("load_status"),
            "rule_inventory": rule_inventory,
            "pipeline_trace": pipeline_trace,
            "geometry_audit": geometry_audit,
            "ownership_audit": ownership_audit,
            "context_audit": context_audit,
            "quantity_audit": quantity_audit,
            "export_audit": export_audit,
            "execution_breaks": breaks,
            "implementation_status_classifications": status_classifications,
            "execution_paths": execution_paths,
            "role_audit": role_audit,
            "dependency_graph": dependency_graph,
            "estimator_trace": estimator_trace,
            "coverage_statistics": coverage,
            "implementation_matrix": implementation_matrix,
            "beam_audit": beam_audit,
            "validation": {"status": "PENDING"},
            "summary": AuditReporting.build_summary(coverage, status_classifications, breaks, "PENDING"),
            "report": None,
        }
        result["report"] = AuditReporting.build_report(result)

        # 13. First export pass
        output_dir = self._paths["output_dir"]
        AuditExport.export_all(output_dir, result, config)
        export_validation = AuditExport.validate_exports(output_dir)
        result["export_validation"] = export_validation

        # 14. Validation
        validation = AuditValidation().validate(result)
        result["validation"] = validation
        result["summary"] = AuditReporting.build_summary(
            coverage, status_classifications, breaks, validation.get("status", "FAIL")
        )
        result["report"] = AuditReporting.build_report(result)

        # 15. Final export
        AuditExport.export_all(output_dir, result, config)
        AuditExport.print_summary(result)
        return result
