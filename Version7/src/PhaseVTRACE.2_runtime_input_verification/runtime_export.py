"""
runtime_export.py — Exports all 12 V.TRACE.2 artefacts.
MODEL_VERSION: 7.1.3  |  READ-ONLY (writes only to the designated output folder)
"""

from __future__ import annotations
import json
import pathlib
from typing import Any, Dict

OUTPUT_DIR = pathlib.Path(
    r"C:\Users\nishanth.h\SteelBeamEstimator\Version7\data\output"
    r"\PhaseVTRACE.2_runtime_input_verification"
)


def _dump(name: str, data: Any) -> pathlib.Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


class RuntimeExporter:

    def export_all(
        self,
        files,
        load_events,
        beam_count_result,
        adapter_results,
        filter_analysis,
        version_report,
        cache_report,
        dependency_report,
        statistics,
        validation,
        report,
    ) -> Dict[str, str]:
        results = {}

        artefacts = {
            "runtime_file_inventory.json": {
                k: v.to_dict() for k, v in files.items()
            },
            "runtime_load_sequence.json": {
                "total_events": len(load_events),
                "events": load_events,
            },
            "runtime_beam_counts.json": beam_count_result,
            "runtime_adapter_validation.json": {
                "total": len(adapter_results),
                "passed": sum(1 for r in adapter_results if r.get("status") == "PASS"),
                "results": adapter_results,
            },
            "runtime_filter_analysis.json": filter_analysis,
            "runtime_dependency_report.json": dependency_report,
            "runtime_version_report.json": version_report,
            "runtime_cache_report.json": cache_report,
            "runtime_statistics.json": statistics,
            "runtime_validation_report.json": {
                "rules": validation,
                "passed": sum(1 for v in validation if v.get("status") == "PASS"),
                "failed": sum(1 for v in validation if v.get("status") == "FAIL"),
            },
            "runtime_root_cause.json": {
                "root_cause":     report.get("sections", {}).get("11_root_cause", ""),
                "recommendation": report.get("sections", {}).get("12_engineering_recommendation", ""),
            },
            "runtime_input_verification_report.json": report,
        }

        for filename, data in artefacts.items():
            path = _dump(filename, data)
            results[filename] = str(path)
            print(f"  [OK]  {filename}")

        return results
