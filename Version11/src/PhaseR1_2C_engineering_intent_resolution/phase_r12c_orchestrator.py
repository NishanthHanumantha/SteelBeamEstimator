"""
Phase R.1.2C Orchestrator — Engineering Intent Resolution Engine
MODEL_VERSION: 8.3.2
"""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
import time
import types
from collections import Counter
from typing import Any, Dict, List, Optional

MODEL_VERSION = "8.3.2"


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


class PhaseR12COrchestrator:

    def __init__(self, v7_root: Optional[pathlib.Path] = None):
        self.v7 = v7_root or pathlib.Path(__file__).resolve().parents[2]
        self._src = pathlib.Path(__file__).parent

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print("Phase R.1.2C - Engineering Intent Resolution Engine")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print("=" * 72)
        t0 = time.perf_counter()

        _load_pkg("PhaseR12C", self._src, [
            "engineering_intent_model",
            "engineering_role_resolver",
            "engineering_diameter_resolver",
            "engineering_extent_resolver",
            "engineering_consistency_engine",
            "engineering_intent_resolution_engine",
            "intent_validators",
            "intent_report_exporter",
        ])
        Engine = sys.modules[
            "PhaseR12C.engineering_intent_resolution_engine"
        ].EngineeringIntentResolutionEngine
        validators = sys.modules["PhaseR12C.intent_validators"]
        Exporter = sys.modules["PhaseR12C.intent_report_exporter"].IntentReportExporter

        # Baseline role counts from annotations (R.1 hypothesis)
        print("\n[1/7] Resolving Engineering Intents ...")
        engine = Engine(self.v7)
        before_roles = Counter()
        for anns in engine._annotations.values():
            for a in anns:
                if a.get("is_reinforcement", True):
                    before_roles[str(a.get("role") or "UNKNOWN")] += 1

        intents, payload = engine.resolve_all()
        after_roles = Counter(i.role for i in intents)
        print(
            f"      Intents={len(intents)} "
            f"role_changes={payload.get('role_changes')} "
            f"conf_mean={(payload.get('confidence') or {}).get('mean')}"
        )

        # Rebuild production with intent-wired builder + consolidation
        print("\n[2/7] Rebuilding R.1.3 + V.B.1 with intent layer ...")
        _run([sys.executable, "Run_PY/run_phase_r13_pipeline_integration.py"], self.v7)
        vb1 = self.v7 / "Run_PY/run_phase_vb1_production_output_completion.py"
        if vb1.exists():
            _run([sys.executable, str(vb1.relative_to(self.v7))], self.v7)

        # Mapping: each production bar (pre or post) to intent
        print("\n[3/7] Building EngineeringBar <-> Intent mapping ...")
        mapping = self._build_mapping(intents)

        print("\n[4/7] BBS / estimator / regression validation ...")
        bbs_validation = validators.BBSIntentValidator().validate(
            self.v7, dict(before_roles), dict(after_roles)
        )
        estimator_comparison = validators.EstimatorComparisonMetrics().compare(self.v7)
        regression = validators.RegressionIntentValidator().validate(
            self.v7, len(intents), len(mapping)
        )
        validation = validators.IntentRulesValidator().validate(
            intents,
            mapping,
            payload.get("consistency") or {},
            bbs_validation,
            regression,
            payload.get("role_resolution") or {},
        )
        print(f"      Rules {validation['passed']}/{validation['total']} passed")

        recommendation = (
            "A"
            if validation.get("passed", 0) >= 7 and regression.get("no_regression")
            else "B"
        )

        result: Dict[str, Any] = {
            "model_version": MODEL_VERSION,
            "phase": "R.1.2C",
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "recommendation": recommendation,
            "intents": [i.to_dict() for i in intents],
            "role_resolution": payload.get("role_resolution"),
            "diameter_resolution": payload.get("diameter_resolution"),
            "extent_resolution": payload.get("extent_resolution"),
            "confidence": payload.get("confidence"),
            "consistency": payload.get("consistency"),
            "mapping": mapping,
            "bbs_validation": bbs_validation,
            "estimator_comparison": estimator_comparison,
            "regression": regression,
            "validation": validation,
            "before_roles": dict(before_roles),
            "after_roles": dict(after_roles),
        }

        print("\n[5/7] Exporting artefacts ...")
        exporter = Exporter(self.v7)
        report_md = exporter.generate_report(result)
        exports = exporter.export_all(result, report_md)

        print("\n[6/7] Summary")
        print(f"      Role changes: {payload.get('role_changes')}")
        print(f"      Steel kg: {bbs_validation.get('steel_weight_kg')}")
        print(f"      Recommendation: {recommendation}")

        print("\n[7/7] Done")
        print("=" * 72)

        result["status"] = "PASS" if validation.get("overall_passed") else "WARN"
        result["export_paths"] = exports
        return result

    def _build_mapping(self, intents) -> List[Dict[str, Any]]:
        """Map intents to EngineeringBars (1:1 at intent emission; consolidation may merge)."""
        mapping = []
        for it in intents:
            mapping.append({
                "intent_id": it.intent_id,
                "intent_ids": [it.intent_id],
                "beam_id": it.beam_id,
                "bar_role": it.role,
                "diameter_mm": it.diameter_mm,
                "quantity": it.quantity,
                "extent": it.extent,
                "bar_label": it.bar_label,
                "annotation_ids": list(it.annotation_ids),
                "intent_confidence": it.intent_confidence,
            })
        # Also read consolidated production bars for lineage check
        eng_path = (
            self.v7
            / "data/output/PhaseR1.3_pipeline_integration"
            / "engineering_bar_models.json"
        )
        if eng_path.exists():
            import json
            data = json.loads(eng_path.read_text(encoding="utf-8"))
            for bm in data.get("beams") or []:
                for bar in bm.get("bars") or []:
                    meta = bar.get("engineering_metadata") or {}
                    iid = meta.get("intent_id")
                    if iid:
                        mapping.append({
                            "intent_id": iid,
                            "intent_ids": meta.get("merged_intent_ids") or [iid],
                            "beam_id": bm.get("beam_id"),
                            "bar_role": bar.get("bar_role"),
                            "diameter_mm": bar.get("diameter_mm"),
                            "quantity": bar.get("quantity"),
                            "extent": meta.get("extent"),
                            "bar_label": bar.get("bar_label"),
                            "source": "production_engineering_bar",
                            "physical_member_id": meta.get("physical_member_id"),
                        })
        return mapping
