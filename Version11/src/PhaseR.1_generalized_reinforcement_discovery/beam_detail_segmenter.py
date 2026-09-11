"""
beam_detail_segmenter.py — Assign DXF entities to beam detail regions.
MODEL_VERSION: 8.2.0

Phase R.1.1A: delegates to AdaptiveAssociationEngine for multi-evidence
adaptive search, leader association, cluster reconstruction, and orphan recovery.
Legacy fixed-radius mode retained as fallback when r11a.enabled is false.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Dict, List, Optional

from .adaptive_association_engine import AdaptiveAssociationEngine
from .dxf_text_utils import (
    entity_position,
    entity_raw_text,
    is_dimension_entity,
    strip_mtext,
)
from .reinforcement_models import BeamDetail

log = logging.getLogger(__name__)


def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


class BeamDetailSegmenter:

    def __init__(self, config: dict, project_root: Optional[pathlib.Path] = None):
        self._config = config
        self._project_root = project_root
        self._max_radius = float(
            config.get("geometry", {}).get("annotation_search_radius", 5000.0)
        )
        self._use_adaptive = config.get("r11a", {}).get("enabled", True)
        self._enable_dimension_text_scan = bool(
            config.get("discovery", {}).get("enable_dimension_text_scan", False)
        )
        self._engine: Optional[AdaptiveAssociationEngine] = None

    @property
    def association_engine(self) -> Optional[AdaptiveAssociationEngine]:
        return self._engine

    def segment(
        self,
        msp,
        details: List[BeamDetail],
        registry: Optional[dict] = None,
    ) -> Dict[str, List[dict]]:
        if self._use_adaptive and self._project_root:
            self._engine = AdaptiveAssociationEngine(self._config, self._project_root)
            beams_raw = registry.get("beams", registry) if registry else {}
            return self._engine.segment(msp, details, beams_raw)

        return self._legacy_segment(msp, details)

    def _legacy_segment(self, msp, details: List[BeamDetail]) -> Dict[str, List[dict]]:
        if not details:
            return {}

        beam_map: Dict[str, List[dict]] = {d.beam_id: [] for d in details}
        total_assigned = 0
        total_rejected = 0

        for entity in msp:
            dtype = entity.dxftype()
            if dtype not in ("TEXT", "MTEXT"):
                if not (
                    self._enable_dimension_text_scan and is_dimension_entity(entity)
                ):
                    continue

            pos = entity_position(entity)
            if pos is None:
                continue

            x, y = pos
            raw_text = entity_raw_text(entity)
            clean_text = strip_mtext(raw_text)

            best_beam = None
            best_dist = float("inf")

            for detail in details:
                d = _distance(x, y, detail.centroid_x, detail.centroid_y)
                if d < best_dist:
                    best_dist = d
                    best_beam = detail

            if best_beam and best_dist <= self._max_radius:
                beam_map[best_beam.beam_id].append({
                    "x": x,
                    "y": y,
                    "raw_text": raw_text,
                    "clean_text": clean_text,
                    "entity_type": entity.dxftype(),
                    "distance": round(best_dist, 1),
                })
                best_beam.entity_count += 1
                total_assigned += 1
            else:
                total_rejected += 1

        log.info(
            "BeamDetailSegmenter (legacy): %d entities assigned, %d rejected",
            total_assigned, total_rejected,
        )
        return beam_map

