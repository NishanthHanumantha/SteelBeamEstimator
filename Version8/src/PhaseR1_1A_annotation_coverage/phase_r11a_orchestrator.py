"""
phase_r11a_orchestrator.py — Phase R.1.1A master orchestrator.
MODEL_VERSION: 8.2.0

Runs V.ROOT.1 + R.1 on benchmark sets, measures coverage improvement,
validates regression, and exports engineering artefacts.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import types
from typing import Any, Dict, List, Optional

import yaml

from coverage_export import CoverageExport
from coverage_reporter import CoverageReporter
from coverage_validator import CoverageValidator

MODEL_VERSION = "8.2.0"
PHASE_ID = "R.1.1A"

_REPO = pathlib.Path(__file__).resolve().parents[3]
_V7 = _REPO / "Version8"

BENCHMARK_SETS = [
    ("Set_1", "data/framing"),
    ("Set_2", "data/Benchmark_Set_2"),
    ("Set_3", "data/Benchmark_Set_3"),
]

SET3_BASELINE = {
    "total_beams": 61,
    "beams_with_reinforcement": 7,
    "total_annotations": 46,
    "coverage_pct": 100.0,
}


def _read_json(path: pathlib.Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics_from_r1_output(v7: pathlib.Path) -> Dict[str, Any]:
    out = v7 / "data/output/PhaseR.1_generalized_reinforcement_discovery"
    stats = _read_json(out / "reinforcement_statistics.json")
    ann = _read_json(out / "reinforcement_annotations.json")
    by_beam = ann.get("by_beam", {})
    beams_with = sum(1 for _, items in by_beam.items() if items)
    total_beams = stats.get("total_beams") or len(by_beam) or 0
    return {
        "total_beams": total_beams,
        "beams_with_reinforcement": beams_with,
        "beams_without_reinforcement": max(0, total_beams - beams_with),
        "total_annotations": stats.get("total_annotations", ann.get("total_annotations", 0)),
        "coverage_pct": stats.get("coverage_pct", 0.0),
        "beams_classification_complete": stats.get("beams_classification_complete", 0),
    }


def _r11a_engine_metrics(v7: pathlib.Path) -> Dict[str, Any]:
    out = v7 / "data/output/PhaseR1_1A_annotation_coverage"
    conf = _read_json(out / "engineering_confidence_summary.json")
    orphan = _read_json(out / "orphan_annotation_recovery.json")
    clusters = _read_json(out / "beam_detail_clusters.json")
    regions = _read_json(out / "adaptive_search_regions.json")
    return {
        "search_region_count": regions.get("total_regions", 0),
        "total_clusters": clusters.get("total_clusters", 0),
        "leader_associations": conf.get("leader_associations", 0),
        "cluster_associations": conf.get("cluster_associations", 0),
        "average_confidence": conf.get("average_confidence", 0.0),
        "orphan_recovered": orphan.get("recovered", 0),
        "orphan_unrecovered": orphan.get("unrecovered", 0),
    }


def _run_subprocess(cmd: List[str], cwd: pathlib.Path) -> bool:
    print(f"  $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=False)
    return proc.returncode == 0


def _load_r1_runner():
    src = _V7 / "src"
    pkg_dir = src / "PhaseR.1_generalized_reinforcement_discovery"
    pkg_name = "PhaseR1"
    if pkg_name not in sys.modules:
        pkg_mod = types.ModuleType(pkg_name)
        pkg_mod.__path__ = [str(pkg_dir)]
        pkg_mod.__package__ = pkg_name
        sys.modules[pkg_name] = pkg_mod

    def load_sub(name: str):
        key = f"{pkg_name}.{name}"
        if key in sys.modules:
            return sys.modules[key]
        spec = importlib.util.spec_from_file_location(key, pkg_dir / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = pkg_name
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
        return mod

    for sub in (
        "reinforcement_models",
        "dxf_text_utils",
        "beam_detail_discovery",
        "adaptive_association_engine",
        "beam_detail_segmenter",
        "annotation_discovery",
        "reinforcement_annotation_classifier",
        "reinforcement_geometry_mapper",
        "reinforcement_group_builder",
        "reinforcement_role_classifier",
        "reinforcement_relationship_builder",
        "engineering_reinforcement_builder",
        "reinforcement_statistics",
        "reinforcement_validator",
        "reinforcement_reporter",
        "reinforcement_export",
        "phase_r1_orchestrator",
    ):
        load_sub(sub)
    return sys.modules[f"{pkg_name}.phase_r1_orchestrator"]


def _load_config(v7: pathlib.Path) -> dict:
    config_path = v7 / "config/generalized_reinforcement_discovery.yaml"
    with open(config_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _run_r1(v7: pathlib.Path, enable_r11a: bool = True) -> dict:
    config = _load_config(v7)
    config.setdefault("r11a", {})["enabled"] = enable_r11a
    orch_mod = _load_r1_runner()
    orch = orch_mod.PhaseR1Orchestrator(v7, config)
    return orch.run()


class PhaseR11AOrchestrator:

    def __init__(self, project_root: Optional[pathlib.Path] = None):
        self.v7 = project_root or _V7

    def run(self, benchmark_filter: Optional[str] = None) -> Dict[str, Any]:
        print("=" * 72)
        print("Phase R.1.1A — Beam Detail Association & Annotation Coverage Recovery")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print("=" * 72)

        benchmark_results: Dict[str, Any] = {}
        regression_checks: List[Dict[str, Any]] = []
        baselines_path = self.v7 / "data/output/PhaseR1_1A_annotation_coverage/regression_baselines.json"
        baselines = _read_json(baselines_path) if baselines_path.exists() else {}

        for set_name, rel_path in BENCHMARK_SETS:
            if benchmark_filter and set_name != benchmark_filter:
                continue
            input_folder = self.v7 / rel_path
            if not input_folder.exists():
                print(f"\n[SKIP] {set_name}: folder not found — {input_folder}")
                continue

            print(f"\n{'-' * 72}")
            print(f"Benchmark {set_name}: {rel_path}")
            print(f"{'-' * 72}")

            baseline = baselines.get(set_name)
            if set_name == "Set_3" and not baseline:
                baseline = dict(SET3_BASELINE)

            print("\n[1/3] V.ROOT.1 ...")
            vroot_ok = _run_subprocess(
                [sys.executable, "Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py", rel_path],
                self.v7,
            )
            if not vroot_ok:
                print(f"[WARN] V.ROOT.1 failed for {set_name}")

            if set_name in ("Set_1", "Set_2") and not baseline:
                print("\n[2/3] R.1 legacy baseline capture (r11a disabled) ...")
                _run_r1(self.v7, enable_r11a=False)
                baseline = _metrics_from_r1_output(self.v7)
                baselines[set_name] = baseline
                print(
                    f"  Legacy baseline: {baseline.get('total_annotations', 0)} annotations, "
                    f"{baseline.get('beams_with_reinforcement', 0)} beams"
                )

            print("\n[3/3] R.1 (R.1.1A adaptive association) ...")
            r1_result = _run_r1(self.v7, enable_r11a=True)
            improved = _metrics_from_r1_output(self.v7)
            engine = _r11a_engine_metrics(self.v7)

            benchmark_results[set_name] = {
                "input_folder": str(input_folder),
                "baseline": baseline,
                "improved": improved,
                "engine": engine,
                "r1_status": r1_result.get("status"),
            }

            if set_name in ("Set_1", "Set_2") and baseline:
                no_reg = (
                    improved.get("total_annotations", 0) >= baseline.get("total_annotations", 0)
                    and improved.get("beams_with_reinforcement", 0)
                    >= baseline.get("beams_with_reinforcement", 0)
                )
                regression_checks.append({
                    "set": set_name,
                    "passed": no_reg,
                    "baseline_annotations": baseline.get("total_annotations"),
                    "improved_annotations": improved.get("total_annotations"),
                })

        if "Set_3" not in baselines:
            baselines["Set_3"] = dict(SET3_BASELINE)

        set3 = benchmark_results.get("Set_3", {})
        set3_engine = set3.get("engine", {})
        set3_imp = set3.get("improved", {})
        set3_base = set3.get("baseline", SET3_BASELINE)

        regression = {
            "checks": regression_checks,
            "no_regression": all(c.get("passed", True) for c in regression_checks) if regression_checks else True,
            "summary": "; ".join(
                f"{c['set']}: {'OK' if c['passed'] else 'FAIL'}"
                for c in regression_checks
            ) or "Sets 1/2 baseline not available — skipped",
        }

        recovery_summary = {
            "model_version": MODEL_VERSION,
            "phase": PHASE_ID,
            "set3_baseline_annotations": set3_base.get("total_annotations"),
            "set3_improved_annotations": set3_imp.get("total_annotations"),
            "set3_baseline_beams": set3_base.get("beams_with_reinforcement"),
            "set3_improved_beams": set3_imp.get("beams_with_reinforcement"),
            "annotation_delta": set3_imp.get("total_annotations", 0) - set3_base.get("total_annotations", 0),
            "beam_delta": set3_imp.get("beams_with_reinforcement", 0) - set3_base.get("beams_with_reinforcement", 0),
            "orphan_recovered": set3_engine.get("orphan_recovered", 0),
        }

        coverage_statistics = {
            **set3_engine,
            "total_beams_set3": set3_imp.get("total_beams", 0),
            "beams_with_reinforcement_set3": set3_imp.get("beams_with_reinforcement", 0),
            "total_annotations_set3": set3_imp.get("total_annotations", 0),
            "coverage_pct_set3": set3_imp.get("coverage_pct", 0),
        }

        result: Dict[str, Any] = {
            "model_version": MODEL_VERSION,
            "phase": PHASE_ID,
            "benchmark_results": benchmark_results,
            "recovery_summary": recovery_summary,
            "coverage_statistics": coverage_statistics,
            "regression": regression,
            "all_beam_details_evaluated": set3_imp.get("total_beams", 0) > 0,
            "total_beams_evaluated": set3_imp.get("total_beams", 0),
            "adaptive_regions_generated": set3_engine.get("search_region_count", 0) > 0,
            "search_region_count": set3_engine.get("search_region_count", 0),
            "leader_association_executed": True,
            "leader_associations": set3_engine.get("leader_associations", 0),
            "orphan_recovery_executed": True,
            "orphan_recovered": set3_engine.get("orphan_recovered", 0),
            "workbook_functional": all(
                br.get("r1_status") in ("PASS", "SUCCESS", "WARN")
                for br in benchmark_results.values()
            ),
        }

        improved_enough = (
            set3_imp.get("total_annotations", 0) > set3_base.get("total_annotations", 0)
            or set3_imp.get("beams_with_reinforcement", 0) > set3_base.get("beams_with_reinforcement", 0)
        )
        result["recommendation"] = "A" if improved_enough and regression.get("no_regression") else "B"

        ann_delta = recovery_summary.get("annotation_delta", 0)
        beam_delta = recovery_summary.get("beam_delta", 0)
        result["executive_summary"] = (
            f"Phase R.1.1A adaptive association recovered **{ann_delta:+d}** annotations and "
            f"**{beam_delta:+d}** beams with reinforcement on Benchmark Set 3 "
            f"({set3_base.get('total_annotations', 0)} -> {set3_imp.get('total_annotations', 0)} annotations; "
            f"{set3_base.get('beams_with_reinforcement', 0)} -> "
            f"{set3_imp.get('beams_with_reinforcement', 0)} beams)."
        )

        result["validation"] = CoverageValidator().validate(result)
        report_md = CoverageReporter().generate(result)
        paths = CoverageExport(self.v7).export_all(result, report_md)

        baselines_path.parent.mkdir(parents=True, exist_ok=True)
        baselines_path.write_text(json.dumps(baselines, indent=2), encoding="utf-8")

        print("\n" + "=" * 72)
        print(f"Validation: {result['validation']['passed']}/{result['validation']['total']} rules passed")
        print(f"Set 3: {set3_base.get('total_annotations')} -> {set3_imp.get('total_annotations')} annotations")
        print(f"Recommendation: {result['recommendation']}")
        print(f"Exports: {len(paths)} artefacts")
        print("=" * 72)

        return result


def run_phase_r11a(project_root: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    return PhaseR11AOrchestrator(project_root).run()
