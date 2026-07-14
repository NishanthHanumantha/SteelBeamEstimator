"""
Phase QA.1.1 — Module 17: Orchestrator
Pipeline: Load → Locate → Diagnose → Classify → Assess → Recommend → Rank → Statistics
         → Validate → Report → Export
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

import datetime
import pathlib
import sys
from typing import Any, Dict, List, Optional

MODEL_VERSION = "6.5.2"

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from diagnostic_models import (
    DiagnosticsSummary, EngineeringDiagnostic, ImpactLevel, PriorityFix
)
from diagnostics_loader      import DiagnosticsLoader
from pipeline_trace_loader   import PipelineTraceLoader
from pipeline_stage_locator  import PipelineStageLocator

from beam_error_diagnostics          import BeamErrorDiagnostics
from reinforcement_error_diagnostics import ReinforcementErrorDiagnostics
from geometry_error_diagnostics      import GeometryErrorDiagnostics
from feature_error_diagnostics       import FeatureErrorDiagnostics
from pattern_error_diagnostics       import PatternErrorDiagnostics
from bbs_error_diagnostics           import BBSErrorDiagnostics
from steel_error_diagnostics         import SteelErrorDiagnostics

from root_cause_classifier            import RootCauseClassifier
from impact_assessor                  import ImpactAssessor
from engineering_recommendation_engine import EngineeringRecommendationEngine
from priority_ranking                 import PriorityRanker
from diagnostics_statistics           import DiagnosticsStatistics
from diagnostics_reporter             import DiagnosticsReporter
from diagnostics_export               import DiagnosticsExport


class EngineeringDiagnosticsError(Exception):
    """Raised when a validation rule is violated."""


class PhaseQA11Orchestrator:
    """
    Phase QA.1.1 — Engineering Error Diagnostics & Root Cause Analysis Engine.
    Read-only. Deterministic. No LLM. No corrections.
    """

    def __init__(self) -> None:
        self._loader      = DiagnosticsLoader()
        self._locator     = PipelineStageLocator()
        self._classifier  = RootCauseClassifier()
        self._assessor    = ImpactAssessor()
        self._recommender = EngineeringRecommendationEngine()
        self._ranker      = PriorityRanker()
        self._statistics  = DiagnosticsStatistics()
        self._reporter    = DiagnosticsReporter()
        self._exporter    = DiagnosticsExport()

    # ── Public entry point ────────────────────────────────────────────────────
    def run(self) -> Dict[str, Any]:
        timestamp = datetime.datetime.now().isoformat()

        # STEP 1: Load all inputs
        print("[QA.1.1] Loading inputs…")
        inputs = self._loader.load_all()
        qa1_errors   = inputs["qa1_errors"]
        qa1_summary  = inputs["qa1_summary"]
        qa1_score    = inputs["qa1_score"]
        qa1_confusion = inputs["qa1_confusion"] or {}
        qa1_beam     = inputs["qa1_beam"] or {}
        qa1_rein     = inputs["qa1_rein"] or {}
        qa1_bbs      = inputs["qa1_bbs"] or {}
        qa1_pattern  = inputs["qa1_pattern"] or {}
        qa1_full     = self._loader.load_qa1_full_report() or {}

        l2_by_beam   = inputs["l2_by_beam"]
        l21_by_beam  = inputs["l21_by_beam"]
        l3_by_beam   = inputs["l3_by_beam"]
        ground_truth = inputs["ground_truth"]
        v5_bbs_by_beam = inputs["v5_bbs_by_beam"]

        benchmark_id = qa1_summary.get("benchmark_id", "UNKNOWN")
        drawing_name = qa1_summary.get("drawing_name", "UNKNOWN")

        # STEP 2: Generate diagnostics from all 7 error modules
        print("[QA.1.1] Generating diagnostics…")
        all_diagnostics: List[EngineeringDiagnostic] = []

        all_diagnostics += BeamErrorDiagnostics().diagnose(
            qa1_beam, l2_by_beam, ground_truth, drawing_name
        )
        all_diagnostics += ReinforcementErrorDiagnostics().diagnose(
            qa1_rein, l2_by_beam, ground_truth, drawing_name
        )
        all_diagnostics += GeometryErrorDiagnostics().diagnose(
            qa1_full, l2_by_beam, ground_truth, drawing_name
        )
        all_diagnostics += FeatureErrorDiagnostics().diagnose(
            qa1_summary, l21_by_beam, l2_by_beam, ground_truth, drawing_name
        )
        all_diagnostics += PatternErrorDiagnostics().diagnose(
            qa1_summary, qa1_pattern, l3_by_beam, ground_truth, drawing_name
        )
        all_diagnostics += BBSErrorDiagnostics().diagnose(
            qa1_errors, qa1_bbs, v5_bbs_by_beam, l2_by_beam, drawing_name
        )
        all_diagnostics += SteelErrorDiagnostics().diagnose(
            qa1_summary, qa1_full, drawing_name
        )

        print(f"[QA.1.1] Total diagnostics generated: {len(all_diagnostics)}")

        # STEP 3: Locate pipeline stages
        print("[QA.1.1] Locating pipeline stages…")
        self._locator.locate_all(all_diagnostics, l2_by_beam, l21_by_beam, l3_by_beam)

        # STEP 4: Classify root causes
        print("[QA.1.1] Classifying root causes…")
        self._classifier.classify_all(all_diagnostics)

        # STEP 5: Assess impact
        print("[QA.1.1] Assessing impact…")
        self._assessor.assess_all(all_diagnostics)

        # STEP 6: Generate recommendations
        print("[QA.1.1] Generating recommendations…")
        self._recommender.assign_all(all_diagnostics)

        # STEP 7: Priority ranking
        print("[QA.1.1] Ranking priorities…")
        priority_fixes = self._ranker.rank(all_diagnostics)

        # STEP 8: Statistics
        print("[QA.1.1] Computing statistics…")
        stats = self._statistics.compute_all(all_diagnostics)

        # STEP 9: Validation rules
        print("[QA.1.1] Validating rules…")
        rule_results = self._validate(qa1_errors, all_diagnostics)

        # STEP 10: Build summary
        summary = DiagnosticsSummary(
            benchmark_id=benchmark_id,
            drawing_name=drawing_name,
            model_version=MODEL_VERSION,
            timestamp=timestamp,
            total_diagnostics=len(all_diagnostics),
            total_qa1_errors_diagnosed=len(qa1_errors.get("highest_impact_errors", [])),
            total_kpi_gap_diagnostics=len(all_diagnostics) - len(
                qa1_errors.get("highest_impact_errors", [])),
            root_cause_distribution=stats["root_cause_distribution"],
            pipeline_stage_distribution=stats["pipeline_stage_distribution"],
            severity_distribution=stats["severity_distribution"],
            impact_distribution=stats["impact_distribution"],
            priority_fixes=priority_fixes,
            validation_passed=all(rule_results.values()),
            rule_results=rule_results,
            overall_diagnostic_confidence=self._statistics.average_confidence(all_diagnostics),
            recommendations_count=len(set(d.recommended_fix for d in all_diagnostics)),
        )

        # STEP 11: Build report
        print("[QA.1.1] Building report…")
        full_report = self._reporter.build_report(
            all_diagnostics, priority_fixes, summary, qa1_summary
        )

        # STEP 12: Export
        print("[QA.1.1] Exporting artefacts…")
        exported_paths = self._exporter.export_all(
            all_diagnostics, priority_fixes, full_report, stats,
            benchmark_id, MODEL_VERSION, timestamp
        )

        result = {
            "model_version": MODEL_VERSION,
            "benchmark_id": benchmark_id,
            "drawing_name": drawing_name,
            "timestamp": timestamp,
            "total_diagnostics": len(all_diagnostics),
            "validation_passed": summary.validation_passed,
            "rule_results": rule_results,
            "root_cause_distribution": stats["root_cause_distribution"],
            "pipeline_stage_distribution": stats["pipeline_stage_distribution"],
            "severity_distribution": stats["severity_distribution"],
            "impact_distribution": stats["impact_distribution"],
            "priority_fixes": [
                {
                    "rank": f.rank,
                    "fix_title": f.fix_title,
                    "priority_score": f.priority_score,
                    "expected_improvement_pct": f.expected_improvement_pct,
                }
                for f in priority_fixes[:5]
            ],
            "exported_paths": exported_paths,
        }
        print("[QA.1.1] Phase QA.1.1 complete.")
        return result

    # ── Validation rules ──────────────────────────────────────────────────────
    def _validate(
        self,
        qa1_errors: Dict[str, Any],
        diagnostics: List[EngineeringDiagnostic],
    ) -> Dict[str, bool]:
        rules: Dict[str, bool] = {}

        # RULE_1: Every QA.1 error has a diagnostic
        qa1_bbs_count = len(qa1_errors.get("highest_impact_errors", []))
        bbs_diag_count = sum(
            1 for d in diagnostics if d.error_type == "BBS_ROW_ERROR"
        )
        rule1_pass = bbs_diag_count >= qa1_bbs_count
        rules["RULE_1_every_qa1_error_has_diagnostic"] = rule1_pass
        if not rule1_pass:
            raise EngineeringDiagnosticsError(
                f"RULE_1 FAILED: {qa1_bbs_count} QA.1 errors but only "
                f"{bbs_diag_count} BBS diagnostics generated."
            )

        # RULE_2: Every diagnostic has exactly one root cause
        missing_rc = [d.diagnostic_id for d in diagnostics if not d.root_cause]
        rule2_pass = len(missing_rc) == 0
        rules["RULE_2_every_diagnostic_has_root_cause"] = rule2_pass
        if not rule2_pass:
            raise EngineeringDiagnosticsError(
                f"RULE_2 FAILED: {len(missing_rc)} diagnostics without root cause."
            )

        # RULE_3: Every diagnostic has exactly one pipeline stage
        missing_stage = [d.diagnostic_id for d in diagnostics if not d.pipeline_stage]
        rule3_pass = len(missing_stage) == 0
        rules["RULE_3_every_diagnostic_has_pipeline_stage"] = rule3_pass
        if not rule3_pass:
            raise EngineeringDiagnosticsError(
                f"RULE_3 FAILED: {len(missing_stage)} diagnostics without pipeline stage."
            )

        # RULE_4: Every diagnostic has one recommendation
        missing_rec = [d.diagnostic_id for d in diagnostics if not d.recommended_fix]
        rule4_pass = len(missing_rec) == 0
        rules["RULE_4_every_diagnostic_has_recommendation"] = rule4_pass
        if not rule4_pass:
            raise EngineeringDiagnosticsError(
                f"RULE_4 FAILED: {len(missing_rec)} diagnostics without recommendations."
            )

        # RULE_5: Every diagnostic has a priority rank
        missing_rank = [d.diagnostic_id for d in diagnostics if d.priority_rank == 0]
        rule5_pass = len(missing_rank) == 0
        rules["RULE_5_every_recommendation_has_priority"] = rule5_pass
        if not rule5_pass:
            raise EngineeringDiagnosticsError(
                f"RULE_5 FAILED: {len(missing_rank)} diagnostics without priority rank."
            )

        return rules
