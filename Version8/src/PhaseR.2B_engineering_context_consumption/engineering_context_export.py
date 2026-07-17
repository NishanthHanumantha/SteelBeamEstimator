"""Export JSON artefacts for Phase R.2B."""
from __future__ import annotations
import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List


def _save(out: pathlib.Path, name: str, data: Any) -> pathlib.Path:
    p = out / name
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


class EngineeringContextExport:

    def __init__(self, output_dir: pathlib.Path):
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def write_all(
        self,
        dependency_map: Dict[str, Any],
        hardcoded_audit: Dict[str, Any],
        usage_results: List,
        statistics: Dict[str, Any],
        loader_summary: Dict[str, Any],
        production_result: Dict[str, Any],
    ) -> Dict[str, str]:
        ts = datetime.utcnow().isoformat()
        paths: Dict[str, str] = {}
        passed = sum(1 for r in usage_results if r.passed)
        total = len(usage_results)

        p = _save(self._out, "engineering_context_consumption_report.json", {
            "generated": ts, "phase": "R.2B", "model_version": "7.6.0",
            "status": "PASS" if passed == total else "FAIL",
            "validation_score": f"{passed}/{total}",
            "consumption_rate": dependency_map.get("consumption_rate"),
            "production": production_result,
        })
        paths["engineering_context_consumption_report"] = str(p)

        p = _save(self._out, "engineering_dependency_graph.json", {
            "generated": ts, "phase": "R.2B", "model_version": "7.6.0",
            "nodes": dependency_map.get("nodes", []),
            "edges": [
                {"from": "EngineeringContextLoader", "to": n["module"]}
                for n in dependency_map.get("nodes", [])
                if n.get("consumes_engineering_context")
            ],
        })
        paths["engineering_dependency_graph"] = str(p)

        p = _save(self._out, "engineering_context_usage.json", {
            "generated": ts, "loader_summary": loader_summary,
            "modules_consuming_context": [
                n["module"] for n in dependency_map.get("nodes", [])
                if n.get("consumes_engineering_context")
            ],
        })
        paths["engineering_context_usage"] = str(p)

        p = _save(self._out, "engineering_context_statistics.json", {
            "generated": ts, **statistics,
        })
        paths["engineering_context_statistics"] = str(p)

        p = _save(self._out, "parameter_consumption_matrix.json", {
            "generated": ts,
            "matrix": dependency_map.get("consumption_matrix", []),
            "consumption_rate": dependency_map.get("consumption_rate"),
        })
        paths["parameter_consumption_matrix"] = str(p)

        p = _save(self._out, "hardcoded_constant_audit.json", {
            "generated": ts, **hardcoded_audit,
        })
        paths["hardcoded_constant_audit"] = str(p)

        p = _save(self._out, "engineering_context_validation.json", {
            "generated": ts, "phase": "R.2B", "model_version": "7.6.0",
            "validation_score": f"{passed}/{total}",
            "all_pass": passed == total,
            "rules": [r.to_dict() for r in usage_results],
        })
        paths["engineering_context_validation"] = str(p)

        p = _save(self._out, "engineering_context_summary.json", {
            "generated": ts, "phase": "R.2B", "model_version": "7.6.0",
            "status": "PASS" if passed == total else "FAIL",
            "validation_score": f"{passed}/{total}",
            "consumption_pct": dependency_map.get("consumption_pct"),
            "steel_weight_kg": production_result.get("steel_weight_kg"),
            "workbook_path": production_result.get("workbook_path"),
            "primary_steel_grade": loader_summary.get("primary_steel_grade"),
            "cover_beam_mm": loader_summary.get("cover_beam_mm"),
            "dev_length_factor": loader_summary.get("dev_length_factor"),
        })
        paths["engineering_context_summary"] = str(p)

        return paths
