"""STEP 1 — Raw DXF text inventory (TEXT, MTEXT, ATTRIB, ATTDEF)."""
from __future__ import annotations

import math
import pathlib
from typing import Any, Dict, List

from .regex_validation_models import RawTextEntity

_ENTITY_TYPES = ("TEXT", "MTEXT", "ATTRIB", "ATTDEF")


class RawTextInventory:

    def __init__(self, dxf_path: pathlib.Path, beam_registry: Dict[str, Any]):
        self._dxf = dxf_path
        self._registry = beam_registry

    def build(self) -> List[RawTextEntity]:
        if not self._dxf.exists():
            return []
        try:
            import ezdxf
            doc = ezdxf.readfile(str(self._dxf))
        except Exception as exc:
            return []

        entities: List[RawTextEntity] = []
        idx = 0
        for entity in doc.modelspace():
            etype = entity.dxftype()
            if etype not in _ENTITY_TYPES:
                continue
            raw = self._raw_text(entity)
            if raw is None:
                continue
            x, y = self._position(entity)
            layer = getattr(entity.dxf, "layer", "") or ""
            entities.append(RawTextEntity(
                entity_id=f"DXF_{etype}_{idx:05d}",
                entity_type=etype,
                layer=str(layer),
                x=round(x, 2),
                y=round(y, 2),
                raw_text=raw,
                nearest_beam_id=self._nearest_beam(x, y),
            ))
            idx += 1
        return entities

    @staticmethod
    def _raw_text(entity) -> str:
        etype = entity.dxftype()
        if etype == "TEXT":
            return entity.dxf.text or ""
        if etype == "MTEXT":
            try:
                return entity.plain_mtext()
            except Exception:
                return getattr(entity.dxf, "text", "") or ""
        if etype in ("ATTRIB", "ATTDEF"):
            return getattr(entity.dxf, "text", "") or ""
        return ""

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
