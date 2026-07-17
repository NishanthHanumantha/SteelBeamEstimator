"""
Phase R.2B Orchestrator — Engineering Context Consumption Engine
MODEL_VERSION: 7.6.0
"""
from __future__ import annotations
import pathlib
import sys
import time
from datetime import datetime
from typing import Any, Dict

from .engineering_context_dependency_mapper import EngineeringContextDependencyMapper
from .engineering_context_usage_validator import EngineeringContextUsageValidator
from .engineering_context_statistics import EngineeringContextConsumptionStatistics
from .engineering_context_export import EngineeringContextExport
from .engineering_context_reporter import EngineeringContextReporter


class PhaseR2BOrchestrator:

    def __init__(self, v7_root: pathlib.Path, output_dir: pathlib.Path):
        self._v7 = v7_root
        self._out = output_dir
        self._src = v7_root / "src"

    def run(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        print(f"\n{'='*70}")
        print("  PHASE R.2B — Engineering Context Consumption Engine")
        print(f"  MODEL_VERSION 7.6.0  |  {datetime.utcnow().isoformat()}")
        print(f"{'='*70}\n")

        # [1] Load EngineeringContext
        print("[1/5] Loading EngineeringContext ...")
        loader = self._load_engineering_context()
        if loader is None:
            return {"status": "FAIL", "reason": "EngineeringContext not available"}
        summary = loader.summary()
        print(f"      Steel grade:  {summary['primary_steel_grade']}")
        print(f"      Cover (beam): {summary['cover_beam_mm']} mm")
        print(f"      DL factor:    {summary['dev_length_factor']}d")
        print(f"      Hook 135:     {summary['hook_multiple_135']}d")

        # [2] Dependency discovery
        print("\n[2/5] Engineering dependency discovery ...")
        mapper = EngineeringContextDependencyMapper(self._src)
        dep_map = mapper.map_dependencies()
        hc_audit = mapper.hardcoded_audit()
        print(f"      Modules scanned: {len(dep_map['nodes'])}")
        print(f"      Consumption:     {dep_map['consumption_rate']} ({dep_map['consumption_pct']}%)")

        # [3] Run production pipeline with loader
        print("\n[3/5] Running production pipeline (VB1) with EngineeringContext ...")
        prod_result = self._run_production(loader)
        print(f"      Steel weight:    {prod_result.get('steel_weight_kg', 0):.3f} kg")
        print(f"      Workbook:        {prod_result.get('workbook_path', 'N/A')}")

        # [4] Validate 12 rules
        print("\n[4/5] Running 12-rule consumption validation ...")
        sw_path = self._src / "PhaseVB.1_production_output_completion" / "steel_weight_completion.py"
        sw_text = sw_path.read_text(encoding="utf-8") if sw_path.exists() else ""
        validator = EngineeringContextUsageValidator()
        results = validator.validate(loader, dep_map, prod_result, sw_text)
        passed = sum(1 for r in results if r.passed)
        for r in results:
            st = "PASS" if r.passed else "FAIL"
            print(f"      [{st}] {r.rule_id}: {r.parameter}")

        # [5] Export
        print(f"\n[5/5] Exporting artefacts to: {self._out}")
        elapsed = time.perf_counter() - t0
        stats = EngineeringContextConsumptionStatistics().compute(
            loader, dep_map, prod_result, elapsed
        )
        exporter = EngineeringContextExport(self._out)
        paths = exporter.write_all(
            dep_map, hc_audit, results, stats, summary, prod_result
        )
        for name, path in paths.items():
            print(f"      {name}: {path}")

        all_pass = passed == len(results) and prod_result.get("status") == "PASS"
        print(f"\n{'='*70}")
        print(f"  PHASE R.2B COMPLETE")
        print(f"  Validation: {passed}/{len(results)}")
        print(f"  Consumption: {dep_map['consumption_pct']}%")
        print(f"  Status: {'PASS' if all_pass else 'FAIL'}")
        print(f"{'='*70}\n")

        return {
            "status": "PASS" if all_pass else "FAIL",
            "validation_score": f"{passed}/{len(results)}",
            "consumption_pct": dep_map["consumption_pct"],
            "steel_weight_kg": prod_result.get("steel_weight_kg", 0),
            "workbook_path": prod_result.get("workbook_path"),
            "export_paths": paths,
        }

    def _bootstrap_r2a(self) -> None:
        """Register PhaseR.2A as importable package (folder name contains dots)."""
        import types
        import importlib.util
        r2a_dir = self._src / "PhaseR.2A_engineering_context"
        if "PhaseR2A.engineering_context_parser" in sys.modules:
            return
        pkg = types.ModuleType("PhaseR2A")
        pkg.__path__ = [str(r2a_dir)]
        pkg.__package__ = "PhaseR2A"
        sys.modules["PhaseR2A"] = pkg

        for sub in [
            "__init__", "engineering_context_model",
            "engineering_context_cache", "engineering_context_loader",
            "general_notes_text_extractor", "development_length_parser",
            "cover_parser", "steel_grade_parser", "concrete_grade_parser",
            "hook_rule_parser", "lap_rule_parser", "general_notes_classifier",
            "engineering_context_builder", "engineering_context_validator",
            "engineering_context_factory", "engineering_context_parser",
        ]:
            spec = importlib.util.spec_from_file_location(
                f"PhaseR2A.{sub}", r2a_dir / f"{sub}.py"
            )
            mod = importlib.util.module_from_spec(spec)
            mod.__package__ = "PhaseR2A"
            sys.modules[f"PhaseR2A.{sub}"] = mod
            spec.loader.exec_module(mod)

    def _load_engineering_context(self):
        if str(self._src) not in sys.path:
            sys.path.insert(0, str(self._src))
        try:
            self._bootstrap_r2a()
            parser_mod = sys.modules["PhaseR2A.engineering_context_parser"]
            loader, passed, warnings = parser_mod.parse_engineering_context(self._v7)
            if loader is None:
                print(f"      WARN: {warnings}")
                return None
            return loader
        except Exception as exc:
            print(f"      ERROR loading context: {exc}")
            import traceback
            traceback.print_exc()
            return None

    def _run_production(self, loader) -> Dict[str, Any]:
        vb1_src = self._src / "PhaseVB.1_production_output_completion"
        if str(vb1_src) not in sys.path:
            sys.path.insert(0, str(vb1_src))
        try:
            from phase_vb1_orchestrator import PhaseVB1Orchestrator
            orch = PhaseVB1Orchestrator(
                v7_root=self._v7,
                loader=loader,
            )
            result = orch.run()
            return {
                "status": "PASS" if result.pipeline_exit_code == 0 else "FAIL",
                "steel_weight_kg": result.steel_weight_kg,
                "workbook_path": result.workbook_path,
                "beam_count": result.beam_count,
                "bbs_row_count": result.bbs_row_count,
            }
        except Exception as exc:
            return {"status": "FAIL", "error": str(exc), "steel_weight_kg": 0}
