"""Phase D.4.2 — resolve longitudinal bar geometry from physical reinforcement."""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from loguru import logger

from src.geometry.geometry_utils import (
    beam_axis_from_bbox,
    beam_span,
    continuity_from_coverage,
    coverage_ratio,
    point_to_segment_distance,
    position_from_coordinate,
)
from src.geometry.rebar_locator import RebarLocator, RebarSegment

Position = Literal["TOP", "BOTTOM", "UNKNOWN"]
Continuity = Literal["CONTINUOUS", "PARTIAL", "UNKNOWN"]
AttachmentMethod = Literal[
    "LEADER_ENDPOINT",
    "NEAREST_LINE",
    "UNRESOLVED",
]


@dataclass
class GeometryResolution:
    attached_entity_id: Optional[str]
    attachment_method: AttachmentMethod
    attachment_distance: float
    beam_length: float
    bar_length: float
    coverage_ratio: float
    physical_position: Position
    physical_continuity: Continuity
    confidence: int
    attachment_point_x: float
    attachment_point_y: float
    matched_segment_mid_x: float
    matched_segment_mid_y: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_rebar_geometry_config(config_path: Path) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "max_attachment_distance": 9000.0,
        "coverage_threshold": 0.80,
        "horizontal_angle_tolerance": 15.0,
        "minimum_rebar_length": 120.0,
        "minimum_span_ratio": 0.12,
        "stirrup_leg_max_length": 900.0,
        "end_marker_max_axis_span_ratio": 0.15,
        "bbox_margin_mm": 80.0,
        "elevation_band_mm": 80.0,
        "position_band_ratio": 0.12,
        "enable_debug_layers": True,
    }
    if not config_path.exists():
        logger.warning("Rebar geometry config not found — using defaults: {}", config_path)
        return defaults

    data = dict(defaults)
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.lower() in ("true", "false"):
            data[key] = value.lower() == "true"
            continue
        try:
            data[key] = float(value) if "." in value else int(value)
        except ValueError:
            data[key] = value
    return data


