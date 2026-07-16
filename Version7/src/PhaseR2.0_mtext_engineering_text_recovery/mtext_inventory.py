"""STEP 1 — Read every MTEXT entity from DXF unchanged."""
from __future__ import annotations

import math
import pathlib
from typing import Any, Dict, List

from .mtext_models import MtextEntity


class MtextInventory:

    def __init__(self, dxf_path: pathlib.Path, beam_registry: Dict[str, Any]):
        self._dxf = dxf_path
        self._registry = beam_registry

    def build(self) -> List[MtextEntity]:
        if not self._dxf.exists():
            return []
        try:
            import ezdxf
            doc = ezdxf.readfile(str(self._dxf))
        except Exception:
            return []

        entities = []
        idx = 0
        for entity in doc.modelspace():
            if entity.dxftype() != "MTEXT":
                continue
            raw = self._raw_text(entity)
            x, y = self._position(entity)
            layer = str(getattr(entity.dxf, "layer", "") or "")
            entities.append(MtextEntity(
                entity_id=f"MTEXT_{idx:05d}",
                layer=layer,
                x=round(x, 2),
                y=round(y, 2),
                raw_text=raw,
                nearest_beam_id=self._nearest_beam(x, y),
            ))
            idx += 1
        return entities

    @staticmethod
    def _raw_text(entity) -> str:
        try:
            return entity.plain_mtext()
        except Exception:
            return getattr(entity.dxf, "text", "") or ""

    @staticmethod
    def _position(entity) -> tuple:
        try:
            pt = entity.dxf.insert
            return float(pt.x), float(pt.y)
        except Exception:
            return 0.0, 0.0

    def _nearest_beam(self, x: float, y: float) -> str:
        best_id = ""
        best_dist = float("inf")
        for bid, beam in self._registry.get("beams", {}).items():
            cx = beam.get("centroid_x") or beam.get("detail_centroid_x")
            cy = beam.get("centroid_y") or beam.get("detail_centroid_y")
            if cx is None or cy is None:
                continue
            d = math.hypot(float(cx) - x, float(cy) - y)
            if d < best_dist:
                best_dist = d
                best_id = bid
        return best_id
