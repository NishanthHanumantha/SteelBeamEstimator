"""Detect engineering detail regions from reinforcement drawing geometry."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from ezdxf.entities import DXFEntity

from src.reinforcement.reinforcement_geometry_entity import (
    PREFIX_REGION,
    format_geometry_id,
    geometry_entity,
)
from src.reinforcement.reinforcement_geometry_utils import (
    bbox_center,
    entity_bbox,
    entity_center,
    entity_text,
    layer_name,
    merge_bboxes,
    normalize_layers,
    parse_beam_section_label,
    point_in_bbox,
)

REGION_TYPE_ENGINEERING_DETAIL = "ENGINEERING_DETAIL"
DETAIL_TYPE_SINGLE_BEAM = "SINGLE_BEAM"
DETAIL_TYPE_MULTI_VIEW_SINGLE_BEAM = "MULTI_VIEW_SINGLE_BEAM"
DETAIL_TYPE_CONTINUOUS_MULTI_SPAN = "CONTINUOUS_MULTI_SPAN"

GEOMETRY_TYPES = frozenset(
    {"LINE", "LWPOLYLINE", "POLYLINE", "ARC", "SPLINE", "CIRCLE", "ELLIPSE"}
)


@dataclass
class HeaderSeed:
    beam_mark: str
    x: float
    y: float
    header_bbox: dict[str, float]
    label_text: str


@dataclass
class DetailRegionGroup:
    seeds: List[HeaderSeed] = field(default_factory=list)
    continuity_links: List[dict[str, Any]] = field(default_factory=list)
    whitespace_splits: List[dict[str, Any]] = field(default_factory=list)
    detail_type_hint: Optional[str] = None
    duplicate_mark_detected: bool = False

    @property
    def beam_marks(self) -> List[str]:
        ordered: List[str] = []
        seen: Set[str] = set()
        for seed in sorted(self.seeds, key=lambda s: s.x):
            if seed.beam_mark not in seen:
                seen.add(seed.beam_mark)
                ordered.append(seed.beam_mark)
        return ordered

    @property
    def label(self) -> str:
        return "/".join(self.beam_marks)


class ReinforcementRegionDetector:
    """Detect engineering detail regions via connected reinforcement geometry."""

    def __init__(self, config: dict[str, Any]) -> None:
        g2 = config.get("reinforcement_geometry", {})
        self._header_layers = set(
            normalize_layers(g2.get("region_header_layers", "SEC TEXT,S-BEAM-IDEN"))
        )
        self._geometry_layers = set(
            normalize_layers(
                g2.get(
                    "reinforcement_layers",
                    "-STR-REINF,-STR-BEAM,-S-STIRUP",
                )
            )
        )
        self._row_tolerance_mm = float(g2.get("row_tolerance_mm", 2500.0))
        self._detail_band_below_mm = float(g2.get("detail_band_below_mm", 4500.0))
        self._detail_band_above_mm = float(g2.get("detail_band_above_mm", 1500.0))
        self._strip_width_mm = float(g2.get("strip_width_mm", 300.0))
        self._shared_bar_threshold = int(g2.get("shared_bar_threshold", 1))
        self._shared_leader_threshold = float(g2.get("shared_leader_threshold", 0.3))
        self._geometry_overlap_ratio = float(g2.get("geometry_overlap_ratio", 0.12))
        self._continuity_gap_mm = float(g2.get("continuity_gap_mm", 800.0))
        self._whitespace_threshold = int(g2.get("whitespace_threshold", 0))
        self._region_growth_radius = float(g2.get("region_growth_radius", 12000.0))
        self._region_margin_below_mm = float(
            g2.get("region_margin_y_below_mm", g2.get("detail_band_below_mm", 9000.0))
        )
        self._region_margin_above_mm = float(
            g2.get("region_margin_y_above_mm", g2.get("detail_band_above_mm", 2500.0))
        )
        self._allow_multibeam_regions = bool(g2.get("allow_multibeam_regions", True))
        self._continuity_min_score = float(g2.get("continuity_min_score", 0.85))
        self._header_merge_distance_mm = float(g2.get("header_merge_distance_mm", 4000.0))
        self._min_strip_entities_for_continuity = int(
            g2.get("min_strip_entities_for_continuity", 4)
        )
        self._duplicate_mark_detection = bool(g2.get("duplicate_mark_detection", True))
        self._enable_multiview_detection = bool(g2.get("enable_multiview_detection", True))
        self._duplicate_merge_distance_mm = float(g2.get("duplicate_merge_distance_mm", 250.0))
        self._min_duplicate_confidence = float(g2.get("min_duplicate_confidence", 0.85))

    def detect(
        self,
        entities: List[DXFEntity],
        text_objects: List[dict[str, Any]],
        leaders: List[dict[str, Any]],
        blocks: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        geometry_items = self._collect_geometry_items(entities)
        seeds = self._collect_header_seeds(entities, text_objects)
        if not seeds:
            return []

        row_groups = self._group_seeds_by_row(seeds)
        region_groups: List[DetailRegionGroup] = []
        for row_seeds in row_groups:
            region_groups.extend(self._build_row_regions(row_seeds, geometry_items))

        regions: List[dict[str, Any]] = []
        for idx, group in enumerate(region_groups, start=1):
            row_seeds = self._row_for_group(group, row_groups)
            region = self._build_region(
                idx,
                group,
                row_seeds,
                geometry_items,
                text_objects,
                leaders,
                blocks,
            )
            if region:
                regions.append(region)
        return regions

    def _collect_geometry_items(
        self,
        entities: List[DXFEntity],
    ) -> List[dict[str, Any]]:
        items: List[dict[str, Any]] = []
        for entity in entities:
            if entity.dxftype() not in GEOMETRY_TYPES:
                continue
            layer = layer_name(entity)
            if self._geometry_layers and layer not in self._geometry_layers:
                continue
            box = entity_bbox(entity)
            center = entity_center(entity)
            if not box or not center:
                continue
            items.append(
                {
                    "bbox": box,
                    "center": center,
                    "layer": layer,
                    "entity_type": entity.dxftype(),
                }
            )
        return items

    def _collect_header_seeds(
        self,
        entities: List[DXFEntity],
        text_objects: List[dict[str, Any]],
    ) -> List[HeaderSeed]:
        raw_seeds: List[HeaderSeed] = []
        for entity in entities:
            if entity.dxftype() not in ("TEXT", "MTEXT", "ATTRIB"):
                continue
            layer = layer_name(entity)
            if self._header_layers and layer not in self._header_layers:
                continue
            text = entity_text(entity)
            parsed = parse_beam_section_label(text)
            if not parsed:
                continue
            center = entity_center(entity)
            box = entity_bbox(entity)
            if not center or not box:
                continue
            raw_seeds.append(
                HeaderSeed(
                    beam_mark=parsed["beam_mark"],
                    x=center[0],
                    y=center[1],
                    header_bbox=box,
                    label_text=text,
                )
            )

        if not raw_seeds:
            for item in text_objects:
                parsed = parse_beam_section_label(str(item.get("text", "")))
                box = item.get("bbox")
                if not parsed or not box:
                    continue
                cx, cy = bbox_center(box)
                raw_seeds.append(
                    HeaderSeed(
                        beam_mark=parsed["beam_mark"],
                        x=cx,
                        y=cy,
                        header_bbox=box,
                        label_text=str(item.get("text", "")),
                    )
                )

        return self._dedupe_header_seeds(raw_seeds)

    def _dedupe_header_seeds(self, seeds: List[HeaderSeed]) -> List[HeaderSeed]:
        if not seeds:
            return []

        grouped: Dict[str, List[HeaderSeed]] = {}
        for seed in seeds:
            grouped.setdefault(seed.beam_mark, []).append(seed)

        deduped: List[HeaderSeed] = []
        for mark, group in grouped.items():
            group.sort(key=lambda s: (s.y, s.x))
            current = group[0]
            merged = HeaderSeed(
                beam_mark=mark,
                x=current.x,
                y=current.y,
                header_bbox=dict(current.header_bbox),
                label_text=current.label_text,
            )
            for seed in group[1:]:
                merge_dist = (
                    self._duplicate_merge_distance_mm
                    if self._enable_multiview_detection
                    else self._header_merge_distance_mm
                )
                if abs(seed.x - merged.x) <= merge_dist and abs(seed.y - merged.y) <= self._row_tolerance_mm:
                    merged.header_bbox = merge_bboxes([merged.header_bbox, seed.header_bbox]) or merged.header_bbox
                    merged.x = (merged.x + seed.x) / 2.0
                    merged.y = (merged.y + seed.y) / 2.0
                else:
                    deduped.append(merged)
                    merged = HeaderSeed(
                        beam_mark=mark,
                        x=seed.x,
                        y=seed.y,
                        header_bbox=dict(seed.header_bbox),
                        label_text=seed.label_text,
                    )
            deduped.append(merged)
        deduped.sort(key=lambda s: (-s.y, s.x))
        return deduped

    def _dedupe_row_seeds(self, row_seeds: List[HeaderSeed]) -> List[HeaderSeed]:
        if not row_seeds:
            return []
        ordered = sorted(row_seeds, key=lambda s: s.x)
        deduped: List[HeaderSeed] = []
        for seed in ordered:
            if (
                deduped
                and deduped[-1].beam_mark == seed.beam_mark
                and abs(seed.x - deduped[-1].x) <= self._duplicate_merge_distance_mm
            ):
                prev = deduped[-1]
                merged_box = merge_bboxes([prev.header_bbox, seed.header_bbox])
                deduped[-1] = HeaderSeed(
                    beam_mark=prev.beam_mark,
                    x=(prev.x + seed.x) / 2.0,
                    y=(prev.y + seed.y) / 2.0,
                    header_bbox=merged_box or prev.header_bbox,
                    label_text=prev.label_text,
                )
            else:
                deduped.append(seed)
        return deduped

    def _group_seeds_by_row(self, seeds: List[HeaderSeed]) -> List[List[HeaderSeed]]:
        if not seeds:
            return []
        rows: List[List[HeaderSeed]] = []
        current_row: List[HeaderSeed] = [seeds[0]]
        row_y = seeds[0].y
        for seed in seeds[1:]:
            if abs(seed.y - row_y) <= self._row_tolerance_mm:
                current_row.append(seed)
            else:
                rows.append(sorted(current_row, key=lambda s: s.x))
                current_row = [seed]
                row_y = seed.y
        rows.append(sorted(current_row, key=lambda s: s.x))
        return rows

    def _build_row_regions(
        self,
        row_seeds: List[HeaderSeed],
        geometry_items: List[dict[str, Any]],
    ) -> List[DetailRegionGroup]:
        if not row_seeds:
            return []

        row_seeds = self._dedupe_row_seeds(row_seeds)
        mark_counts = Counter(seed.beam_mark for seed in row_seeds)
        duplicate_marks: Set[str] = set()
        if self._duplicate_mark_detection and self._enable_multiview_detection:
            duplicate_marks = {mark for mark, count in mark_counts.items() if count > 1}

        bounds = self._column_bounds(row_seeds)
        links: List[Tuple[int, int, dict[str, Any]]] = []
        splits: List[dict[str, Any]] = []

        for idx in range(len(row_seeds) - 1):
            left = row_seeds[idx]
            right = row_seeds[idx + 1]
            mid = bounds[idx]
            detail_band = self._detail_band(left.y, right.y)
            continuity = self._continuity_at_boundary(
                mid,
                detail_band,
                geometry_items,
                row_seeds,
                idx,
            )
            blocked = (
                left.beam_mark in duplicate_marks
                or right.beam_mark in duplicate_marks
                or left.beam_mark == right.beam_mark
            )
            if continuity["continuous"] and not blocked:
                links.append((idx, idx + 1, continuity))
            elif not blocked and not continuity["continuous"]:
                splits.append(
                    {
                        "left_mark": left.beam_mark,
                        "right_mark": right.beam_mark,
                        "midpoint_x": round(mid, 3),
                        "strip_entity_count": continuity["strip_entity_count"],
                        "reason": "WHITESPACE",
                    }
                )
            elif blocked:
                splits.append(
                    {
                        "left_mark": left.beam_mark,
                        "right_mark": right.beam_mark,
                        "midpoint_x": round(mid, 3),
                        "strip_entity_count": continuity["strip_entity_count"],
                        "reason": "DUPLICATE_MARK",
                    }
                )

        single_indices = [
            idx for idx, seed in enumerate(row_seeds) if seed.beam_mark not in duplicate_marks
        ]
        parent = {idx: idx for idx in single_indices}

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i: int, j: int) -> None:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[rj] = ri

        if self._allow_multibeam_regions:
            for left_idx, right_idx, continuity in links:
                if continuity["continuity_score"] >= self._continuity_min_score:
                    union(left_idx, right_idx)

        groups: List[DetailRegionGroup] = []

        roots: Dict[int, DetailRegionGroup] = {}
        for idx in single_indices:
            root = find(idx)
            if root not in roots:
                roots[root] = DetailRegionGroup()
            roots[root].seeds.append(row_seeds[idx])

        for left_idx, right_idx, continuity in links:
            if left_idx not in parent or right_idx not in parent:
                continue
            root = find(left_idx)
            if root in roots:
                roots[root].continuity_links.append(
                    {
                        "from_mark": row_seeds[left_idx].beam_mark,
                        "to_mark": row_seeds[right_idx].beam_mark,
                        **continuity,
                    }
                )

        for group in roots.values():
            group.whitespace_splits = splits
            groups.append(group)

        for mark in sorted(duplicate_marks, key=lambda m: min(s.x for s in row_seeds if s.beam_mark == m)):
            mark_seeds = [seed for seed in row_seeds if seed.beam_mark == mark]
            groups.append(
                DetailRegionGroup(
                    seeds=mark_seeds,
                    whitespace_splits=splits,
                    detail_type_hint=DETAIL_TYPE_MULTI_VIEW_SINGLE_BEAM,
                    duplicate_mark_detected=True,
                )
            )

        groups.sort(key=lambda g: min(seed.x for seed in g.seeds))
        return groups

    def _row_for_group(
        self,
        group: DetailRegionGroup,
        row_groups: List[List[HeaderSeed]],
    ) -> List[HeaderSeed]:
        if not group.seeds:
            return []
        first = group.seeds[0]
        for row in row_groups:
            for seed in row:
                if seed.beam_mark == first.beam_mark and abs(seed.x - first.x) < 1.0:
                    return row
        return list(group.seeds)

    def _region_x_bounds(
        self,
        group: DetailRegionGroup,
        row_seeds: List[HeaderSeed],
    ) -> Tuple[float, float]:
        seed_indices: List[int] = []
        for gs in group.seeds:
            for idx, rs in enumerate(row_seeds):
                if gs.beam_mark == rs.beam_mark and abs(gs.x - rs.x) < 1.0:
                    seed_indices.append(idx)
                    break
        if not seed_indices:
            xs = [seed.x for seed in group.seeds]
            return min(xs) - 2000.0, max(xs) + 2000.0

        i_min = min(seed_indices)
        i_max = max(seed_indices)
        xs = [seed.x for seed in row_seeds]
        bounds = self._column_bounds(row_seeds)
        margin = 1500.0
        if i_min == 0:
            x_min = xs[0] - margin
        else:
            x_min = bounds[i_min - 1]
        if i_max >= len(xs) - 1:
            x_max = xs[-1] + margin
        else:
            x_max = bounds[i_max]
        return x_min, x_max

    def _column_bounds(self, row_seeds: List[HeaderSeed]) -> List[float]:
        xs = [seed.x for seed in row_seeds]
        bounds: List[float] = []
        for idx in range(len(xs) - 1):
            bounds.append((xs[idx] + xs[idx + 1]) / 2.0)
        return bounds

    def _detail_band(self, left_y: float, right_y: float) -> dict[str, float]:
        header_y = (left_y + right_y) / 2.0
        return {
            "min_y": header_y - self._detail_band_below_mm,
            "max_y": header_y + self._detail_band_above_mm,
        }

    def _continuity_at_boundary(
        self,
        midpoint_x: float,
        detail_band: dict[str, float],
        geometry_items: List[dict[str, Any]],
        row_seeds: List[HeaderSeed],
        left_index: int,
    ) -> dict[str, Any]:
        left = row_seeds[left_index]
        right = row_seeds[left_index + 1]
        strip_entities = self._entities_in_strip(
            geometry_items,
            midpoint_x,
            detail_band,
        )
        strip_count = len(strip_entities)
        crossing_long = self._count_crossing_long_segments(
            geometry_items,
            midpoint_x,
            detail_band,
            max_span_mm=15000.0,
        )
        left_sketch = self._column_sketch_bbox(row_seeds, left_index, geometry_items)
        right_sketch = self._column_sketch_bbox(row_seeds, left_index + 1, geometry_items)
        overlap_ratio = self._bbox_overlap_ratio(left_sketch, right_sketch)
        sketch_gap_mm = self._sketch_gap_mm(left_sketch, right_sketch)

        strip_ok = strip_count >= self._min_strip_entities_for_continuity
        gap_ok = sketch_gap_mm <= self._continuity_gap_mm
        crossing_ok = crossing_long >= self._shared_bar_threshold
        continuous = strip_ok and gap_ok and crossing_ok
        if not self._allow_multibeam_regions:
            continuous = False

        continuity_score = 0.0
        if continuous:
            strip_score = min(1.0, strip_count / max(self._min_strip_entities_for_continuity, 1))
            bar_score = min(1.0, crossing_long / max(self._shared_bar_threshold, 1))
            overlap_score = min(1.0, overlap_ratio / max(self._geometry_overlap_ratio, 0.01))
            gap_score = min(
                1.0,
                max(0.0, 1.0 - sketch_gap_mm / max(self._continuity_gap_mm, 1.0)),
            )
            continuity_score = round(
                (strip_score + bar_score + overlap_score + gap_score) / 4.0,
                4,
            )

        return {
            "continuous": continuous and continuity_score >= self._continuity_min_score,
            "continuity_score": continuity_score,
            "strip_entity_count": strip_count,
            "crossing_long_segments": crossing_long,
            "geometry_overlap_ratio": round(overlap_ratio, 4),
            "sketch_gap_mm": round(sketch_gap_mm, 3),
            "detail_band": detail_band,
            "midpoint_x": round(midpoint_x, 3),
        }

    def _column_search_box(
        self,
        row_seeds: List[HeaderSeed],
        seed_index: int,
    ) -> dict[str, float]:
        xs = [seed.x for seed in row_seeds]
        bounds = self._column_bounds(row_seeds)
        seed = row_seeds[seed_index]
        margin = 1500.0
        if seed_index == 0:
            x_min = xs[0] - margin
        else:
            x_min = bounds[seed_index - 1]
        if seed_index >= len(xs) - 1:
            x_max = xs[-1] + margin
        else:
            x_max = bounds[seed_index]
        return {
            "min_x": x_min,
            "max_x": x_max,
            "min_y": seed.y - self._detail_band_below_mm,
            "max_y": seed.y + self._detail_band_above_mm,
        }

    def _sketch_gap_mm(
        self,
        left: Optional[dict[str, float]],
        right: Optional[dict[str, float]],
    ) -> float:
        if not left or not right:
            return float("inf")
        return max(0.0, right["min_x"] - left["max_x"])

    def _entities_in_strip(
        self,
        geometry_items: List[dict[str, Any]],
        midpoint_x: float,
        detail_band: dict[str, float],
    ) -> List[dict[str, Any]]:
        strip_box = {
            "min_x": midpoint_x - self._strip_width_mm,
            "max_x": midpoint_x + self._strip_width_mm,
            "min_y": detail_band["min_y"],
            "max_y": detail_band["max_y"],
        }
        return [
            item
            for item in geometry_items
            if point_in_bbox(item["center"][0], item["center"][1], strip_box)
        ]

    def _count_crossing_long_segments(
        self,
        geometry_items: List[dict[str, Any]],
        midpoint_x: float,
        detail_band: dict[str, float],
        max_span_mm: float = 15000.0,
    ) -> int:
        count = 0
        min_span = max(self._continuity_gap_mm * 2.0, 2500.0)
        for item in geometry_items:
            box = item["bbox"]
            cy = item["center"][1]
            if cy < detail_band["min_y"] or cy > detail_band["max_y"]:
                continue
            width = box["max_x"] - box["min_x"]
            height = box["max_y"] - box["min_y"]
            span = max(width, height)
            if span < min_span or span > max_span_mm:
                continue
            if width >= height and box["min_x"] < midpoint_x < box["max_x"]:
                count += 1
        return count

    def _column_sketch_bbox(
        self,
        row_seeds: List[HeaderSeed],
        seed_index: int,
        geometry_items: List[dict[str, Any]],
    ) -> Optional[dict[str, float]]:
        search_box = self._column_search_box(row_seeds, seed_index)
        boxes = [
            item["bbox"]
            for item in geometry_items
            if point_in_bbox(item["center"][0], item["center"][1], search_box)
        ]
        return merge_bboxes(boxes)

    def _bbox_overlap_ratio(
        self,
        left: Optional[dict[str, float]],
        right: Optional[dict[str, float]],
    ) -> float:
        if not left or not right:
            return 0.0
        overlap = max(
            0.0,
            min(left["max_x"], right["max_x"]) - max(left["min_x"], right["min_x"]),
        )
        min_width = min(
            left["max_x"] - left["min_x"],
            right["max_x"] - right["min_x"],
            1.0,
        )
        return round(min(1.0, overlap / min_width), 4)

    def _build_region(
        self,
        index: int,
        group: DetailRegionGroup,
        row_seeds: List[HeaderSeed],
        geometry_items: List[dict[str, Any]],
        text_objects: List[dict[str, Any]],
        leaders: List[dict[str, Any]],
        blocks: List[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        if not group.seeds:
            return None

        header_boxes = [seed.header_bbox for seed in group.seeds]
        header_box = merge_bboxes(header_boxes)
        if not header_box:
            return None

        x_min, x_max = self._region_x_bounds(group, row_seeds)
        header_y = sum(seed.y for seed in group.seeds) / len(group.seeds)
        detail_band = self._detail_band(group.seeds[0].y, group.seeds[-1].y)
        region_box = {
            "min_x": x_min,
            "max_x": x_max,
            "min_y": detail_band["min_y"],
            "max_y": detail_band["max_y"],
        }

        geometry_boxes = [
            item["bbox"]
            for item in geometry_items
            if point_in_bbox(item["center"][0], item["center"][1], region_box)
        ]
        grown_box = merge_bboxes([region_box, header_box, *geometry_boxes]) or region_box
        grown_box["min_x"] = max(grown_box["min_x"], x_min)
        grown_box["max_x"] = min(grown_box["max_x"], x_max)
        grown_box["min_y"] = max(grown_box["min_y"], detail_band["min_y"])
        grown_box["max_y"] = min(grown_box["max_y"], detail_band["max_y"])

        text_count = self._count_in_bbox(text_objects, grown_box)
        leader_count = self._count_in_bbox(leaders, grown_box, point_key="start")
        block_count = self._count_in_bbox(blocks, grown_box)

        beam_marks = group.beam_marks
        duplicate_mark_detected = group.duplicate_mark_detected or (
            len(group.seeds) > len(beam_marks)
        )
        if group.detail_type_hint:
            detail_type = group.detail_type_hint
        elif duplicate_mark_detected and len(beam_marks) == 1:
            detail_type = DETAIL_TYPE_MULTI_VIEW_SINGLE_BEAM
        elif len(beam_marks) > 1:
            detail_type = DETAIL_TYPE_CONTINUOUS_MULTI_SPAN
        else:
            detail_type = DETAIL_TYPE_SINGLE_BEAM

        view_seeds = self._view_seed_specs(group, row_seeds)
        beam_count = len(beam_marks)
        view_count = len(view_seeds) if detail_type == DETAIL_TYPE_MULTI_VIEW_SINGLE_BEAM else 1

        continuity_score = self._group_continuity_score(group)
        shared_geometry_score = self._group_geometry_score(group)
        shared_leader_score = self._shared_leader_score(group, leaders, grown_box)
        shared_text_score = self._shared_text_score(group, text_objects, grown_box)
        if detail_type == DETAIL_TYPE_MULTI_VIEW_SINGLE_BEAM:
            engineering_confidence = round(
                min(
                    1.0,
                    max(self._min_duplicate_confidence, 0.95 + 0.01 * (view_count - 1)),
                ),
                4,
            )
        else:
            engineering_confidence = round(
                min(
                    1.0,
                    continuity_score * 0.4
                    + min(1.0, shared_geometry_score) * 0.25
                    + min(1.0, shared_leader_score) * 0.2
                    + min(1.0, shared_text_score) * 0.15,
                ),
                4,
            )

        label = beam_marks[0] if detail_type == DETAIL_TYPE_MULTI_VIEW_SINGLE_BEAM else group.label

        return geometry_entity(
            format_geometry_id(PREFIX_REGION, index),
            region_type=REGION_TYPE_ENGINEERING_DETAIL,
            detail_type=detail_type,
            label=label,
            beam_marks=beam_marks,
            beam_count=beam_count,
            view_count=view_count,
            views=[],
            duplicate_mark_detected=duplicate_mark_detected,
            bbox=grown_box,
            header_bbox=header_box,
            text_count=text_count,
            leader_count=leader_count,
            block_count=block_count,
            label_texts=[seed.label_text for seed in group.seeds],
            continuity_score=continuity_score,
            shared_geometry_score=shared_geometry_score,
            shared_text_score=shared_text_score,
            shared_leader_score=shared_leader_score,
            engineering_confidence=engineering_confidence,
            detection_debug={
                "algorithm": "engineering_detail_geometry_growth",
                "classification": detail_type,
                "growth_path": beam_marks,
                "continuity_links": group.continuity_links,
                "whitespace_splits": group.whitespace_splits,
                "detail_band": self._detail_band(group.seeds[0].y, group.seeds[-1].y),
                "view_seeds": view_seeds,
                "duplicate_mark_detected": duplicate_mark_detected,
            },
        )

    def _view_seed_specs(
        self,
        group: DetailRegionGroup,
        row_seeds: List[HeaderSeed],
    ) -> List[dict[str, Any]]:
        is_multiview = group.detail_type_hint == DETAIL_TYPE_MULTI_VIEW_SINGLE_BEAM or (
            group.duplicate_mark_detected
            and len(group.beam_marks) == 1
            and len(group.seeds) > 1
        )
        if not is_multiview:
            return []

        specs: List[dict[str, Any]] = []
        for seed in sorted(group.seeds, key=lambda s: s.x):
            seed_index = None
            for idx, row_seed in enumerate(row_seeds):
                if row_seed.beam_mark == seed.beam_mark and abs(row_seed.x - seed.x) < 1.0:
                    seed_index = idx
                    break
            if seed_index is None:
                view_box = {
                    "min_x": seed.x - 2000.0,
                    "max_x": seed.x + 2000.0,
                    "min_y": seed.y - self._detail_band_below_mm,
                    "max_y": seed.y + self._detail_band_above_mm,
                }
            else:
                view_box = dict(self._column_search_box(row_seeds, seed_index))
            specs.append(
                {
                    "beam_mark": seed.beam_mark,
                    "x": round(seed.x, 3),
                    "y": round(seed.y, 3),
                    "bbox": view_box,
                }
            )
        return specs

    def _group_continuity_score(self, group: DetailRegionGroup) -> float:
        if group.detail_type_hint == DETAIL_TYPE_MULTI_VIEW_SINGLE_BEAM:
            return 1.0
        if len(group.seeds) == 1:
            return 1.0
        if not group.continuity_links:
            return 0.0
        scores = [float(link.get("continuity_score", 0.0)) for link in group.continuity_links]
        relevant = [s for s in scores if s > 0]
        if not relevant:
            return 0.0
        return round(sum(relevant) / len(relevant), 4)

    def _group_geometry_score(self, group: DetailRegionGroup) -> float:
        if not group.continuity_links:
            return 1.0 if len(group.seeds) == 1 else 0.0
        overlaps = [
            float(link.get("geometry_overlap_ratio", 0.0)) for link in group.continuity_links
        ]
        return round(sum(overlaps) / len(overlaps), 4) if overlaps else 0.0

    def _shared_leader_score(
        self,
        group: DetailRegionGroup,
        leaders: List[dict[str, Any]],
        region_box: dict[str, float],
    ) -> float:
        if len(group.seeds) == 1:
            return 1.0
        xs = sorted(seed.x for seed in group.seeds)
        span = xs[-1] - xs[0]
        if span <= 0:
            return 0.0
        shared = 0
        total = 0
        for leader in leaders:
            start = leader.get("start", {})
            end = leader.get("end", {})
            sx, sy = start.get("x"), start.get("y")
            ex, ey = end.get("x"), end.get("y")
            if sx is None or sy is None:
                continue
            if not point_in_bbox(sx, sy, region_box):
                continue
            total += 1
            lx = min(sx, ex if ex is not None else sx)
            rx = max(sx, ex if ex is not None else sx)
            if rx - lx >= span * self._shared_leader_threshold:
                shared += 1
        if total == 0:
            return 0.0
        return round(shared / total, 4)

    def _shared_text_score(
        self,
        group: DetailRegionGroup,
        text_objects: List[dict[str, Any]],
        region_box: dict[str, float],
    ) -> float:
        texts = [
            text
            for text in text_objects
            if text.get("bbox") and point_in_bbox(*bbox_center(text["bbox"]), region_box)
        ]
        if not texts:
            return 0.0
        if len(group.seeds) == 1:
            return 1.0
        marks = set(group.beam_marks)
        matched = sum(
            1
            for text in texts
            if any(mark in str(text.get("text", "")).upper() for mark in marks)
        )
        return round(matched / len(texts), 4)

    def _count_in_bbox(
        self,
        items: List[dict[str, Any]],
        region_box: dict[str, float],
        point_key: str = "bbox",
    ) -> int:
        count = 0
        for item in items:
            if point_key == "bbox":
                box = item.get("bbox")
                if not box:
                    continue
                cx, cy = bbox_center(box)
            else:
                point = item.get(point_key, {})
                cx = point.get("x")
                cy = point.get("y")
                if cx is None or cy is None:
                    continue
            if point_in_bbox(cx, cy, region_box):
                count += 1
        return count