class LongitudinalGeometryResolver:
    """Attach longitudinal bar annotations to physical reinforcement geometry."""

    def __init__(
        self,
        locator: RebarLocator,
        config: dict[str, Any],
        region_unions: dict[tuple[str, str], dict[str, float]] | None = None,
        sketch_bbox_lookup: dict[str, dict[str, float]] | None = None,
    ) -> None:
        self._locator = locator
        self._config = config
        self._region_unions = region_unions or {}
        self._sketch_bbox_lookup = sketch_bbox_lookup or {}

    def resolve_all(
        self, engineering_objects: List[dict[str, Any]]
    ) -> Tuple[List[dict[str, Any]], List[dict[str, Any]]]:
        enriched: List[dict[str, Any]] = []
        resolutions: List[dict[str, Any]] = []

        for obj in engineering_objects:
            if obj.get("engineering_type") != "LONGITUDINAL_BAR":
                enriched.append(dict(obj))
                continue
            if obj.get("parser_status") != "SUCCESS":
                enriched.append(dict(obj))
                continue

            resolution = self.resolve_one(obj)
            updated = dict(obj)
            updated["geometry_resolution"] = resolution.to_dict()
            updated["resolved_position"] = resolution.physical_position
            updated["resolved_continuity"] = resolution.physical_continuity
            enriched.append(updated)
            resolutions.append(
                {
                    "object_id": obj.get("object_id"),
                    "source_annotation_id": obj.get("source_annotation_id"),
                    "owner_sketch_id": obj.get("owner_sketch_id"),
                    "resolved_beam_mark": obj.get("resolved_beam_mark"),
                    "clean_text": obj.get("clean_text"),
                    "geometry_resolution": resolution.to_dict(),
                    "resolved_position": updated.get("resolved_position"),
                    "resolved_continuity": updated.get("resolved_continuity"),
                }
            )

        logger.info(
            "Resolved geometry for {} longitudinal bar object(s)",
            len(resolutions),
        )
        return enriched, resolutions

    def resolve_one(self, obj: dict[str, Any]) -> GeometryResolution:
        owner_bbox = obj.get("sketch_bbox") or {}
        sketch_id = str(obj.get("owner_sketch_id", ""))
        if sketch_id in self._sketch_bbox_lookup:
            owner_bbox = self._sketch_bbox_lookup[sketch_id]
        segments = self._locator.find_longitudinal_segments(
            sketch_id, owner_bbox, self._config, reference_bbox=owner_bbox
        )
        search_bbox = owner_bbox
        if not segments:
            union_key = (
                str(obj.get("detail_region_id", "")),
                str(obj.get("resolved_beam_mark", "")),
            )
            union_bbox = self._region_unions.get(union_key)
            if union_bbox:
                segments = self._locator.find_longitudinal_segments(
                    f"{sketch_id}__union",
                    union_bbox,
                    self._config,
                    reference_bbox=owner_bbox,
                )
                if segments:
                    search_bbox = union_bbox

        axis = beam_axis_from_bbox(owner_bbox)
        beam_length = beam_span(owner_bbox, axis)
        attach_x, attach_y, used_leader = self._best_attachment_point(
            obj, search_bbox or owner_bbox
        )

        if not segments or beam_length <= 0.0:
            return self._unresolved(
                attach_x, attach_y, beam_length, "No reinforcement candidates"
            )

        match = self._find_best_segment(segments, obj, search_bbox or owner_bbox)
        if match is None:
            return self._unresolved(
                attach_x, attach_y, beam_length, "No segment within search distance"
            )

        segment, distance, method = match
        bar_length = self._bar_length(
            segment, segments, axis, owner_bbox, search_bbox or owner_bbox
        )
        ratio = coverage_ratio(bar_length, beam_length)
        threshold = float(self._config.get("coverage_threshold", 0.80))
        continuity = continuity_from_coverage(ratio, threshold)

        position_value = segment.mid_y if axis == "X" else segment.mid_x
        band_ratio = float(self._config.get("position_band_ratio", 0.12))
        position = position_from_coordinate(
            position_value, owner_bbox, axis, band_ratio
        )

        confidence = self._confidence(distance, method, position, continuity, ratio)

        return GeometryResolution(
            attached_entity_id=segment.entity_id,
            attachment_method=method,
            attachment_distance=round(distance, 3),
            beam_length=round(beam_length, 3),
            bar_length=round(bar_length, 3),
            coverage_ratio=round(ratio, 4),
            physical_position=position,
            physical_continuity=continuity,
            confidence=confidence,
            attachment_point_x=round(attach_x, 3),
            attachment_point_y=round(attach_y, 3),
            matched_segment_mid_x=round(segment.mid_x, 3),
            matched_segment_mid_y=round(segment.mid_y, 3),
        )

    def _best_attachment_point(
        self, obj: dict[str, Any], bbox: dict[str, float]
    ) -> Tuple[float, float, bool]:
        leader = obj.get("leader_endpoint")
        coords = obj.get("coordinates") or {}
        eval_x = float(coords.get("eval_x", coords.get("x", 0.0)))
        eval_y = float(coords.get("eval_y", coords.get("y", 0.0)))
        candidates: List[Tuple[float, float, bool]] = []
        if leader:
            candidates.append(
                (float(leader["x"]), float(leader["y"]), True)
            )
        candidates.append((eval_x, eval_y, False))
        if bbox:
            candidates.append(
                (
                    max(float(bbox["xmin"]), min(eval_x, float(bbox["xmax"]))),
                    max(float(bbox["ymin"]), min(eval_y, float(bbox["ymax"]))),
                    False,
                )
            )
        return candidates[0] if leader else candidates[1]

    def _attachment_point(
        self, obj: dict[str, Any], bbox: dict[str, float]
    ) -> Tuple[float, float, bool]:
        return self._best_attachment_point(obj, bbox)

    def _find_best_segment(
        self,
        segments: List[RebarSegment],
        obj: dict[str, Any],
        search_bbox: dict[str, float],
    ) -> Optional[Tuple[RebarSegment, float, AttachmentMethod]]:
        max_dist = float(self._config.get("max_attachment_distance", 9000.0))
        best: Optional[Tuple[RebarSegment, float, AttachmentMethod]] = None

        leader = obj.get("leader_endpoint")
        coords = obj.get("coordinates") or {}
        eval_x = float(coords.get("eval_x", coords.get("x", 0.0)))
        eval_y = float(coords.get("eval_y", coords.get("y", 0.0)))
        probe_points: List[Tuple[float, float, bool]] = []
        if leader:
            probe_points.append(
                (float(leader["x"]), float(leader["y"]), True)
            )
        probe_points.append((eval_x, eval_y, False))
        if search_bbox:
            probe_points.append(
                (
                    max(float(search_bbox["xmin"]), min(eval_x, float(search_bbox["xmax"]))),
                    max(float(search_bbox["ymin"]), min(eval_y, float(search_bbox["ymax"]))),
                    False,
                )
            )

        for px, py, used_leader in probe_points:
            for segment in segments:
                dist, _, _ = point_to_segment_distance(
                    px, py, segment.x1, segment.y1, segment.x2, segment.y2
                )
                if dist > max_dist:
                    continue
                method: AttachmentMethod = (
                    "LEADER_ENDPOINT" if used_leader else "NEAREST_LINE"
                )
                if best is None or dist < best[1]:
                    best = (segment, dist, method)

        return best

    def _bar_length(
        self,
        segment: RebarSegment,
        segments: List[RebarSegment],
        axis: str,
        owner_bbox: dict[str, float],
        clip_bbox: dict[str, float],
    ) -> float:
        band = float(self._config.get("elevation_band_mm", 80.0))
        beam_length = beam_span(owner_bbox, axis)
        long_span = max(segment.span_axis, segment.span_perp)

        clipped = self._clip_span_to_bbox(segment, axis, clip_bbox)
        if clipped > 0.0:
            return min(clipped, beam_length)

        if long_span > 0.0:
            return min(long_span, beam_length)

        if segment.is_axis_aligned:
            return min(segment.span_axis, beam_length)

        elevation = segment.mid_y if axis == "X" else segment.mid_x
        band_span = self._locator.max_axis_span_at_elevation(
            segments, elevation, axis, band
        )
        if band_span > 0.0:
            return min(band_span, beam_length)

        if axis == "X":
            xmin, xmax = float(bbox["xmin"]), float(bbox["xmax"])
            dist_left = abs(segment.mid_x - xmin)
            dist_right = abs(xmax - segment.mid_x)
            return beam_length - min(dist_left, dist_right)
        ymin, ymax = float(bbox["ymin"]), float(bbox["ymax"])
        dist_low = abs(segment.mid_y - ymin)
        dist_high = abs(ymax - segment.mid_y)
        return beam_length - min(dist_low, dist_high)

    def _clip_span_to_bbox(
        self, segment: RebarSegment, axis: str, bbox: dict[str, float]
    ) -> float:
        if axis == "X":
            lo = max(float(bbox["xmin"]), min(segment.x1, segment.x2))
            hi = min(float(bbox["xmax"]), max(segment.x1, segment.x2))
            return max(0.0, hi - lo)
        lo = max(float(bbox["ymin"]), min(segment.y1, segment.y2))
        hi = min(float(bbox["ymax"]), max(segment.y1, segment.y2))
        return max(0.0, hi - lo)

    def _confidence(
        self,
        distance: float,
        method: AttachmentMethod,
        position: Position,
        continuity: Continuity,
        ratio: float,
    ) -> int:
        score = 45.0
        max_dist = float(self._config.get("max_attachment_distance", 1200.0))
        if max_dist > 0.0:
            score += 25.0 * max(0.0, 1.0 - distance / max_dist)
        if method == "LEADER_ENDPOINT":
            score += 10.0
        if position != "UNKNOWN":
            score += 10.0
        if continuity != "UNKNOWN":
            score += 10.0
        if ratio >= float(self._config.get("coverage_threshold", 0.80)):
            score += 5.0
        return int(min(100, round(score)))

    def _unresolved(
        self,
        attach_x: float,
        attach_y: float,
        beam_length: float,
        reason: str,
    ) -> GeometryResolution:
        logger.debug("Geometry unresolved at ({}, {}): {}", attach_x, attach_y, reason)
        return GeometryResolution(
            attached_entity_id=None,
            attachment_method="UNRESOLVED",
            attachment_distance=0.0,
            beam_length=round(beam_length, 3),
            bar_length=0.0,
            coverage_ratio=0.0,
            physical_position="UNKNOWN",
            physical_continuity="UNKNOWN",
            confidence=0,
            attachment_point_x=round(attach_x, 3),
            attachment_point_y=round(attach_y, 3),
            matched_segment_mid_x=0.0,
            matched_segment_mid_y=0.0,
        )
