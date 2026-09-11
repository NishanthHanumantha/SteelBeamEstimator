"""
Geometry Registry Engine — Phase L.2.2 (Version8 / D.5.3).
MODEL_VERSION: 8.9.2

Builds geometry_registry.json from the current run's VROOT1 artefacts.

Preserved engineering (from Version7 L.2.2 registry contract):
  - Local beam axis 0 → span, mid-depth y
  - Default LEFT@0 / RIGHT@1 supports
  - GeometryRegistry aggregation schema

Removed for R-spine web production:
  - L.2 / L.2.1 gap detection and L.2.1 retrigger
  - Version5 schedule / engineering_objects lookup
  - Placeholder bar injection
  - Benchmark_Set / shared-output assumptions
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .geometry_registry import GeometryRegistry, build_entry_from_vroot1, build_failed_entry


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _beams_dict(beam_registry: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    beams = beam_registry.get("beams") or {}
    if isinstance(beams, list):
        return {str(b.get("beam_id")): b for b in beams if b.get("beam_id")}
    if isinstance(beams, dict):
        return {str(k): v for k, v in beams.items()}
    return {}


def _geometry_hints(dynamic_geo: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not dynamic_geo or not isinstance(dynamic_geo, dict):
        return {}
    geos = dynamic_geo.get("geometries") or {}
    if isinstance(geos, dict):
        return {str(k): v for k, v in geos.items() if isinstance(v, dict)}
    return {}


class GeometryRegistryEngine:
    """Synthesize R.3-compatible geometry_registry from VROOT1 run outputs."""

    def run(
        self,
        beam_registry_path: Path,
        dynamic_geometry_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        beam_reg = _load_json(Path(beam_registry_path))
        if not beam_reg or not isinstance(beam_reg, dict):
            raise FileNotFoundError(
                f"VROOT1 beam_registry.json not found or invalid: {beam_registry_path}"
            )

        dyn = None
        if dynamic_geometry_path is not None:
            dyn = _load_json(Path(dynamic_geometry_path))
        hints = _geometry_hints(dyn)

        beams = _beams_dict(beam_reg)
        if not beams:
            raise ValueError(f"No beams in beam_registry: {beam_registry_path}")

        registry = GeometryRegistry()
        for beam_id, entry in sorted(beams.items(), key=lambda kv: (len(kv[0]), kv[0])):
            try:
                geo_entry = build_entry_from_vroot1(
                    beam_id=beam_id,
                    beam_entry=entry if isinstance(entry, dict) else {},
                    geometry_hint=hints.get(beam_id),
                )
            except Exception as exc:  # noqa: BLE001 — isolate per-beam failures
                geo_entry = build_failed_entry(beam_id, str(exc))
            registry.add(geo_entry)

        registry_dict = registry.to_dict()
        return {
            "geometry_registry": registry_dict,
            "beam_count": registry_dict["total"],
            "original_count": registry_dict["original_count"],
            "recovered_count": registry_dict["recovered_count"],
            "failed_count": registry_dict["failed_count"],
            "sources": {
                "beam_registry": str(beam_registry_path),
                "dynamic_beam_geometry": str(dynamic_geometry_path)
                if dynamic_geometry_path
                else None,
            },
        }
