"""
QA.2B.1 — Production Output Regeneration & Ground Truth Re-Benchmark orchestrator.
MODEL_VERSION: 9.6.1
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .benchmark_launcher import BenchmarkLauncher
from .production_regenerator import ProductionRegenerator
from .qa_reporter import QAReporter
from .regeneration_validator import RegenerationValidator

MODEL_VERSION = "9.6.1"
PHASE_ID = "QA.2B.1"


class PhaseQA2B1Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        output_root: Optional[Path] = None,
        test_input: Optional[Path] = None,
    ):
        self.engine_root = Path(engine_root)
        self.output_root = (
            Path(output_root)
            if output_root
            else self.engine_root / "data" / "output" / "PhaseQA2B1_production_regeneration"
        )
        self.test_input = (
            Path(test_input)
            if test_input
            else self.engine_root.parent / "Test_Input"
        )
        self.output_root.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print(f"Phase {PHASE_ID} - Production Output Regeneration & GT Re-Benchmark")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print(f"Output        : {self.output_root}")
        print("reuse_existing_model = False (hard requirement)")
        print("=" * 72)
        t0 = time.perf_counter()
        started_utc = datetime.now(timezone.utc).isoformat()

        regenerator = ProductionRegenerator(self.engine_root, self.output_root)
        prior = regenerator.snapshot_prior_workbooks()

        print("\n[QA.2B.1] Regenerating production outputs from DXF (full pipeline)...")
        regeneration = regenerator.regenerate_all(test_input=self.test_input)
        (self.output_root / "RegenerationResult.json").write_text(
            json.dumps(regeneration, indent=2, default=str), encoding="utf-8"
        )
        if not regeneration.get("success"):
            print("[QA.2B.1] Regeneration failed - aborting benchmark")
            return {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "success": False,
                "error": "regeneration_failed",
                "regeneration": regeneration,
                "output_root": str(self.output_root),
            }

        launcher = BenchmarkLauncher(self.engine_root, self.output_root)
        benchmark = launcher.benchmark_regenerated(
            regeneration, test_input=self.test_input
        )

        # Consolidated GroundTruth_Benchmark_Report.json (deliverable name)
        gt_json = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "reuse_existing_model": False,
            "benchmark": (benchmark.get("compiled") or {}).get("benchmark"),
            "statistics": (benchmark.get("compiled") or {}).get("statistics"),
            "dashboard": (benchmark.get("compiled") or {}).get("dashboard"),
            "errors": (benchmark.get("compiled") or {}).get("errors"),
            "drawing_sets": [
                {
                    "drawing_set": r.get("drawing_set"),
                    "compared": r.get("compared"),
                    "drawing_summary": r.get("drawing_summary"),
                    "model_summary": r.get("model_summary"),
                    "estimator_summary": r.get("estimator_summary"),
                    "beam_matching": {
                        k: (r.get("beam_matching") or {}).get(k)
                        for k in (
                            "detection_pct",
                            "matching_pct",
                            "estimator_beams",
                            "detected_beams",
                            "missing_ids",
                        )
                    },
                    "bar_matching": {
                        k: (r.get("bar_matching") or {}).get(k)
                        for k in (
                            "detection_pct",
                            "accuracy_pct",
                            "missing_bars",
                            "extra_bars",
                            "matched_bars",
                        )
                    },
                    "steel": (r.get("metrics") or {}).get("metric8_overall_steel"),
                }
                for r in (benchmark.get("results") or [])
            ],
            "elapsed_s": benchmark.get("elapsed_s"),
        }
        for dest in (
            self.output_root / "GroundTruth_Benchmark_Report.json",
            self.engine_root
            / "data"
            / "output"
            / "QA2A_GroundTruthBenchmark"
            / "GroundTruth_Benchmark_Report.json",
        ):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(gt_json, indent=2, default=str), encoding="utf-8")

        validator = RegenerationValidator(self.output_root)
        validation = validator.validate(
            prior, regeneration, benchmark, started_utc=started_utc
        )

        reporter = QAReporter(self.output_root)
        qa = reporter.write_production_qa(regeneration, benchmark, validation)
        overall_elapsed = round(time.perf_counter() - t0, 2)
        summary_path = reporter.write_execution_summary(
            regeneration,
            benchmark,
            validation,
            qa,
            overall_elapsed_s=overall_elapsed,
        )
        bench_summary = reporter.write_benchmark_summary(benchmark)

        success = bool(validation.get("overall_pass")) and bool(benchmark.get("success"))
        result = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "success": success,
            "output_root": str(self.output_root),
            "elapsed_s": overall_elapsed,
            "production_regeneration_qa": str(
                self.output_root / "ProductionRegenerationQA.json"
            ),
            "regeneration_comparison": str(
                self.output_root / "RegenerationComparison.json"
            ),
            "production_regeneration_summary": str(summary_path),
            "benchmark_summary": str(bench_summary),
            "ground_truth_xlsx": str(
                self.output_root / "GroundTruth_Benchmark_Report.xlsx"
            ),
            "ground_truth_json": str(
                self.output_root / "GroundTruth_Benchmark_Report.json"
            ),
            "validation_overall_pass": validation.get("overall_pass"),
        }
        (self.output_root / "PhaseQA2B1_result.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        print(
            f"\n[{PHASE_ID}] done success={success} elapsed={overall_elapsed}s "
            f"pass={validation.get('overall_pass')}"
        )
        return result
