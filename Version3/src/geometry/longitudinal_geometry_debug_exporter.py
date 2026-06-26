"""Phase D.4.2 — DXF debug layers for rebar geometry resolution."""

from pathlib import Path
from typing import Any, Dict, List

import ezdxf
from loguru import logger

from src.geometry.rebar_locator import RebarLocator

_LAYER_GEOMETRY = "DEBUG_REBAR_GEOMETRY"
_LAYER_ATTACHMENTS = "DEBUG_REBAR_ATTACHMENTS"
_LAYER_CONTINUITY = "DEBUG_REBAR_CONTINUITY"
_LAYER_POSITION = "DEBUG_REBAR_POSITION"

_COLOR_OK = 3
_COLOR_FALLBACK = 2
_COLOR_FAIL = 1


class LongitudinalGeometryDebugExporter:
    """Draw leader endpoints, matched segments, and resolution attributes."""

    def __init__(self, locator: RebarLocator) -> None:
        self._locator = locator

    def export(
        self,
        enriched_objects: List[dict[str, Any]],
        output_path: Path,
        config: dict[str, Any],
    ) -> None:
        doc = ezdxf.new("R2010")
        for layer in (
            _LAYER_GEOMETRY,
            _LAYER_ATTACHMENTS,
            _LAYER_CONTINUITY,
            _LAYER_POSITION,
        ):
            if layer not in doc.layers:
                doc.layers.add(layer)
        msp = doc.modelspace()

        drawn_sketches: set[str] = set()
        for obj in enriched_objects:
            if obj.get("engineering_type") != "LONGITUDINAL_BAR":
                continue
            sketch_id = str(obj.get("owner_sketch_id", ""))
            bbox = obj.get("sketch_bbox") or {}
            if sketch_id and sketch_id not in drawn_sketches and bbox:
                segments = self._locator.find_longitudinal_segments(
                    sketch_id, bbox, config
                )
                for segment in segments:
                    msp.add_line(
                        (segment.x1, segment.y1),
                        (segment.x2, segment.y2),
                        dxfattribs={"layer": _LAYER_GEOMETRY, "color": 8},
                    )
                drawn_sketches.add(sketch_id)

            geo = obj.get("geometry_resolution") or {}
            method = geo.get("attachment_method", "UNRESOLVED")
            color = _color_for(method)
            ax = float(geo.get("attachment_point_x", 0.0))
            ay = float(geo.get("attachment_point_y", 0.0))
            mx = float(geo.get("matched_segment_mid_x", 0.0))
            my = float(geo.get("matched_segment_mid_y", 0.0))

            msp.add_circle(
                (ax, ay),
                90.0,
                dxfattribs={"layer": _LAYER_ATTACHMENTS, "color": color},
            )
            if geo.get("attached_entity_id"):
                msp.add_line(
                    (ax, ay),
                    (mx, my),
                    dxfattribs={"layer": _LAYER_ATTACHMENTS, "color": color},
                )

            continuity = obj.get("resolved_continuity", "UNKNOWN")
            position = obj.get("resolved_position", "UNKNOWN")
            label = (
                f"{str(obj.get('object_id', ''))[:8]}\n"
                f"P={position} C={continuity}\n"
                f"cov={geo.get('coverage_ratio', 0)}"
            )
            msp.add_text(
                label,
                dxfattribs={
                    "layer": _LAYER_CONTINUITY,
                    "color": color,
                    "height": 160.0,
                    "insert": (ax, ay + 220.0),
                },
            )
            pos_layer = _LAYER_POSITION
            msp.add_text(
                position,
                dxfattribs={
                    "layer": pos_layer,
                    "color": _COLOR_OK if position != "UNKNOWN" else _COLOR_FAIL,
                    "height": 140.0,
                    "insert": (mx, my + 180.0),
                },
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info("Phase D.4.2 debug DXF -> {}", output_path)


def _color_for(method: str) -> int:
    if method == "LEADER_ENDPOINT":
        return _COLOR_OK
    if method == "NEAREST_LINE":
        return _COLOR_FALLBACK
    return _COLOR_FAIL
