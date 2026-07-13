"""
Pattern Export — writes all Phase L.3 output artefacts.

Files produced
--------------
engineering_patterns.json
engineering_pattern_registry.json
pattern_summary.json
beam_pattern_matrix.json
pattern_validation_report.json
pattern_statistics.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from pattern_models import EngineeringPattern
from pattern_registry import PatternRegistry


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class PatternExport:

    REQUIRED_FILES = [
        "engineering_patterns.json",
        "engineering_pattern_registry.json",
        "pattern_summary.json",
        "beam_pattern_matrix.json",
        "pattern_validation_report.json",
        "pattern_statistics.json",
    ]

    @staticmethod
    def export_all(
        output_dir: Path,
        patterns: List[EngineeringPattern],
        registry: PatternRegistry,
        pattern_summary: Dict[str, Any],
        beam_pattern_matrix: List[Dict[str, Any]],
        validation_report: Dict[str, Any],
        statistics: Dict[str, Any],
    ) -> None:
        _write(
            output_dir / "engineering_patterns.json",
            {
                "phase": "L.3",
                "model_version": "6.5.0",
                "total_patterns": len(patterns),
                "patterns": [p.to_dict() for p in patterns],
            },
        )
        _write(output_dir / "engineering_pattern_registry.json", registry.to_dict())
        _write(output_dir / "pattern_summary.json", pattern_summary)
        _write(
            output_dir / "beam_pattern_matrix.json",
            {
                "phase": "L.3",
                "model_version": "6.5.0",
                "total_beams": len(beam_pattern_matrix),
                "matrix": beam_pattern_matrix,
            },
        )
        _write(output_dir / "pattern_validation_report.json", validation_report)
        _write(output_dir / "pattern_statistics.json", statistics)

    @staticmethod
    def validate_exports(output_dir: Path) -> Dict[str, Any]:
        results = []
        for fname in PatternExport.REQUIRED_FILES:
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
        return {"status": "PASS" if all_ok else "FAIL", "files": results}

    @staticmethod
    def print_summary(result: Dict[str, Any]) -> None:
        sep = "=" * 80
        print(sep)
        print("Phase L.3 — Beam Reinforcement Pattern Recognition Engine")
        print(sep)
        summ = result.get("pattern_summary") or {}
        stats = result.get("statistics") or {}
        val = result.get("validation") or {}
        exp = result.get("export_validation") or {}
        print(f"  Model Version       : {summ.get('model_version', '6.5.0')}")
        print(f"  Total Beams         : {summ.get('total_beams_classified', '?')}")
        print(f"  Validation          : {val.get('status', '?')}")
        print()
        print("  Span Pattern Distribution:")
        for k, v in (stats.get("span_pattern_distribution") or {}).items():
            print(f"    {k:<40}: {v}")
        print()
        print("  Continuity Distribution:")
        for k, v in (stats.get("continuity_distribution") or {}).items():
            print(f"    {k:<40}: {v}")
        print()
        print("  Reinforcement Pattern Distribution:")
        for k, v in (stats.get("reinforcement_pattern_distribution") or {}).items():
            print(f"    {k:<40}: {v}")
        print()
        print("  Confidence Distribution:")
        for k, v in (stats.get("confidence_distribution") or {}).items():
            print(f"    {k:<40}: {v}")
        cstats = stats.get("confidence_stats") or {}
        print(f"  Confidence Mean     : {cstats.get('mean', '?')}")
        print()
        print(f"  Export Validation   : {exp.get('status', '?')}")
        for f in exp.get("files") or []:
            icon = "[OK]  " if f["status"] == "OK" else "[MISS]"
            print(f"    {icon} {f['file']}")
        print(sep)
