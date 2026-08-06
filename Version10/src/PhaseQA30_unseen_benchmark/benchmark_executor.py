"""
QA.3.0 — BenchmarkExecutor
MODEL_VERSION: 10.0.0

Loads estimator Excel ONLY here (post-production) and runs unmodified QA.2A
matchers / metrics against freshly generated Model workbooks.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "10.0.0"
PHASE_ID = "QA.3.0"

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


class BenchmarkExecutor:
    def __init__(self, engine_root: Path, phase_output_root: Path):
        self.engine_root = Path(engine_root)
        self.phase_output_root = Path(phase_output_root)

    def _bootstrap_qa2a(self) -> None:
        v10 = self.engine_root
        os.chdir(v10)
        pkg_dir = v10 / "src" / "PhaseQA.2A_ground_truth_benchmark"
        alias = "PhaseQA2A"
        r14 = str(v10 / "src" / "PhaseR1_4_production_accuracy_benchmark")
        for p in (r14, str(v10)):
            if p not in sys.path:
                sys.path.insert(0, p)

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

    def benchmark_production(self, production: Dict[str, Any]) -> Dict[str, Any]:
        print(f"\n[{PHASE_ID}] BENCHMARK - loading estimator Excel for GT comparison only")
        self._bootstrap_qa2a()

        WorkbookNormalizer = sys.modules["workbook_normalizer"].WorkbookNormalizer
        BeamMatcher = sys.modules["beam_matcher"].BeamMatcher
        BarMatcher = sys.modules["bar_matcher"].BarMatcher
        MetricsEngine = sys.modules["metrics_engine"].MetricsEngine
        ErrorClassifier = sys.modules["error_classifier"].ErrorClassifier
        compile_results = sys.modules["report_compiler"].compile_results

        normalizer = WorkbookNormalizer()
        beam_matcher = BeamMatcher()
        bar_matcher = BarMatcher()
        metrics_engine = MetricsEngine()
        error_clf = ErrorClassifier()

        results: List[Dict[str, Any]] = []
        t0 = time.perf_counter()

        for item in production.get("sets") or []:
            ds_name = item["drawing_set"]
            set_key = item.get("set_key")
            model_excel = Path(item.get("model_excel") or "")
            est_excel = Path(item.get("estimator_excel") or "")
            set_dir = Path(item.get("set_output_dir") or self.phase_output_root)

            print(f"  [{set_key}] GT={est_excel.name if est_excel.exists() else 'MISSING'}")
            print(f"         Model={model_excel}")

            if not model_excel.exists() or not est_excel.exists():
                results.append(
                    {
                        "drawing_set": ds_name,
                        "set_key": set_key,
                        "compared": False,
                        "error": "missing_model_or_estimator",
                        "estimator_excel_opened": False,
                    }
                )
                continue

            # FIRST (and only) open of estimator workbook — benchmark stage
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

            row = {
                "drawing_set": ds_name,
                "set_key": set_key,
                "compared": True,
                "estimator_excel_opened": True,
                "estimator_excel_stage": "benchmark_only",
                "pipeline": {
                    "success": True,
                    "reused": False,
                    "model_excel": str(model_excel),
                    "elapsed_s": item.get("pipeline_elapsed_s"),
                    "run_root": item.get("run_root"),
                },
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
                    "steel_accuracy_pct": metrics["metric8_overall_steel"]["accuracy_pct"],
                    "estimator_kg": metrics["metric8_overall_steel"]["estimator_total_kg"],
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
            results.append(row)
            (set_dir / "benchmark_result.json").write_text(
                json.dumps(
                    {
                        "drawing_summary": row["drawing_summary"],
                        "estimator_summary": row["estimator_summary"],
                        "model_summary": row["model_summary"],
                        "beam_matching": {
                            k: beam_matching.get(k)
                            for k in (
                                "detection_pct",
                                "matching_pct",
                                "estimator_beams",
                                "detected_beams",
                                "missing_ids",
                            )
                        },
                        "bar_matching": {
                            k: bar_matching.get(k)
                            for k in (
                                "detection_pct",
                                "accuracy_pct",
                                "missing_bars",
                                "extra_bars",
                                "matched_bars",
                            )
                        },
                        "steel": metrics.get("metric8_overall_steel"),
                        "errors": errors.get("frequency"),
                        "estimator_excel_opened": True,
                        "estimator_excel_stage": "benchmark_only",
                    },
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
            print(
                f"         beam={beam_matching['detection_pct']}% "
                f"bar={bar_matching['detection_pct']}% "
                f"match={bar_matching['accuracy_pct']}% "
                f"steel={metrics['metric8_overall_steel']['accuracy_pct']}%"
            )

        compiled = compile_results(results)
        elapsed = round(time.perf_counter() - t0, 2)
        return {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "success": all(r.get("compared") for r in results) and len(results) > 0,
            "elapsed_s": elapsed,
            "estimator_excel_opened_during_benchmark": True,
            "estimator_excel_opened_during_production": False,
            "compiled": compiled,
            "results": results,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
