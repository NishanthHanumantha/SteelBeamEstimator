"""Extract TEXT, MTEXT, and ATTRIB entities from reinforcement drawings."""

from __future__ import annotations

from typing import Any, List

from ezdxf.entities import DXFEntity

from src.reinforcement.reinforcement_geometry_entity import (
    PREFIX_TEXT,
    format_geometry_id,
    geometry_entity,
)
from src.reinforcement.reinforcement_geometry_utils import entity_bbox, entity_text, layer_name


class ReinforcementTextExtractor:
    """Extract all engineering text without interpretation."""

    TEXT_TYPES = frozenset({"TEXT", "MTEXT", "ATTRIB"})

    def extract(self, entities: List[DXFEntity]) -> List[dict[str, Any]]:
        text_objects: List[dict[str, Any]] = []
        counter = 0

        for entity in entities:
            if entity.dxftype() not in self.TEXT_TYPES:
                continue
            text = entity_text(entity)
            if not text:
                continue
            box = entity_bbox(entity)
            if not box:
                continue

            counter += 1
            rotation = 0.0
            height = 250.0
            try:
                rotation = float(getattr(entity.dxf, "rotation", 0.0) or 0.0)
                if entity.dxftype() == "MTEXT":
                    height = float(getattr(entity.dxf, "char_height", 250.0) or 250.0)
                else:
                    height = float(getattr(entity.dxf, "height", 250.0) or 250.0)
            except Exception:
                pass

            text_objects.append(
                geometry_entity(
                    format_geometry_id(PREFIX_TEXT, counter),
                    text=text,
                    bbox=box,
                    layer=layer_name(entity),
                    rotation=round(rotation, 3),
                    height=round(height, 3),
                    entity_type=entity.dxftype(),
                )
            )

        return text_objects
