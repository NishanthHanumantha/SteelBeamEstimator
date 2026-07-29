"""
Phase R.1.6.1 orchestrator.
MODEL_VERSION: 8.8.1
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from engineeringbar_builder import EngineeringBarBuilder
from general_notes_adapter import GeneralNotesAdapter
from input_loader import InputLoader
from json_exporter import JsonExporter
from report_generator import ReportGenerator
from stirrup_computation_engine import StirrupComputationEngine
from stirrup_model import StirrupComputation
from validation_engine import ValidationEngine

MODEL_VERSION = "8.8.1"
PHASE_ID = "R.1.6.1"


class PhaseR161Orchestrator:
    def __init__(self, v8_root: Optional[Path] = None):
        self.v8 = Path(v8_root) if v8_root else Path(__file__).resolve().parents[2]
        self.out = self.v8 / "data" / "output" / "PhaseR1_6_1_estimator_stirrup_computation"
        self.package_dir = Path(__file__).resolve().parent

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print("Phase R.1.6.1 — Estimator Stirrup Computation Engine")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print("Deterministic estimator methodology — no AI / no heuristics")
        print("=" * 72)
        t0 = time.perf_counter()

        print("\n[1/6] Loading General Notes + inputs ...")
        gn = GeneralNotesAdapter(self.v8)
        gn_summary = gn.summary()
        print(f"      GN available={gn.available} cover={gn_summary.get('clear_cover_mm')} mm")
        data = InputLoader(self.v8).load()
        print(f"      Stirrup jobs={len(data['jobs'])} (from intents+geometry)")

        print("\n[2/6] Computing stirrups ...")
        engine = StirrupComputationEngine(gn)
        computations: List[StirrupComputation] = []
        errors: List[Dict[str, str]] = []
        for job in data["jobs"]:
            try:
                computations.append(engine.compute(
                    beam_id=job["beam_id"],
                    label=job["label"],
                    beam_length_mm=job["beam_length_mm"],
                    beam_width_mm=job["beam_width_mm"],
                    beam_depth_mm=job["beam_depth_mm"],
                    source_intent_id=job.get("intent_id") or "",
                    source_detail_id=job.get("detail_id") or "",
                ))
            except Exception as exc:
                errors.append({"beam_id": job["beam_id"], "label": job["label"], "error": str(exc)})
        print(f"      Computed={len(computations)} errors={len(errors)}")

        print("\n[3/6] Building EngineeringBars ...")
        bars = EngineeringBarBuilder().build(computations)
        print(f"      Bars={len(bars)}")

        print("\n[4/6] Validation + regression ...")
        validation = ValidationEngine(gn).run_all(self.package_dir)
        # production coverage soft check
        validation["rules"].append({
            "id": "production_stirrups_computed",
            "passed": len(computations) > 0,
        })
        validation["rules"].append({
            "id": "rule_library_stirrup_family_present",
            "passed": bool(data["rule_library_ref"].get("has_stirrup_rule")),
        })
        validation["passed"] = sum(1 for r in validation["rules"] if r["passed"])
        validation["total"] = len(validation["rules"])
        validation["overall_passed"] = validation["passed"] == validation["total"]
        recommendation = "A" if validation["overall_passed"] else "B"
        print(f"      Validation {validation['passed']}/{validation['total']} -> {recommendation}")

        payload: Dict[str, Any] = {
            "model_version": MODEL_VERSION,
            "phase": PHASE_ID,
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "recommendation": recommendation,
            "computations": computations,
            "bars": bars,
            "validation": validation,
            "gn_summary": gn_summary,
            "errors": errors,
            "sources": data["sources"],
            "rule_library_ref": data["rule_library_ref"],
        }

        print("\n[5/6] Exporting artefacts ...")
        paths = JsonExporter(self.out).export_all(payload)
        md = ReportGenerator().markdown(payload)
        md_path = self.out / "phase_r161_summary.md"
        md_path.write_text(md, encoding="utf-8")
        paths["phase_r161_summary.md"] = str(md_path)

        print("\n[6/6] Done")
        print("=" * 72)
        status = "PASS" if validation["overall_passed"] else "WARN"
        print(f"STATUS: {status} | Recommendation: {recommendation}")
        print(f"Output: {self.out}")
        print("=" * 72)

        payload["export_paths"] = paths
        payload["status"] = status
        return payload
