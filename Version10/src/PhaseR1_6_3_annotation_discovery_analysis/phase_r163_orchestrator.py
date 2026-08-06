"""
Phase R.1.6.3 orchestrator — Annotation Discovery Analysis & Engineering Review.
MODEL_VERSION: 8.8.3
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional

from annotation_discovery_analyzer import AnnotationDiscoveryAnalyzer
from annotation_statistics_engine import AnnotationStatisticsEngine, PatternAnalysisEngine
from beam_analysis_model import MODEL_VERSION, PHASE_ID
from beam_comparison_engine import BeamComparisonEngine
from engineering_review_builder import EngineeringReviewBuilder
from input_loader import InputLoader
from review_question_generator import ReviewQuestionGenerator
from summary_report_builder import SummaryReportBuilder
from validation_engine import ValidationEngine


class PhaseR163Orchestrator:
    def __init__(self, v8_root: Optional[Path] = None):
        self.v8 = Path(v8_root) if v8_root else Path(__file__).resolve().parents[2]
        self.out = self.v8 / "data" / "output" / "PhaseR1_6_3_annotation_discovery_analysis"
        self.package_dir = Path(__file__).resolve().parent

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print("Phase R.1.6.3 — Annotation Discovery Analysis & Engineering Review")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print("EVIDENCE ONLY — no correction / no LLM / no production modification")
        print("=" * 72)
        t0 = time.perf_counter()

        print("\n[1/8] Loading artefacts (registry, annotations, RULE-012, leaders) ...")
        data = InputLoader(self.v8).load()
        print(
            f"      Beams={len(data['beam_ids'])} "
            f"detected={len(data['detected_ids'])} missing={len(data['missing_ids'])}"
        )
        if not data["beam_ids"]:
            raise RuntimeError("Beam Registry empty — run V.ROOT.1 first.")
        if not data["detected_ids"] and not data["missing_ids"]:
            raise RuntimeError("RULE-012 outputs missing — run Phase R.1.6.2 first.")

        print("\n[2/8] Beam-by-beam annotation discovery analysis ...")
        records = AnnotationDiscoveryAnalyzer().analyze_all(data)
        print(f"      Records={len(records)}")

        print("\n[3/8] Comparison + statistics + pattern observations ...")
        comparison = BeamComparisonEngine().compare(records, data["detected_ids"], data["missing_ids"])
        statistics = AnnotationStatisticsEngine().build(
            records, data["detected_ids"], data["missing_ids"], data.get("dashboard012") or {}
        )
        pattern = PatternAnalysisEngine().analyze(
            comparison, records, data["detected_ids"], data["missing_ids"]
        )
        print(f"      Coverage={statistics.get('coverage_pct')}% conclusion={pattern.get('pattern_conclusion')}")

        print("\n[4/8] Engineering review dataset + questions ...")
        review_dataset = EngineeringReviewBuilder().build(records)
        questions = ReviewQuestionGenerator().generate(statistics, pattern)
        print(f"      Review rows={review_dataset.get('row_count')} questions={questions.get('question_count')}")

        print("\n[5/8] Validation + regression ...")
        ve = ValidationEngine()
        validation = ve.validate(records, data, self.package_dir)
        regression = ve.regression(self.package_dir, statistics)
        print(f"      Validation {validation['passed']}/{validation['total']} regression={regression.get('passed')}")

        recommendation = "A" if validation.get("overall_passed") and regression.get("passed") else "B"
        elapsed = round(time.perf_counter() - t0, 2)

        payload: Dict[str, Any] = {
            "model_version": MODEL_VERSION,
            "phase": PHASE_ID,
            "records": records,
            "detected_ids": data["detected_ids"],
            "missing_ids": data["missing_ids"],
            "comparison": comparison,
            "statistics": statistics,
            "pattern": pattern,
            "review_dataset": review_dataset,
            "questions": questions,
            "validation": validation,
            "regression": regression,
            "recommendation": recommendation,
            "elapsed_s": elapsed,
            "sources": data["sources"],
        }

        print("\n[6/8] Exporting review package ...")
        paths = SummaryReportBuilder(self.out).export_all(payload)
        print(f"      Exported={len(paths)} -> {self.out}")

        print("\n[7/8] Complete.")
        status = "PASS" if validation.get("overall_passed") else "FAIL"
        result = {
            "model_version": MODEL_VERSION,
            "phase": PHASE_ID,
            "status": status,
            "recommendation": recommendation,
            "statistics": statistics,
            "pattern_conclusion": pattern.get("pattern_conclusion"),
            "validation": validation,
            "regression": regression,
            "export_paths": paths,
            "elapsed_s": elapsed,
        }
        self._print_summary(result)
        return result

    @staticmethod
    def _print_summary(result: Dict[str, Any]) -> None:
        s = result.get("statistics") or {}
        print("\n" + "-" * 72)
        print(f"  PHASE {result.get('phase')} SUMMARY")
        print(f"  Status           : {result.get('status')}")
        print(f"  Beams            : {s.get('total_beams')}")
        print(f"  Detected/Missing : {s.get('detected_beams')}/{s.get('missing_beams')}")
        print(f"  Coverage %       : {s.get('coverage_pct')}")
        print(f"  Pattern          : {result.get('pattern_conclusion')}")
        print(f"  Recommendation   : {result.get('recommendation')}")
        print("-" * 72)
