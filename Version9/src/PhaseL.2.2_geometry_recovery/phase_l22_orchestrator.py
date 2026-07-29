"""
phase_l22_orchestrator.py — Master orchestrator for Phase L.2.2.
MODEL_VERSION: 8.9.2

Execution sequence:
  1. Load VROOT1 beam_registry.json (+ optional dynamic_beam_geometry.json)
  2. Build R.3-compatible geometry_registry entries
  3. Export geometry_registry.json under the current run output folder

I/O is run-scoped via RunContext (Phase D.5.3). Registry schema/axis/support
construction preserved from the Version7 L.2.2 contract.
"""
from __future__ import annotations

import pathlib
from datetime import datetime
from typing import Any, Dict, Optional

from .geometry_registry_engine import GeometryRegistryEngine
from .recovery_export import GeometryRegistryExport

MODEL_VERSION = "8.9.2"
PHASE_ID = "L.2.2"
_OUT_NAME = "PhaseL.2.2_geometry_recovery"
_VROOT1 = "PhaseVROOT.1_dynamic_pipeline_initialization"


class PhaseL22Orchestrator:
    """Master orchestrator for Phase L.2.2 — Geometry Registry Generation."""

    def __init__(
        self,
        beam_registry_path: Optional[pathlib.Path] = None,
        dynamic_geometry_path: Optional[pathlib.Path] = None,
        output_dir: Optional[pathlib.Path] = None,
        output_root: Optional[pathlib.Path] = None,
        engine_root: Optional[pathlib.Path] = None,
    ):
        self._output_root = (
            pathlib.Path(output_root)
            if output_root
            else (
                pathlib.Path(engine_root) / "data" / "output"
                if engine_root
                else None
            )
        )

        if beam_registry_path is not None:
            self.beam_registry_path = pathlib.Path(beam_registry_path)
        elif self._output_root is not None:
            self.beam_registry_path = (
                self._output_root / _VROOT1 / "beam_registry.json"
            )
        else:
            raise ValueError("beam_registry_path or output_root/engine_root required")

        if dynamic_geometry_path is not None:
            self.dynamic_geometry_path = pathlib.Path(dynamic_geometry_path)
        elif self._output_root is not None:
            self.dynamic_geometry_path = (
                self._output_root / _VROOT1 / "dynamic_beam_geometry.json"
            )
        else:
            self.dynamic_geometry_path = None

        if output_dir is not None:
            self.output_dir = pathlib.Path(output_dir)
        elif self._output_root is not None:
            self.output_dir = self._output_root / _OUT_NAME
        else:
            raise ValueError("output_dir or output_root/engine_root required")

        self._engine = GeometryRegistryEngine()
        self._exporter = GeometryRegistryExport()

    def run(self) -> Dict[str, Any]:
        start = datetime.now()
        print(f"[L.2.2] Geometry Registry Generation — MODEL_VERSION {MODEL_VERSION}")
        print(f"[L.2.2] Phase: {PHASE_ID}")
        print(f"[L.2.2] beam_registry: {self.beam_registry_path}")
        print(f"[L.2.2] dynamic_geometry: {self.dynamic_geometry_path}")
        print(f"[L.2.2] Output: {self.output_dir}")
        print()

        dyn = self.dynamic_geometry_path
        if dyn is not None and not dyn.exists():
            print(f"[L.2.2] Optional dynamic_beam_geometry missing — continuing without it")
            dyn = None

        result = self._engine.run(
            beam_registry_path=self.beam_registry_path,
            dynamic_geometry_path=dyn,
        )
        registry = result["geometry_registry"]
        print(
            f"[L.2.2] Built registry: total={result['beam_count']} "
            f"original={result['original_count']} "
            f"recovered={result['recovered_count']} "
            f"failed={result['failed_count']}"
        )

        elapsed = (datetime.now() - start).total_seconds()
        exported = self._exporter.export_all(
            output_dir=self.output_dir,
            geometry_registry_dict=registry,
            run_meta={
                "model_version": MODEL_VERSION,
                "sources": result.get("sources"),
                "elapsed_seconds": round(elapsed, 2),
            },
        )
        validation = self._exporter.validate_exports(self.output_dir)
        print(f"[L.2.2] Export validation: {validation.get('status')}")
        for f in validation.get("files") or []:
            icon = "OK" if f["status"] == "OK" else "MISS"
            print(f"  [{icon}] {f['file']} ({f['size_bytes']} bytes)")

        success = validation.get("status") == "PASS" and result["failed_count"] == 0
        out = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "beam_count": result["beam_count"],
            "original_count": result["original_count"],
            "recovered_count": result["recovered_count"],
            "failed_count": result["failed_count"],
            "exported_artefacts": {k: str(v) for k, v in exported.items()},
            "export_validation": validation,
            "elapsed_seconds": round(elapsed, 2),
            "success": success,
            "geometry_registry_path": str(
                self.output_dir / "geometry_registry.json"
            ),
        }
        print()
        print(f"[L.2.2] Completed in {elapsed:.2f}s — success={success}")
        return out
