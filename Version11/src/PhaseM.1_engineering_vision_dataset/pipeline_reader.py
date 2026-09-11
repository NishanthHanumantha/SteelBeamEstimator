"""
pipeline_reader.py — Read deterministic pipeline outputs for Phase M.1.

Reads all available artefacts from prior pipeline stages.
Graceful fallback when phases have not yet run.

MODEL_VERSION: 9.0.0
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "9.0.0"

_NAT_RE = re.compile(r"(\d+)|(\D+)")


def _natural_key(beam_id: str) -> Tuple:
    parts: List[Any] = []
    for num, text in _NAT_RE.findall(str(beam_id)):
        parts.append(int(num) if num else text.upper())
    return tuple(parts)


def _read(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


class PipelineReader:
    """
    Read all available pipeline artefacts for M.1 dataset generation.

    output_root  — path to the pipeline's data/output/ directory.
                   Accepts either:
                     • <engine_root>/data/output/
                     • <run_root>/data/output/
    """

    VROOT1_DIR = "PhaseVROOT.1_dynamic_pipeline_initialization"
    R1_DIR     = "PhaseR.1_generalized_reinforcement_discovery"
    R3_DIR     = "PhaseR3_geometry_context_engine"
    R13_DIR    = "PhaseR1.3_pipeline_integration"

    def __init__(self, output_root: Path) -> None:
        self.out = Path(output_root)

    # ── public API ────────────────────────────────────────────────────────────

    def load(self) -> Dict[str, Any]:
        """
        Return a unified data dict consumed by the M.1 orchestrator.

        Keys
        ----
        beam_ids       : List[str]  — ordered beam IDs
        beams          : Dict[str, Any]  — beam_registry entries keyed by beam_id
        annotations    : Dict[str, List[Dict]]  — R1 annotations, by_beam
        axes           : Dict[str, Any]  — BeamAxis entries keyed by beam_id
        geo_contexts   : Dict[str, List[Dict]]  — GeometryContexts by_beam
        prod_bars      : Dict[str, Any]  — production bar model per beam_id
        drawings       : Dict[str, str]  — drawing name → DXF file path
        available      : Dict[str, bool]  — which phases produced output
        """
        vroot = self.out / self.VROOT1_DIR
        r1    = self.out / self.R1_DIR
        r3    = self.out / self.R3_DIR
        r13   = self.out / self.R13_DIR

        registry_raw = _read(vroot / "beam_registry.json")         or {}
        ann_raw      = _read(r1   / "reinforcement_annotations.json") or {}
        axis_raw     = _read(r3   / "BeamAxis.json")               or {}
        geo_ctx_raw  = _read(r3   / "GeometryContexts.json")       or {}
        prod_raw     = _read(r13  / "beam_reinforcement_models_production.json") or {}

        available = {
            "VROOT1": bool(registry_raw),
            "R1":     bool(ann_raw),
            "R3":     bool(axis_raw),
            "R1.3":   bool(prod_raw),
        }

        beam_ids = self._extract_beam_ids(registry_raw)
        beams    = self._extract_beams_dict(registry_raw)
        prod_by_beam = self._index_prod_bars(prod_raw)

        return {
            "beam_ids":    beam_ids,
            "beams":       beams,
            "annotations": ann_raw.get("by_beam") or {},
            "axes":        axis_raw.get("axes")   or {},
            "geo_contexts":geo_ctx_raw.get("contexts_by_beam") or {},
            "prod_bars":   prod_by_beam,
            "drawings":    registry_raw.get("drawings") or {},
            "available":   available,
        }

    # ── internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_beam_ids(registry: Dict[str, Any]) -> List[str]:
        raw_ids = registry.get("beam_ids") or []
        if not raw_ids:
            beams = registry.get("beams") or {}
            raw_ids = list(beams.keys()) if isinstance(beams, dict) else []
        return sorted({str(b) for b in raw_ids if b}, key=_natural_key)

    @staticmethod
    def _extract_beams_dict(registry: Dict[str, Any]) -> Dict[str, Any]:
        beams = registry.get("beams") or {}
        if isinstance(beams, dict):
            return {str(k): v for k, v in beams.items()}
        return {}

    @staticmethod
    def _index_prod_bars(prod_raw: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        raw = prod_raw.get("beams") or []
        if isinstance(raw, dict):
            return {str(k): v for k, v in raw.items()}
        for entry in raw:
            if isinstance(entry, dict) and entry.get("beam_id"):
                out[str(entry["beam_id"])] = entry
        return out
