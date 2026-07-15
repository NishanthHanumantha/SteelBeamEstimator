"""
beam_detail_discovery.py — Discover every beam reinforcement detail block.

Reads the V.ROOT.1 beam_registry to obtain all 65 beam centroid positions,
then creates one BeamDetail object per beam.

No hardcoded beam IDs.  No benchmark-specific assumptions.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Dict, List, Optional

from .reinforcement_models import BeamDetail

log = logging.getLogger(__name__)


class BeamDetailDiscovery:
    """
    Discovers all beam reinforcement detail blocks from the V.ROOT.1
    beam_registry and the reinforcement DXF.
    """

    DEFAULT_RADIUS = 5000.0   # DXF-unit search radius

    def __init__(self, project_root: pathlib.Path, config: dict):
        self.project_root  = project_root
        self.config        = config
        self._registry_rel = config.get("discovery", {}).get(
            "beam_registry_path",
            "data/output/PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry.json"
        )
        self._radius       = float(
            config.get("geometry", {}).get("annotation_search_radius", self.DEFAULT_RADIUS)
        )

    # ──────────────────────────────────────────────────────────────────────────
    def discover(self) -> List[BeamDetail]:
        """Return one BeamDetail per beam in the registry."""
        registry = self._load_registry()
        beams_raw = registry.get("beams", {})
        if not beams_raw:
            log.error("beam_registry contains no beams – check V.ROOT.1 output")
            return []

        details: List[BeamDetail] = []
        for beam_id, rec in beams_raw.items():
            cx = rec.get("centroid_x")
            cy = rec.get("centroid_y")
            if cx is None or cy is None:
                log.warning("Beam %s has no centroid – using (0,0)", beam_id)
                cx, cy = 0.0, 0.0

            section = rec.get("section", {}) or {}
            detail = BeamDetail(
                beam_id       = beam_id,
                beam_mark     = rec.get("beam_mark", beam_id),
                centroid_x    = float(cx),
                centroid_y    = float(cy),
                section       = section,
                detail_radius = self._radius,
            )
            details.append(detail)

        log.info("BeamDetailDiscovery: %d beam details discovered", len(details))
        return details

    # ──────────────────────────────────────────────────────────────────────────
    def _load_registry(self) -> dict:
        p = self.project_root / self._registry_rel
        if not p.exists():
            log.error("beam_registry not found at %s", p)
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            log.error("Cannot read beam_registry: %s", exc)
            return {}
