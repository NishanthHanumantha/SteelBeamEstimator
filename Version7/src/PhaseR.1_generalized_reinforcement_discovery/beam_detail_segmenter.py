"""
beam_detail_segmenter.py — Assign DXF entities to beam detail regions.

For every DXF text/mtext entity the segmenter:
  1. Computes the Euclidean distance to every beam centroid.
  2. Assigns the entity to the closest beam whose centroid is within
     detail_radius DXF units.
  3. Rejects entities that are too far from all beams (noise / title-block text).

No hardcoded beam IDs.  Geometry-only logic.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

import ezdxf

from .reinforcement_models import BeamDetail

log = logging.getLogger(__name__)

# Mtext code stripper
_MTEXT_CODE = re.compile(r"\\[A-Za-z][^;]*;|\\\\|\\P|\\p[^;]+;|\{[^{}]*\}")


def _strip_mtext(raw: str) -> str:
    cleaned = _MTEXT_CODE.sub("", raw)
    cleaned = re.sub(r"%%[A-Za-z]", "", cleaned)
    return cleaned.strip()


def _entity_position(entity) -> Optional[Tuple[float, float]]:
    """Return (x, y) insert point of a TEXT or MTEXT entity."""
    try:
        pt = entity.dxf.insert
        return (float(pt.x), float(pt.y))
    except Exception:
        return None


def _entity_raw_text(entity) -> str:
    if entity.dxftype() == "TEXT":
        return entity.dxf.text or ""
    if entity.dxftype() == "MTEXT":
        try:
            return entity.plain_mtext()
        except Exception:
            return entity.text or ""
    return ""


def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


class BeamDetailSegmenter:
    """
    Assigns every DXF TEXT/MTEXT entity to the nearest beam detail region
    using Euclidean proximity to beam centroids.
    """

    def __init__(self, config: dict):
        self._max_radius = float(
            config.get("geometry", {}).get("annotation_search_radius", 5000.0)
        )

    # ──────────────────────────────────────────────────────────────────────────
    def segment(
        self,
        msp,
        details: List[BeamDetail],
    ) -> Dict[str, List[dict]]:
        """
        Returns a dict: beam_id → [raw_entity_record, ...]
        Each record: {x, y, raw_text, clean_text, entity_type}
        """
        if not details:
            return {}

        beam_map: Dict[str, List[dict]] = {d.beam_id: [] for d in details}
        total_assigned = 0
        total_rejected = 0

        for entity in msp:
            if entity.dxftype() not in ("TEXT", "MTEXT"):
                continue

            pos = _entity_position(entity)
            if pos is None:
                continue

            x, y = pos
            raw_text   = _entity_raw_text(entity)
            clean_text = _strip_mtext(raw_text)

            best_beam  = None
            best_dist  = float("inf")

            for detail in details:
                d = _distance(x, y, detail.centroid_x, detail.centroid_y)
                if d < best_dist:
                    best_dist = d
                    best_beam = detail

            if best_beam and best_dist <= self._max_radius:
                beam_map[best_beam.beam_id].append({
                    "x":           x,
                    "y":           y,
                    "raw_text":    raw_text,
                    "clean_text":  clean_text,
                    "entity_type": entity.dxftype(),
                    "distance":    round(best_dist, 1),
                })
                best_beam.entity_count += 1
                total_assigned += 1
            else:
                total_rejected += 1

        log.info(
            "BeamDetailSegmenter: %d entities assigned, %d rejected",
            total_assigned, total_rejected
        )
        return beam_map
