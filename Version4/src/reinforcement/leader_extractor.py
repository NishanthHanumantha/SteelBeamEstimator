"""Extract LEADER, MULTILEADER, and arrow polyline geometry."""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from ezdxf.entities import DXFEntity

from src.reinforcement.reinforcement_geometry_entity import (
    PREFIX_LEADER,
    format_geometry_id,
    geometry_entity,
)
from src.reinforcement.reinforcement_geometry_utils import layer_name, normalize_layers


class LeaderExtractor:
    """Detect leader lines and arrowheads without ownership assignment."""

    def __init__(self, config: dict[str, Any]) -> None:
        g2 = config.get("reinforcement_geometry", {})
        self._arrow_layers = set(
            normalize_layers(g2.get("arrow_layers", "-S-ARROW"))
        )

    def extract(self, entities: List[DXFEntity]) -> List[dict[str, Any]]:
        leaders: List[dict[str, Any]] = []
        counter = 0

        for entity in entities:
            dxftype = entity.dxftype()
            if dxftype == "LEADER":
                leader = self._from_leader_entity(entity)
                if leader:
                    counter += 1
                    leaders.append(
                        geometry_entity(
                            format_geometry_id(PREFIX_LEADER, counter),
                            **leader,
                        )
                    )
            elif dxftype in ("LWPOLYLINE", "POLYLINE", "LINE"):
                layer = layer_name(entity)
                if layer in self._arrow_layers or "ARROW" in layer.upper():
                    leader = self._from_linear_entity(entity, layer)
                    if leader:
                        counter += 1
                        leaders.append(
                            geometry_entity(
                                format_geometry_id(PREFIX_LEADER, counter),
                                **leader,
                            )
                        )

        return leaders

    def _from_leader_entity(self, entity: DXFEntity) -> Optional[dict[str, Any]]:
        try:
            vertices = list(entity.vertices)
            if len(vertices) < 2:
                return None
            start = self._point(vertices[0])
            end = self._point(vertices[-1])
            if not start or not end:
                return None
            return {
                "start": start,
                "end": end,
                "arrow": True,
                "layer": layer_name(entity),
                "entity_type": "LEADER",
                "vertex_count": len(vertices),
            }
        except Exception:
            return None

    def _from_linear_entity(
        self,
        entity: DXFEntity,
        layer: str,
    ) -> Optional[dict[str, Any]]:
        try:
            if entity.dxftype() == "LINE":
                start = self._point(entity.dxf.start)
                end = self._point(entity.dxf.end)
            elif entity.dxftype() == "LWPOLYLINE":
                points = list(entity.get_points("xy"))
                if len(points) < 2:
                    return None
                start = {"x": round(points[0][0], 3), "y": round(points[0][1], 3)}
                end = {"x": round(points[-1][0], 3), "y": round(points[-1][1], 3)}
            else:
                return None
            if not start or not end:
                return None
            return {
                "start": start,
                "end": end,
                "arrow": True,
                "layer": layer,
                "entity_type": entity.dxftype(),
            }
        except Exception:
            return None

    @staticmethod
    def _point(value: Any) -> Optional[dict[str, float]]:
        try:
            return {"x": round(float(value[0]), 3), "y": round(float(value[1]), 3)}
        except Exception:
            try:
                return {"x": round(float(value.x), 3), "y": round(float(value.y), 3)}
            except Exception:
                return None
