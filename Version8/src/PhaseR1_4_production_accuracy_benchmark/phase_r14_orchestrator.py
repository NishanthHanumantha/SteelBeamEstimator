"""
Phase R.1.4 orchestrator — Production Accuracy Benchmark Engine.
MODEL_VERSION: 8.6.0
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional

from benchmark_kpi_engine import BenchmarkKPIEngine
from benchmark_report_generator import BenchmarkReportGenerator
from comparison_engine import ComparisonEngine
from error_classifier import ErrorClassifier
from official_model_builder import OfficialModelBuilder
from production_snapshot_loader import ProductionSnapshotLoader
from regression_engine import RegressionEngine
from root_cause_engine import RootCauseEngine

MODEL_VERSION = "8.6.0"
PHASE_ID = "R.1.4"

_DEFAULT_REFERENCE = (
    Path(__file__).resolve().parents[3]
    / "Test_Input"
    / "Third Set Drawings"
    / "Estimator_Output_3rdSet"
    / "EstimatorOutput_OnlyTF_Beam BBS.xlsx"
)


class PhaseR14Orchestrator:
    def __init__(
        self,
        v8_root: Optional[Path] = None,
        estimator_workbook: Optional[Path] = None,
    ):
        self.v8 = Path(v8_root) if v8_root else Path(__file__).resolve().parents[2]
        self.estimator_workbook = Path(estimator_workbook) if estimator_workbook else _DEFAULT_REFERENCE
        self.out = self.v8 / "data" / "output" / "PhaseR1_4_production_accuracy_benchmark"
        self.package_dir = Path(__file__).resolve().parent

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print("Phase R.1.4 — Production Accuracy Benchmark & Validation Engine")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print("=" * 72)
        t0 = time.perf_counter()

        print("\n[1/8] Interpreting official estimator workbook ...")
        print(f"      {self.estimator_workbook}")
        if not self.estimator_workbook.exists():
            raise FileNotFoundError(self.estimator_workbook)
        official = OfficialModelBuilder().build(self.estimator_workbook)
        print(
            f"      Summary kg={official.steel_summary.total_kg} "
            f"beams={len(official.beams)} rows={len(official.reinforcement_rows)}"
        )
        print(
            f"      Detected summary={official.interpretation.get('summary_detected')} "
            f"breakup={official.interpretation.get('breakup_detected')}"
        )

        print("\n[2/8] Loading production snapshot ...")
        production = ProductionSnapshotLoader(self.v8).load()
        print(
            f"      intents={len(production.intents)} details={len(production.details)} "
            f"bars={len(production.engineering_bars)} "
            f"steel_kg={production.steel_summary.get('total_kg')}"
        )

        print("\n[3/8] Benchmark comparison ...")
        comparison = ComparisonEngine().compare(official, production)

        print("\n[4/8] KPI engine ...")
        kpis = BenchmarkKPIEngine().compute(comparison)
        overall = (kpis.get("scorecard") or {}).get("overall_pct")
        print(f"      Overall production accuracy: {overall}%")

        print("\n[5/8] Error classification + root cause ...")
        diagnostics = ErrorClassifier().classify(comparison)
        root_cause = RootCauseEngine().analyze(diagnostics, comparison, kpis)
        print(f"      Diagnostics={diagnostics.get('diagnostic_count')} "
              f"primary_phase={root_cause.get('primary_originating_phase')}")

        print("\n[6/8] Regression (Benchmark Sets 1–3) ...")
        regression = RegressionEngine(self.v8, self.package_dir).run(
            official_model=official,
            reference_path=self.estimator_workbook,
        )
        print(f"      Regression passed={regression.get('passed')}")

        print("\n[7/8] Validation gate ...")
        validation = self._validate(official, production, comparison, kpis, regression)
        recommendation = "A" if validation.get("overall_passed") else "B"
        print(f"      Rules {validation['passed']}/{validation['total']} -> Recommendation {recommendation}")

        result: Dict[str, Any] = {
            "model_version": MODEL_VERSION,
            "phase": PHASE_ID,
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "recommendation": recommendation,
            "official_model": official,
            "production_snapshot": production,
            "comparison": comparison,
            "kpis": kpis,
            "diagnostics": diagnostics,
            "root_cause": root_cause,
            "regression": regression,
            "validation": validation,
        }

        print("\n[8/8] Exporting artefacts ...")
        paths = BenchmarkReportGenerator(self.out).export_all(result)
        result["export_paths"] = paths
        result["status"] = "PASS" if validation.get("overall_passed") else "WARN"

        print("=" * 72)
        print(f"STATUS: {result['status']} | Recommendation: {recommendation}")
        print(f"Output: {self.out}")
        print("=" * 72)
        return result

    def _validate(
        self,
        official,
        production,
        comparison,
        kpis,
        regression,
    ) -> Dict[str, Any]:
        rules = [
            ("summary_table_detected_dynamically", bool(official.interpretation.get("summary_detected"))),
            ("quantity_breakup_detected_dynamically", bool(official.interpretation.get("breakup_detected"))),
            ("overall_steel_extracted", official.steel_summary.total_kg > 0),
            ("diameter_steel_extracted", len(official.steel_summary.diameter_summary) >= 3),
            ("beam_blocks_identified", len(official.beams) > 0),
            ("reinforcement_rows_grouped", len(official.reinforcement_rows) > 0),
            ("official_engineering_model_generated", True),
            ("production_snapshot_generated", production is not None),
            ("benchmark_comparison_completed", bool(comparison)),
            ("kpis_generated", bool(kpis.get("kpis"))),
            ("root_causes_generated", True),
            ("regression_passed", bool(regression.get("passed"))),
            ("no_worksheet_name_dependency", any(
                c.get("id") == "no_worksheet_name_dependency" and c.get("passed")
                for c in (regression.get("checks") or [])
            )),
            ("no_fixed_cell_references", any(
                c.get("id") == "no_fixed_cell_references" and c.get("passed")
                for c in (regression.get("checks") or [])
            )),
            ("no_benchmark_specific_heuristics", bool(regression.get("no_benchmark_specific_rules"))),
        ]
        passed = sum(1 for _, ok in rules if ok)
        return {
            "model_version": MODEL_VERSION,
            "passed": passed,
            "total": len(rules),
            "overall_passed": passed == len(rules),
            "rules": [{"id": i, "passed": ok} for i, ok in rules],
        }
