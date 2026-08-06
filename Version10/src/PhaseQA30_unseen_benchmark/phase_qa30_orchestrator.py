"""
QA.3.0 — Unseen Drawing Benchmark orchestrator.
MODEL_VERSION: 10.0.0

Orchestration only. Reuses Version10 production pipeline + QA.2A formulas.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .benchmark_executor import BenchmarkExecutor
from .drawing_set_discovery import DrawingSetDiscovery
from .generalization_report import (
    build_engineering_error_summary,
    build_generalization_assessment,
    write_generalization_json,
    write_generalization_summary_md,
    write_generalization_xlsx,
)
from .production_executor import ProductionExecutor
from .qa_validator import QAValidator
from .report_builder import (
    print_completion_summary,
    write_execution_summary,
    write_phase_readme,
)

MODEL_VERSION = "10.0.0"
PHASE_ID = "QA.3.0"


class PhaseQA30Orchestrator:
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
            else self.engine_root / "data" / "output" / "PhaseQA30_unseen_benchmark"
        )
        self.test_input = (
            Path(test_input)
            if test_input
            else self.engine_root.parent / "Test_Input"
        )
        self.output_root.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print(f"Phase {PHASE_ID} - Unseen Drawing Benchmark (Generalization)")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print(f"Engine        : {self.engine_root}")
        print(f"Test_Input    : {self.test_input}")
        print(f"Output        : {self.output_root}")
        print("Estimator Excel: BENCHMARK ONLY (never during production)")
        print("=" * 72)
        t0 = time.perf_counter()

        # 1) Discover
        disco = DrawingSetDiscovery(self.test_input)
        all_sets = disco.discover()
        discovery_doc = disco.write_report(
            self.output_root / "DrawingSetDiscovery.json", all_sets
        )
        targets = [
            s for s in all_sets if s.is_unseen_target and s.is_complete
        ]
        # Stable order: Fourth, Fifth, Sixth
        order = {"Fourth": 0, "Fifth": 1, "Sixth": 2}
        targets.sort(key=lambda s: order.get(s.set_key, 99))

        print(f"\n[{PHASE_ID}] Discovered {len(all_sets)} set(s); "
              f"complete unseen targets={len(targets)}")
        for s in targets:
            print(f"  - {s.name} [{s.set_key}]")

        if len(targets) < 3:
            err = {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "success": False,
                "error": "incomplete_unseen_targets",
                "discovery": discovery_doc,
                "output_root": str(self.output_root),
            }
            (self.output_root / "PhaseQA30_result.json").write_text(
                json.dumps(err, indent=2, default=str), encoding="utf-8"
            )
            return err

        # 2) Production (DXF only)
        prod_ex = ProductionExecutor(self.engine_root, self.output_root)
        production = prod_ex.run_all(targets)
        (self.output_root / "ProductionResult.json").write_text(
            json.dumps(production, indent=2, default=str), encoding="utf-8"
        )
        if not production.get("success"):
            print(f"[{PHASE_ID}] Production failed - aborting benchmark")
            result = {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "success": False,
                "error": "production_failed",
                "production": production,
                "output_root": str(self.output_root),
            }
            (self.output_root / "PhaseQA30_result.json").write_text(
                json.dumps(result, indent=2, default=str), encoding="utf-8"
            )
            return result

        # 3) Benchmark (estimator Excel ONLY here)
        bench_ex = BenchmarkExecutor(self.engine_root, self.output_root)
        benchmark = bench_ex.benchmark_production(production)
        (self.output_root / "BenchmarkResult.json").write_text(
            json.dumps(
                {
                    k: v
                    for k, v in benchmark.items()
                    if k not in ("compiled", "results")
                }
                | {
                    "drawing_sets": [
                        r.get("drawing_set") for r in (benchmark.get("results") or [])
                    ],
                    "compared_count": sum(
                        1 for r in (benchmark.get("results") or []) if r.get("compared")
                    ),
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        # 4) Generalization reports
        eng = build_engineering_error_summary(benchmark)
        (self.output_root / "EngineeringErrorSummary.json").write_text(
            json.dumps(eng, indent=2), encoding="utf-8"
        )
        assessment = build_generalization_assessment(benchmark, eng)
        report = write_generalization_json(
            self.output_root / "Generalization_Benchmark_Report.json",
            production,
            benchmark,
            eng,
            assessment,
        )
        write_generalization_summary_md(
            self.output_root / "GeneralizationSummary.md", report
        )
        write_generalization_xlsx(
            self.output_root / "Generalization_Benchmark_Report.xlsx",
            report,
            benchmark.get("compiled") or {},
            benchmark.get("results") or [],
            self.engine_root,
        )

        report_paths = {
            "json": str(self.output_root / "Generalization_Benchmark_Report.json"),
            "xlsx": str(self.output_root / "Generalization_Benchmark_Report.xlsx"),
            "md": str(self.output_root / "GeneralizationSummary.md"),
        }

        # 5) QA validation
        validator = QAValidator(self.output_root, self.engine_root)
        validation = validator.validate(
            discovery_doc, production, benchmark, report_paths
        )

        overall_elapsed = round(time.perf_counter() - t0, 2)
        write_execution_summary(
            self.output_root / "ExecutionSummary.md",
            discovery_doc,
            production,
            benchmark,
            validation,
            report,
            overall_elapsed,
        )
        write_phase_readme(self.output_root / "README.md")

        success = bool(validation.get("overall_pass")) and bool(benchmark.get("success"))
        result = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "success": success,
            "output_root": str(self.output_root),
            "elapsed_s": overall_elapsed,
            "validation_overall_pass": validation.get("overall_pass"),
            "report_paths": report_paths,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        (self.output_root / "PhaseQA30_result.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )

        print_completion_summary(production, report, validation, overall_elapsed)
        return result
