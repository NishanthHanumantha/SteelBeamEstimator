"""Extract INSERT and block reference geometry."""

from __future__ import annotations

from typing import Any, Dict, List

from ezdxf.entities import DXFEntity

from src.reinforcement.reinforcement_geometry_entity import (
    PREFIX_BLOCK,
    format_geometry_id,
    geometry_entity,
)
from src.reinforcement.reinforcement_geometry_utils import entity_bbox, layer_name


class BlockExtractor:
    """Extract block inserts and attributes without interpretation."""

    def extract(self, entities: List[DXFEntity]) -> List[dict[str, Any]]:
        blocks: List[dict[str, Any]] = []
        counter = 0

        for entity in entities:
            if entity.dxftype() != "INSERT":
                continue
            box = entity_bbox(entity)
            if not box:
                continue

            counter += 1
            attributes: Dict[str, str] = {}
            try:
                for attrib in entity.attribs:
                    tag = str(getattr(attrib.dxf, "tag", "") or "")
                    text = str(getattr(attrib.dxf, "text", "") or "")
                    if tag:
                        attributes[tag] = text
            except Exception:
                pass

            insertion = {
                "x": round(float(entity.dxf.insert.x), 3),
                "y": round(float(entity.dxf.insert.y), 3),
            }
            blocks.append(
                geometry_entity(
                    format_geometry_id(PREFIX_BLOCK, counter),
                    name=str(entity.dxf.name),
                    insertion=insertion,
                    bbox=box,
                    layer=layer_name(entity),
                    attributes=attributes,
                    entity_type="INSERT",
                )
            )

        return blocks
