"""
benchmark3_validator.py — Deterministic validation rules for V.TEST.3.
MODEL_VERSION: 8.1.1
"""
from __future__ import annotations

from typing import Any, Dict


class Benchmark3Validator:

    RULES = {
        "RULE_1":  "Dynamic drawing discovery",
        "RULE_2":  "Dynamic beam discovery",
        "RULE_3":  "Dynamic General Notes parsing",
        "RULE_4":  "Engineering Context generated",
        "RULE_5":  "Engineering Facts generated",
        "RULE_6":  "Geometry Context generated",
        "RULE_7":  "Drawing Relationships generated",
        "RULE_8":  "EngineeringBarModels generated",
        "RULE_9":  "Production workbook generated",
        "RULE_10": "Pipeline completed successfully",
        "RULE_11": "No benchmark-specific assumptions",
        "RULE_12": "No hardcoded beam IDs",
    }

    def validate(
        self,
        discovery: Dict[str, Any],
        beams: Dict[str, Any],
        gn: Dict[str, Any],
        interp: Dict[str, Any],
        bars: Dict[str, Any],
        prod: Dict[str, Any],
        pipeline: Dict[str, Any],
        audit: Dict[str, Any],
    ) -> Dict[str, Any]:
        results: Dict[str, Dict[str, Any]] = {}

        results["RULE_1"] = self._r(
            discovery.get("dxf_count", 0) >= 3,
            f"{discovery.get('dxf_count', 0)} DXF files discovered dynamically",
        )
        results["RULE_2"] = self._r(
            beams.get("total_beams", 0) > 0,
            f"{beams.get('total_beams', 0)} beams in registry",
        )
        results["RULE_3"] = self._r(
            gn.get("dynamically_obtained", False),
            f"GN DXF: {gn.get('gn_dxf_path', 'not found')}",
        )
        results["RULE_4"] = self._r(
            gn.get("engineering_context_available", False),
            "Engineering Context from General Notes",
        )
        results["RULE_5"] = self._r(
            interp.get("engineering_facts", 0) > 0,
            f"{interp.get('engineering_facts', 0)} engineering facts",
        )
        results["RULE_6"] = self._r(
            interp.get("geometry_contexts", 0) > 0,
            f"{interp.get('geometry_contexts', 0)} geometry contexts",
        )
        results["RULE_7"] = self._r(
            interp.get("drawing_relationships", 0) > 0,
            f"{interp.get('drawing_relationships', 0)} drawing relationships",
        )
        results["RULE_8"] = self._r(
            bars.get("engineering_bar_models", 0) > 0,
            f"{bars.get('engineering_bar_models', 0)} engineering bar models",
        )
        results["RULE_9"] = self._r(
            prod.get("workbook_generated", False),
            "Estimation_Output.xlsx generated" if prod.get("workbook_generated") else "Workbook missing",
        )
        results["RULE_10"] = self._r(
            pipeline.get("pipeline_completed", False),
            f"{pipeline.get('stages_passed', 0)}/{pipeline.get('stages_executed', 0)} stages passed",
        )
        results["RULE_11"] = self._r(
            audit.get("all_checks_passed", False),
            audit.get("summary", ""),
        )
        results["RULE_12"] = self._r(
            audit.get("checks", {}).get("no_hardcoded_beam_ids", False),
            "No B1-B18 hardcoded fingerprint" if audit.get("checks", {}).get("no_hardcoded_beam_ids")
            else "Hardcoded beam ID pattern detected",
        )

        passed = sum(1 for r in results.values() if r["passed"])
        return {
            "rules": results,
            "passed": passed,
            "total": len(results),
            "all_pass": passed == len(results),
            "summary": f"{passed}/{len(results)} validation rules passed",
        }

    @staticmethod
    def _r(passed: bool, detail: str) -> Dict[str, Any]:
        return {"passed": passed, "status": "PASS" if passed else "FAIL", "detail": detail}
