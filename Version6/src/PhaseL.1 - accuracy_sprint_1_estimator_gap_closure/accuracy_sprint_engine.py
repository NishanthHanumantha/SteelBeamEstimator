"""Phase L.1 Accuracy Sprint 1 — Estimator Gap Closure orchestrator."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from accuracy_loader import PHASE, MODEL_VERSION, ENGINE_VERSION, default_paths
from accuracy_collector import AccuracyCollector
from coverage_analyzer import CoverageAnalyzer
from decision_gap_analyzer import DecisionGapAnalyzer
from engineering_gap_classifier import EngineeringGapClassifier
from engineering_rule_gap_analyzer import EngineeringRuleGapAnalyzer
from estimator_comparator import EstimatorComparator
from export import EXPORT_FILES, AccuracyExport
from improvement_tracker import ImprovementTracker
from priority_ranker import PriorityRanker
from reinforcement_gap_analyzer import ReinforcementGapAnalyzer
from reporting import AccuracyReporting
from root_cause_engine import RootCauseEngine
from statistics import AccuracyStatistics
from validation import AccuracySprintValidation


class AccuracySprintEngine:
    """Run deterministic Phase L.1 Accuracy Sprint."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._root = project_root or Path.cwd()
        self._paths = default_paths(self._root)

    def run(self) -> Dict[str, Any]:
        started = time.perf_counter()

        # 1. Collect all inputs
        snapshot = AccuracyCollector(self._root).collect()
        config = snapshot.get("config") or {}

        # 2. Compare estimator vs model
        comparison = EstimatorComparator().compare(snapshot)

        # 3. Classify engineering gaps
        raw_gaps = EngineeringGapClassifier().classify(comparison, snapshot)

        # 4. Root cause analysis
        gaps_with_rc = RootCauseEngine().analyze(raw_gaps, snapshot)

        # 5. Coverage analysis
        coverage = CoverageAnalyzer().analyze(snapshot, comparison)

        # 6. Reinforcement role gap analysis
        role_gaps = ReinforcementGapAnalyzer().analyze(comparison, snapshot)

        # 7. Engineering rule gap analysis
        rule_gap_analysis = EngineeringRuleGapAnalyzer().analyze(gaps_with_rc, snapshot)

        # 8. Decision gap analysis
        decision_gaps = DecisionGapAnalyzer().analyze(snapshot, comparison)

        # 9. Priority ranking
        priority_backlog = PriorityRanker().rank(gaps_with_rc, {})

        # 10. Statistics
        statistics = AccuracyStatistics().build(comparison, coverage, priority_backlog, snapshot)

        # 11. Health
        health = AccuracyStatistics.build_health(statistics)

        # 12. Improvement tracker
        improvement_tracker = ImprovementTracker().build(priority_backlog, statistics, config)

        duration_s = time.perf_counter() - started

        result: Dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "duration_s": round(duration_s, 3),
            "config": config,
            "snapshot": {
                "load_status": snapshot.get("load_status"),
                "load_status_summary": snapshot.get("load_status_summary"),
                "artifact_presence": snapshot.get("artifact_presence"),
                "estimator_data": {
                    k: v for k, v in (snapshot.get("estimator_data") or {}).items()
                    if k != "rows"  # exclude large rows list from result payload
                },
                "decision_count": len(snapshot.get("decisions") or []),
                "intent_count": len(snapshot.get("intents") or []),
            },
            "comparison": comparison,
            "classified_gaps": priority_backlog,
            "coverage": coverage,
            "reinforcement_role_gaps": role_gaps,
            "rule_gap_analysis": rule_gap_analysis,
            "decision_gaps": decision_gaps,
            "priority_backlog": priority_backlog,
            "statistics": statistics,
            "health": health,
            "improvement_tracker": improvement_tracker,
            "idempotent": bool(snapshot.get("existing_validation_keys")
                               or (self._paths["output_dir"] / "engineering_gap_report.json").exists()),
            # Build provisional summary/report for first export pass
            "summary": AccuracyStatistics.build_summary(statistics, health, "PENDING"),
            "validation": {"status": "PENDING"},
            "dashboard": AccuracyReporting.build_dashboard(statistics, coverage, gaps_with_rc, comparison),
            "gap_matrix": AccuracyReporting.build_gap_matrix(priority_backlog),
            "report": None,
        }
        result["report"] = AccuracyReporting.build_report(result)

        # 13. Export first pass (for validation)
        output_dir = self._paths["output_dir"]
        AccuracyExport.export_all(output_dir, result, config)
        export_validation = AccuracyExport.validate_exports(output_dir)
        result["export_validation"] = export_validation

        # 14. Run validation
        validation = AccuracySprintValidation().validate(result)
        result["validation"] = validation
        result["summary"] = AccuracyStatistics.build_summary(
            statistics, health, validation.get("status", "FAIL")
        )
        result["report"] = AccuracyReporting.build_report(result)

        # 15. Final export with validation embedded
        AccuracyExport.export_all(output_dir, result, config)
        AccuracyExport.print_summary(result)
        return result
