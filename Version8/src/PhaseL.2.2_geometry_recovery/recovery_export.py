"""
Recovery Export — writes Phase L.2.2 artefacts.
MODEL_VERSION: 8.9.2

Primary production artefact:
  geometry_registry.json

Also writes a compact summary report for diagnostics.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class GeometryRegistryExport:
    REQUIRED_FILES = [
        "geometry_registry.json",
        "geometry_registry_report.json",
    ]

    @staticmethod
    def export_all(
        output_dir: Path,
        geometry_registry_dict: Dict[str, Any],
        run_meta: Dict[str, Any],
    ) -> Dict[str, Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        paths: Dict[str, Path] = {}
        p_reg = output_dir / "geometry_registry.json"
        _write(p_reg, geometry_registry_dict)
        paths["geometry_registry"] = p_reg

        report = {
            "phase_id": "L.2.2",
            "model_version": run_meta.get("model_version"),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "summary": {
                "total": geometry_registry_dict.get("total"),
                "original_count": geometry_registry_dict.get("original_count"),
                "recovered_count": geometry_registry_dict.get("recovered_count"),
                "failed_count": geometry_registry_dict.get("failed_count"),
                "beam_ids": geometry_registry_dict.get("beam_ids"),
            },
            "sources": run_meta.get("sources"),
            "elapsed_seconds": run_meta.get("elapsed_seconds"),
        }
        p_rep = output_dir / "geometry_registry_report.json"
        _write(p_rep, report)
        paths["geometry_registry_report"] = p_rep
        return paths

    @staticmethod
    def validate_exports(output_dir: Path) -> Dict[str, Any]:
        results = []
        for fname in GeometryRegistryExport.REQUIRED_FILES:
            path = Path(output_dir) / fname
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
