"""
coverage_validator.py — Production coverage validation for Phase R.1.1B.
MODEL_VERSION: 8.2.1

Reports per-beam and per-bar coverage across Steel, BBS, and Workbook.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List


class ProductionCoverageValidator:
    """Validates production coverage for every beam and bar."""

    def __init__(self, v7_root: pathlib.Path):
        self._v7 = v7_root

    def validate(
        self,
        r13_result: Dict[str, Any],
        production_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        r13_beams = r13_result.get("beams_with_bars", 0)
        total_bars = r13_result.get("total_bars", 0)
        beams_steel = production_result.get("beams_reaching_steel", 0)
        beams_bbs = production_result.get("beams_reaching_bbs", 0)
        beams_excel = production_result.get("beams_reaching_excel", 0)
        total_steel_kg = production_result.get("total_steel_kg", 0.0)

        excel_ok = (self._v7 / "data/output/Production_Output/Estimation_Output.xlsx").exists()
        if excel_ok and beams_excel == 0:
            beams_excel = beams_steel

        bar_coverage_pct = round(100.0 * beams_steel / r13_beams, 1) if r13_beams else 0.0

        per_beam = self._load_per_beam_detail(r13_result)

        return {
            "total_engineering_bars": total_bars,
            "beams_with_engineering_bars": r13_beams,
            "beams_reaching_steel": beams_steel,
            "beams_reaching_bbs": beams_bbs,
            "beams_reaching_excel": beams_excel,
            "total_steel_kg": round(total_steel_kg, 3),
            "coverage_pct": bar_coverage_pct,
            "per_beam_coverage": per_beam,
            "coverage_summary": {
                "engineering_bars_built": total_bars,
                "steel_coverage_pct": bar_coverage_pct,
                "bbs_coverage_pct": round(100.0 * beams_bbs / r13_beams, 1) if r13_beams else 0.0,
                "excel_coverage_pct": round(100.0 * beams_excel / r13_beams, 1) if r13_beams else 0.0,
            },
        }

    def _load_per_beam_detail(self, r13_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        prod_path = self._v7 / "data/output/PhaseR1.3_pipeline_integration/beam_reinforcement_models_production.json"
        if not prod_path.exists():
            return []

        per_beam = []
        try:
            data = json.loads(prod_path.read_text(encoding="utf-8"))
            beams = data.get("beams", data.get("models", []))
            if isinstance(beams, list):
                for m in beams:
                    beam_id = m.get("beam_id", "")
                    bar_count = m.get("bar_count", 0)
                    per_beam.append({
                        "beam_id": beam_id,
                        "engineering_bars": bar_count,
                        "has_steel": bar_count > 0,
                        "classification_complete": m.get("classification_complete", False),
                    })
            elif isinstance(beams, dict):
                for beam_id in sorted(beams.keys()):
                    m = beams[beam_id]
                    bar_count = m.get("bar_count", 0)
                    per_beam.append({
                        "beam_id": beam_id,
                        "engineering_bars": bar_count,
                        "has_steel": bar_count > 0,
                        "classification_complete": m.get("classification_complete", False),
                    })
            return []
        except Exception:
            return []
        return per_beam
