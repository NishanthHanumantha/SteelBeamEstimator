"""
Phase R.1.2B Orchestrator — EngineeringBar Deduplication & Consolidation
MODEL_VERSION: 8.3.1
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import time
import types
from typing import Any, Dict, List, Optional

MODEL_VERSION = "8.3.1"


def _load_pkg(pkg_name: str, pkg_dir: pathlib.Path, subs: List[str]):
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(pkg_dir)]
        pkg.__package__ = pkg_name
        sys.modules[pkg_name] = pkg
    for sub in subs:
        key = f"{pkg_name}.{sub}"
        if key in sys.modules:
            del sys.modules[key]
        spec = importlib.util.spec_from_file_location(key, pkg_dir / f"{sub}.py")
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = pkg_name
        sys.modules[key] = mod
        spec.loader.exec_module(mod)


def _run(cmd: List[str], cwd: pathlib.Path) -> int:
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, cwd=str(cwd)).returncode


class PhaseR12BOrchestrator:

    def __init__(self, v7_root: Optional[pathlib.Path] = None):
        self.v7 = v7_root or pathlib.Path(__file__).resolve().parents[2]
        self._src = pathlib.Path(__file__).parent

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print("Phase R.1.2B - EngineeringBar Deduplication & Consolidation Engine")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print("=" * 72)
        t0 = time.perf_counter()

        _load_pkg("PhaseR12B", self._src, [
            "physical_reinforcement_model",
            "engineeringbar_duplicate_detector",
            "engineeringbar_consolidator",
            "consolidation_service",
            "consolidation_validators",
            "consolidation_report_exporter",
        ])
        Detector = sys.modules[
            "PhaseR12B.engineeringbar_duplicate_detector"
        ].EngineeringBarDuplicateDetector
        Service = sys.modules[
            "PhaseR12B.consolidation_service"
        ].EngineeringBarConsolidationService
        validators = sys.modules["PhaseR12B.consolidation_validators"]
        Exporter = sys.modules[
            "PhaseR12B.consolidation_report_exporter"
        ].ConsolidationReportExporter

        # 1. Build pre-consolidation EngineeringBars (R.1.3 path without merge)
        print("\n[1/7] Auditing EngineeringBars before consolidation ...")
        before_models = self._build_raw_beam_dicts()
        detector = Detector()
        audit_before = detector.audit(before_models)
        detection = detector.detect(before_models)
        print(
            f"      Bars={audit_before['total_engineering_bars']} "
            f"dup_groups={detection['duplicate_group_count']} "
            f"redundant={detection['redundant_bar_count']}"
        )

        diameter_before = validators.diameter_distribution(
            before_models, "before_consolidation"
        )

        # 2. Consolidate offline for artefacts
        print("\n[2/7] Consolidating Physical Reinforcement Members ...")
        service = Service()
        after_models, payload = service.apply(before_models)
        detection_after = detector.detect(after_models)
        diameter_after = validators.diameter_distribution(
            after_models, "after_consolidation"
        )
        diameter_comparison = validators.compare_diameter_distributions(
            diameter_before, diameter_after
        )
        print(
            f"      Bars {payload['report']['bars_before']} -> "
            f"{payload['report']['bars_after']} "
            f"(removed {payload['report']['bars_removed_as_duplicates']})"
        )

        # 3. Rebuild production R.1.3 + V.B.1 with consolidation wired in
        print("\n[3/7] Rebuilding R.1.3 + V.B.1 with consolidation enabled ...")
        _run([sys.executable, "Run_PY/run_phase_r13_pipeline_integration.py"], self.v7)
        vb1 = self.v7 / "Run_PY/run_phase_vb1_production_output_completion.py"
        if vb1.exists():
            _run([sys.executable, str(vb1.relative_to(self.v7))], self.v7)

        # 4. Validate
        print("\n[4/7] Consolidation / BBS / diameter validation ...")
        consol_val = validators.ConsolidationValidator().validate(
            audit_before,
            detection,
            after_models,
            payload.get("physical_members") or [],
            detection_after,
        )
        bbs_validation = validators.BBSConsolidationValidator().validate(self.v7)
        regression = validators.RegressionConsolidationValidator().validate(
            self.v7, payload.get("report") or {}
        )
        validation = validators.PhaseRulesValidator().validate(
            consol_val, diameter_comparison, bbs_validation, regression
        )
        print(f"      Rules {validation['passed']}/{validation['total']} passed")
        print(f"      BBS passed={bbs_validation.get('passed')} "
              f"issues={bbs_validation.get('issue_count')}")

        # 5. Recommendation
        improved = bool(diameter_comparison.get("diameter_distribution_improved"))
        clean_bbs = bool(bbs_validation.get("passed"))
        no_reg = bool(regression.get("no_regression"))
        recommendation = (
            "A"
            if improved
            and clean_bbs
            and no_reg
            and validation.get("passed", 0) >= 7
            else "B"
        )

        result: Dict[str, Any] = {
            "model_version": MODEL_VERSION,
            "phase": "R.1.2B",
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "recommendation": recommendation,
            "audit_before": audit_before,
            "detection": detection,
            "detection_after": detection_after,
            "consol_report": payload.get("report") or {},
            "physical_members": payload.get("physical_members") or [],
            "traceability": payload.get("traceability") or [],
            "diameter_before": diameter_before,
            "diameter_after": diameter_after,
            "diameter_comparison": diameter_comparison,
            "bbs_validation": bbs_validation,
            "regression": regression,
            "consol_validation": consol_val,
            "validation": validation,
        }

        print("\n[5/7] Exporting artefacts ...")
        exporter = Exporter(self.v7)
        report_md = exporter.generate_report(result)
        exports = exporter.export_all(result, report_md)

        print("\n[6/7] Summary")
        print(f"      Duplicate groups: {detection.get('duplicate_group_count')}")
        print(f"      Weight pct change: {diameter_comparison.get('totals', {}).get('weight_pct_change')}")
        print(f"      Recommendation: {recommendation}")

        print("\n[7/7] Done")
        print("=" * 72)

        result["status"] = "PASS" if validation.get("overall_passed") else "WARN"
        result["export_paths"] = exports
        return result

    def _build_raw_beam_dicts(self) -> List[Dict[str, Any]]:
        """Build EngineeringBars via R.1.3 adapters without consolidation."""
        r13_dir = self.v7 / "src/PhaseR1.3_pipeline_integration"
        _load_pkg("PhaseR13", r13_dir, [
            "engineering_bar_model",
            "engineering_bar_builder",
            "reinforcement_source_selector",
            "reinforcement_pipeline_adapter",
            "l2_engineering_processor",
        ])
        Selector = sys.modules[
            "PhaseR13.reinforcement_source_selector"
        ].ReinforcementSourceSelector
        Adapter = sys.modules[
            "PhaseR13.reinforcement_pipeline_adapter"
        ].ReinforcementPipelineAdapter
        Processor = sys.modules[
            "PhaseR13.l2_engineering_processor"
        ].L2EngineeringProcessor

        selector = Selector(self.v7)
        ctx = self._load_ctx()
        adapter = Adapter(
            selector.r1_models_path(),
            selector.beam_registry_path(),
            ctx,
        )
        beam_models, _stats = adapter.load_and_convert()
        Processor().process(beam_models)
        return [bm.to_dict() for bm in beam_models]

    def _load_ctx(self) -> Dict[str, Any]:
        try:
            r2a_dir = self.v7 / "src/PhaseR.2A_engineering_context"
            if "PhaseR2A" not in sys.modules:
                pkg = types.ModuleType("PhaseR2A")
                pkg.__path__ = [str(r2a_dir)]
                sys.modules["PhaseR2A"] = pkg
            key = "PhaseR2A.engineering_context_parser"
            if key not in sys.modules:
                spec = importlib.util.spec_from_file_location(
                    key, r2a_dir / "engineering_context_parser.py"
                )
                mod = importlib.util.module_from_spec(spec)
                mod.__package__ = "PhaseR2A"
                sys.modules[key] = mod
                spec.loader.exec_module(mod)
            parser = sys.modules[key]
            loader, _, _ = parser.parse_engineering_context(self.v7)
            return (loader.summary() or {}) if loader else {}
        except Exception:
            return {}
