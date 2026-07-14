"""
Recovery Export — writes all Phase L.2.2 output artefacts.

Files produced
--------------
geometry_registry.json
geometry_recovery_report.json
beam_coverage_matrix.json
pipeline_validation_report.json
extended_beam_reinforcement_models.json   (written by engine; validated here)
geometry_traceability_map.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class RecoveryExport:
    """Handles deterministic export of all L.2.2 artefacts."""

    REQUIRED_FILES = [
        "geometry_registry.json",
        "geometry_recovery_report.json",
        "beam_coverage_matrix.json",
        "pipeline_validation_report.json",
        "geometry_traceability_map.json",
        "extended_beam_reinforcement_models.json",
    ]

    @staticmethod
    def export_all(
        output_dir: Path,
        geometry_registry_dict: Dict[str, Any],
        recovery_report: Dict[str, Any],
        coverage_matrix_report: Dict[str, Any],
        pipeline_validation_report: Dict[str, Any],
        traceability_map: Dict[str, Any],
    ) -> None:
        _write(output_dir / "geometry_registry.json", geometry_registry_dict)
        _write(output_dir / "geometry_recovery_report.json", recovery_report)
        _write(output_dir / "beam_coverage_matrix.json", coverage_matrix_report)
        _write(output_dir / "pipeline_validation_report.json", pipeline_validation_report)
        _write(output_dir / "geometry_traceability_map.json", traceability_map)

    @staticmethod
    def validate_exports(output_dir: Path) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        for fname in RecoveryExport.REQUIRED_FILES:
            path = output_dir / fname
            exists = path.exists()
            size = path.stat().st_size if exists else 0
            results.append(
                {
                    "file": fname,
                    "exists": exists,
                    "size_bytes": size,
                    "status": "OK" if (exists and size > 10) else "MISSING",
                }
            )
        all_ok = all(r["status"] == "OK" for r in results)
        return {
            "status": "PASS" if all_ok else "FAIL",
            "files": results,
        }

    @staticmethod
    def print_summary(result: Dict[str, Any]) -> None:
        sep = "-" * 70
        print(sep)
        print("Phase L.2.2 — Engineering Geometry Recovery")
        print(sep)
        rec = result.get("geometry_recovery_report", {}).get("summary", {})
        cov = result.get("beam_coverage_matrix", {}).get("summary", {})
        val = result.get("pipeline_validation", {})
        print(f"  Detected Beams      : {rec.get('total_detected_beams', '?')}")
        print(f"  Gap Beams Found     : {rec.get('gap_beams_identified', '?')}")
        print(f"  Recovered           : {rec.get('recovered_count', '?')}")
        print(f"  Failed Recovery     : {rec.get('failed_count', '?')}")
        print(f"  Coverage            : {cov.get('coverage_percent', '?')}%")
        print(f"  Pipeline Status     : {val.get('pipeline_status', '?')}")
        exp = result.get("export_validation", {})
        print(f"  Export Validation   : {exp.get('status', '?')}")
        print(sep)
