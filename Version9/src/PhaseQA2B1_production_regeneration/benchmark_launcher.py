"""
QA.2B.1 — BenchmarkLauncher
MODEL_VERSION: 9.6.1

Runs QA.2A ground-truth comparison against freshly regenerated workbooks.
Does NOT pass --reuse-existing-model. Does NOT load prior Estimation_Output.xlsx.

Comparison uses unmodified QA.2A matcher / metrics modules; only the workbook
paths are supplied from the regeneration result.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import time
import types
from pathlib import Path
from typing import Any, Dict, List, Optional

MODEL_VERSION = "9.6.1"
PHASE_ID = "QA.2B.1"

_SUBMODULES = [
    "__init__",
    "gt_models",
    "workbook_normalizer",
    "beam_matcher",
    "bar_matcher",
    "metrics_engine",
    "error_classifier",
    "report_compiler",
    "json_exporter",
    "excel_exporter",
    "phase_qa2a_orchestrator",
]


class BenchmarkLauncher:
    def __init__(self, engine_root: Path, output_root: Path):
        self.engine_root = Path(engine_root)
        self.output_root = Path(output_root)
        self.qa2a_out = self.engine_root / "data" / "output" / "QA2A_GroundTruthBenchmark"
        self.output_root.mkdir(parents=True, exist_ok=True)

    def _bootstrap_qa2a(self) -> types.ModuleType:
        v9 = self.engine_root
        os.chdir(v9)
        pkg_dir = v9 / "src" / "PhaseQA.2A_ground_truth_benchmark"
        alias = "PhaseQA2A"
        r14 = str(v9 / "src" / "PhaseR1_4_production_accuracy_benchmark")
        for p in (r14, str(v9)):
            if p not in sys.path:
                sys.path.insert(0, p)

        # Fresh package each launch to avoid stale modules from prior phases
        pkg = types.ModuleType(alias)
        pkg.__path__ = [str(pkg_dir)]
        pkg.__package__ = alias
        sys.modules[alias] = pkg

        loaded = {}
        for sub in _SUBMODULES:
            full = f"{alias}.{sub}"
            spec = importlib.util.spec_from_file_location(full, pkg_dir / f"{sub}.py")
            mod = importlib.util.module_from_spec(spec)
            mod.__package__ = alias
            sys.modules[full] = mod
            loaded[sub] = (spec, mod)
            if sub != "__init__":
                setattr(pkg, sub, mod)
                sys.modules[sub] = mod

        for sub in _SUBMODULES:
            spec, mod = loaded[sub]
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            if sub == "__init__":
                for attr, val in vars(mod).items():
                    if not attr.startswith("__"):
                        setattr(pkg, attr, val)
            else:
                sys.modules[sub] = mod
                setattr(pkg, sub, mod)
        return pkg

    def benchmark_regenerated(
        self,
        regeneration: Dict[str, Any],
        *,
        test_input: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Compare each regenerated Model Excel to estimator GT using QA.2A engines.
        Writes standard QA.2A report artefacts (xlsx/json) as the 9.6.1 benchmark.
        """
        print("\n[QA.2B.1] Launching QA.2A benchmark on regenerated workbooks only...")
        print("  reuse_existing_model=False (forced)")
        t0 = time.perf_counter()
        self._bootstrap_qa2a()

        WorkbookNormalizer = sys.modules["workbook_normalizer"].WorkbookNormalizer
        BeamMatcher = sys.modules["beam_matcher"].BeamMatcher
        BarMatcher = sys.modules["bar_matcher"].BarMatcher
        MetricsEngine = sys.modules["metrics_engine"].MetricsEngine
        ErrorClassifier = sys.modules["error_classifier"].ErrorClassifier
        compile_results = sys.modules["report_compiler"].compile_results
        export_compiled = sys.modules["json_exporter"].export_compiled
        export_drawing_set = sys.modules["json_exporter"].export_drawing_set
        ExcelExporter = sys.modules["excel_exporter"].ExcelExporter

        normalizer = WorkbookNormalizer()
        beam_matcher = BeamMatcher()
        bar_matcher = BarMatcher()
        metrics_engine = MetricsEngine()
        error_clf = ErrorClassifier()

        results: List[Dict[str, Any]] = []
        per_set_timing: List[Dict[str, Any]] = []

        for item in regeneration.get("sets") or []:
            t_set = time.perf_counter()
            ds_name = item["drawing_set"]
            model_excel = Path((item.get("workbook") or {}).get("path") or "")
            est_excel = Path(item.get("estimator_excel") or "")
            print(f"\n[QA.2B.1][BENCH] {ds_name}")
            print(f"  model={model_excel}")
            if not model_excel.exists() or not est_excel.exists():
                results.append(
                    {
                        "drawing_set": ds_name,
                        "compared": False,
                        "error": "missing_model_or_estimator_excel",
                        "pipeline": item.get("pipeline"),
                    }
                )
                continue

            # Guard: reject prior workbook paths / hashes
            if item.get("reused"):
                results.append(
                    {
                        "drawing_set": ds_name,
                        "compared": False,
                        "error": "reuse_detected_blocked",
                    }
                )
                continue

            estimator = normalizer.normalize(est_excel, "ESTIMATOR")
            model = normalizer.normalize(model_excel, "MODEL")
            beam_matching = beam_matcher.match(estimator, model)
            pairs = beam_matcher.matched_beam_pairs(estimator, model, beam_matching)
            unmatched_est = [
                b
                for b in estimator.beams
                if b.beam_id in (beam_matching.get("missing_ids") or [])
            ]
            bar_matching = bar_matcher.match_all(ds_name, pairs, unmatched_est)
            metrics = metrics_engine.compute(
                ds_name, estimator, model, beam_matching, bar_matching
            )
            errors = error_clf.classify(
                ds_name,
                beam_matching,
                bar_matching,
                metrics["metric8_overall_steel"],
            )
            bench_s = round(time.perf_counter() - t_set, 2)
            per_set_timing.append(
                {
                    "drawing_set": ds_name,
                    "set_key": item.get("set_key"),
                    "benchmark_elapsed_s": bench_s,
                    "pipeline_elapsed_s": item.get("pipeline_elapsed_s"),
                }
            )
            print(
                f"  beams={beam_matching['detection_pct']}% "
                f"bars={bar_matching['detection_pct']}% "
                f"steel={metrics['metric8_overall_steel']['accuracy_pct']}%"
            )
            results.append(
                {
                    "drawing_set": ds_name,
                    "pipeline": {
                        **(item.get("pipeline") or {}),
                        "reused": False,
                        "model_excel": str(model_excel),
                        "success": True,
                    },
                    "compared": True,
                    "beam_matching": beam_matching,
                    "bar_matching": bar_matching,
                    "metrics": metrics,
                    "errors": errors,
                    "drawing_summary": {
                        "drawing_set": ds_name,
                        "pipeline_success": True,
                        "pipeline_elapsed_s": item.get("pipeline_elapsed_s"),
                        "model_excel": str(model_excel),
                        "estimator_excel": str(est_excel),
                        "beam_detection_pct": beam_matching["detection_pct"],
                        "beam_matching_pct": beam_matching["matching_pct"],
                        "bar_detection_pct": bar_matching["detection_pct"],
                        "bar_accuracy_pct": bar_matching["accuracy_pct"],
                        "steel_accuracy_pct": metrics["metric8_overall_steel"][
                            "accuracy_pct"
                        ],
                        "estimator_kg": metrics["metric8_overall_steel"][
                            "estimator_total_kg"
                        ],
                        "model_kg": metrics["metric8_overall_steel"]["model_total_kg"],
                        "error_count": errors["total_errors"],
                    },
                    "estimator_summary": {
                        "beams": len(estimator.beams),
                        "bars": sum(len(b.bars) for b in estimator.beams),
                        "kg": estimator.total_steel_kg,
                    },
                    "model_summary": {
                        "beams": len(model.beams),
                        "bars": sum(len(b.bars) for b in model.beams),
                        "kg": model.total_steel_kg,
                    },
                }
            )

        compiled = compile_results(results)
        elapsed = round(time.perf_counter() - t0, 2)

        # Canonical QA.2A output location (updated 9.6.1 artefacts)
        self.qa2a_out.mkdir(parents=True, exist_ok=True)
        for r in results:
            if r.get("compared"):
                export_drawing_set(self.qa2a_out, r)
        export_compiled(self.qa2a_out, compiled, elapsed)
        xlsx = self.qa2a_out / "GroundTruth_Benchmark_Report.xlsx"
        ExcelExporter().export(xlsx, compiled, [r for r in results if r.get("compared")])

        # Mirror into PhaseQA2B1 output
        import json
        import shutil

        for name in (
            "GroundTruth_Benchmark_Report.xlsx",
            "GroundTruth_Benchmark_Report.json",
            "compiled_benchmark.json",
        ):
            src = self.qa2a_out / name
            if src.exists():
                shutil.copy2(src, self.output_root / name)

        # Prefer compiled export name used by json_exporter
        for cand in self.qa2a_out.glob("*.json"):
            if "GroundTruth" in cand.name or cand.name.startswith("compiled"):
                shutil.copy2(cand, self.output_root / cand.name)

        summary = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "reuse_existing_model": False,
            "success": all(r.get("compared") for r in results) and len(results) > 0,
            "elapsed_s": elapsed,
            "qa2a_output": str(self.qa2a_out),
            "excel_report": str(xlsx),
            "compiled": compiled,
            "results": results,
            "per_set_timing": per_set_timing,
            "compared_count": sum(1 for r in results if r.get("compared")),
        }
        (self.output_root / "BenchmarkLaunchResult.json").write_text(
            json.dumps(
                {
                    k: v
                    for k, v in summary.items()
                    if k not in ("compiled", "results")
                }
                | {
                    "drawing_sets": [r.get("drawing_set") for r in results],
                    "compared_count": summary["compared_count"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return summary
