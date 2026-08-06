"""
Validation + regression for estimator stirrup computation.
MODEL_VERSION: 8.8.1
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from cut_length_engine import CutLengthEngine
from general_notes_adapter import GeneralNotesAdapter
from hook_engine import HookEngine
from perimeter_engine import PerimeterEngine
from quantity_engine import QuantityEngine
from stirrup_computation_engine import StirrupComputationEngine
from stirrup_notation_parser import StirrupNotationParser
from weight_engine import WeightEngine
from zone_builder import ZoneBuilder

MODEL_VERSION = "8.8.1"


class ValidationEngine:
    def __init__(self, gn: GeneralNotesAdapter):
        self._gn = gn
        self._engine = StirrupComputationEngine(gn)
        self._parser = StirrupNotationParser()
        self._qty = QuantityEngine()
        self._perim = PerimeterEngine()

    def run_all(self, package_dir: Path) -> Dict[str, Any]:
        cases = self._regression_cases()
        results = []
        for case in cases:
            results.append(self._run_case(case))

        formula_checks = [
            ("uniform_6m_100", self._qty.uniform_quantity(6000, 100) == 61),
            ("var_zone_2m_100", self._qty.zone_quantity(2000, 100) == 21),
            ("var_zone_2m_200", self._qty.zone_quantity(2000, 200) == 11),
            ("perimeter_400x750_c30", abs(self._perim.compute(400, 750, 30) - 2 * ((400 - 60) + (750 - 60))) < 1e-9),
            ("parse_uniform", self._parser.parse("2L-Y8@100C/C") is not None),
            ("parse_variable_3", len(self._parser.parse("2L-Y8@100/200/100").spacing_values_mm) == 3),
            ("parse_variable_4", len(self._parser.parse("2L-Y10@100/150/200/150").spacing_values_mm) == 4),
            ("parse_variable_2", len(self._parser.parse("2L-Y8@100/150").spacing_values_mm) == 2),
            ("gn_cover_available", self._gn.available and self._gn.clear_cover_mm() > 0),
            ("gn_hook_available", bool(self._gn.hook_rules())),
            ("no_excel_import", self._no_excel(package_dir)),
        ]

        case_pass = all(r["passed"] for r in results)
        formula_pass = all(ok for _, ok in formula_checks)
        rules = [
            ("regression_cases", case_pass),
            ("formula_checks", formula_pass),
            ("equal_zone_rule", all(r.get("equal_zones", True) for r in results)),
            ("general_notes_integration", self._gn.available),
        ]
        passed = sum(1 for _, ok in rules if ok)
        return {
            "model_version": MODEL_VERSION,
            "passed": passed,
            "total": len(rules),
            "overall_passed": passed == len(rules),
            "rules": [{"id": i, "passed": ok} for i, ok in rules],
            "formula_checks": [{"id": i, "passed": ok} for i, ok in formula_checks],
            "regression_cases": results,
        }

    def _run_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        try:
            comp = self._engine.compute(
                beam_id=case["beam_id"],
                label=case["label"],
                beam_length_mm=case["length_mm"],
                beam_width_mm=case["width_mm"],
                beam_depth_mm=case["depth_mm"],
                cover_mm=case.get("cover_mm"),
            )
            equal = all(
                abs(z.length_mm - case["length_mm"] / len(comp.zones)) < 1e-6
                for z in comp.zones
            )
            qty_ok = comp.total_quantity == case["expected_qty"]
            zones_ok = len(comp.zones) == case["expected_zones"]
            perim_ok = abs(comp.perimeter_mm - case["expected_perimeter"]) < 0.01
            cut_ok = abs(comp.cut_length_mm - case["expected_cut"]) < 0.01
            weight_ok = abs(comp.weight_kg - case["expected_weight"]) < 0.05
            passed = equal and qty_ok and zones_ok and perim_ok and cut_ok and weight_ok
            return {
                "case_id": case["case_id"],
                "passed": passed,
                "equal_zones": equal,
                "quantity": comp.total_quantity,
                "expected_qty": case["expected_qty"],
                "zones": len(comp.zones),
                "perimeter_mm": comp.perimeter_mm,
                "cut_length_mm": comp.cut_length_mm,
                "weight_kg": comp.weight_kg,
                "hook": comp.hook.to_dict(),
            }
        except Exception as exc:
            return {"case_id": case["case_id"], "passed": False, "error": str(exc), "equal_zones": False}

    def _regression_cases(self) -> List[Dict[str, Any]]:
        # Cover/hook from GN for production-like cases; explicit cover for pure formula cases
        cover = 30.0
        # dia 8 → hook 5d = 40 if GN says 5xd @135
        try:
            hook_mult = int(self._gn.primary_hook_rule(135).get("multiplier_xd") or 5)
        except Exception:
            hook_mult = 5
        dia = 8.0
        hook = hook_mult * dia
        # B=300,D=450,C=30 → clear 240+390=630 → perim 1260; cut=1260+80=1340 for 8mm/5d
        # Use width 300 depth 450 for examples matching mental math, and also 400x750

        def cut(w, d, c, dia_mm):
            perim = 2 * ((w - 2 * c) + (d - 2 * c))
            return perim, perim + 2 * (hook_mult * dia_mm)

        p1, c1 = cut(300, 450, cover, 8)
        # 6m @100 → 61; weight = 1.340 * 61 * 0.395
        w1 = round((c1 / 1000.0) * 61 * 0.395, 4)

        p2, c2 = cut(300, 450, cover, 8)
        # 6m 100/200/100 → 21+11+21=53
        w2 = round((c2 / 1000.0) * 53 * 0.395, 4)

        p3, c3 = cut(400, 750, cover, 10)
        # 8m @150 → 8000/150+1 = 53+1=54? 8000//150=53 +1=54
        # hook for 10mm
        p3, c3 = cut(400, 750, cover, 10)
        w3 = round((c3 / 1000.0) * 54 * 0.617, 4)

        p4, c4 = cut(250, 500, cover, 8)
        # 5m 100/150 → 2 zones of 2500: 2500/100+1=26, 2500/150+1=17 → 43
        w4 = round((c4 / 1000.0) * 43 * 0.395, 4)

        p5, c5 = cut(350, 600, cover, 8)
        # 7.2m 100/150/200/150 → 4 zones of 1800
        # 1800/100+1=19, 1800/150+1=13, 1800/200+1=10, 1800/150+1=13 → 55
        w5 = round((c5 / 1000.0) * 55 * 0.395, 4)

        return [
            {
                "case_id": "uniform_6m_100",
                "beam_id": "T1",
                "label": "2L-Y8@100C/C",
                "length_mm": 6000,
                "width_mm": 300,
                "depth_mm": 450,
                "cover_mm": cover,
                "expected_zones": 1,
                "expected_qty": 61,
                "expected_perimeter": p1,
                "expected_cut": c1,
                "expected_weight": w1,
            },
            {
                "case_id": "variable_3zone_100_200_100",
                "beam_id": "T2",
                "label": "2L-Y8@100/200/100",
                "length_mm": 6000,
                "width_mm": 300,
                "depth_mm": 450,
                "cover_mm": cover,
                "expected_zones": 3,
                "expected_qty": 53,
                "expected_perimeter": p2,
                "expected_cut": c2,
                "expected_weight": w2,
            },
            {
                "case_id": "uniform_8m_150_dia10",
                "beam_id": "T3",
                "label": "2L-Y10@150C/C",
                "length_mm": 8000,
                "width_mm": 400,
                "depth_mm": 750,
                "cover_mm": cover,
                "expected_zones": 1,
                "expected_qty": 54,
                "expected_perimeter": p3,
                "expected_cut": c3,
                "expected_weight": w3,
            },
            {
                "case_id": "variable_2zone_100_150",
                "beam_id": "T4",
                "label": "2L-Y8@100/150C/C",
                "length_mm": 5000,
                "width_mm": 250,
                "depth_mm": 500,
                "cover_mm": cover,
                "expected_zones": 2,
                "expected_qty": 43,
                "expected_perimeter": p4,
                "expected_cut": c4,
                "expected_weight": w4,
            },
            {
                "case_id": "variable_4zone_100_150_200_150",
                "beam_id": "T5",
                "label": "2L-Y8@100/150/200/150",
                "length_mm": 7200,
                "width_mm": 350,
                "depth_mm": 600,
                "cover_mm": cover,
                "expected_zones": 4,
                "expected_qty": 55,
                "expected_perimeter": p5,
                "expected_cut": c5,
                "expected_weight": w5,
            },
        ]

    @staticmethod
    def _no_excel(package_dir: Path) -> bool:
        for path in package_dir.glob("*.py"):
            if path.name == "validation_engine.py":
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "load_workbook" in text:
                return False
        return True
