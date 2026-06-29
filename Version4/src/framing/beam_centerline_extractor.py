"""Extract beam centreline geometry from framing plan DXF."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from ezdxf.entities.dxfgfx import DXFGraphic
from loguru import logger

from src.extractor.beam_label_extractor import BEAM_LABEL_PATTERN
from src.framing.beam_geometry import LineSegment, assign_segments_greedy, beam_mark_sort_key
from src.parser.dxf_flattener import flatten_entities
from src.parser.dxf_reader import DxfReader
from src.utils.text_cleaner import TextCleaner

_TEXT_TYPES = frozenset({"TEXT", "MTEXT", "ATTRIB"})
_LINE_TYPES = frozenset({"LINE", "LWPOLYLINE", "POLYLINE", "ARC"})


@dataclass
class BeamLabelRecord:
    beam_mark: str
    label_text: str
    width_mm: int
    depth_mm: int
    x: float
    y: float
    layer: str
    handle: str
    source_file: str
    layout: str = "Model"


@dataclass
class BeamCenterlineRecord:
    beam_id: str
    beam_mark: str
    segment: Optional[LineSegment]
    label: BeamLabelRecord
    confidence: float = 1.0
    entity_ids: List[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BeamCenterlineExtractor:
    """Detect beam labels and assign framing-plan centreline segments."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._cleaner = TextCleaner()
        self._beam_layers = set(self._layer_list(config.get("beam_line_layers", ["STR-BEAM"])))
        self._label_layers = set(self._layer_list(config.get("beam_label_layers", ["S-BEAM-IDEN"])))
        self._min_segment = float(config.get("min_beam_segment_mm", 500.0))
        self._max_label_distance = float(
            config.get("max_label_segment_distance_mm", 3000.0)
        )

    def extract_from_dxf(self, dxf_path: Path, layout_name: str = "Model") -> List[BeamCenterlineRecord]:
        reader = DxfReader(dxf_path)
        doc = reader.read()
        if layout_name == "Model":
            layout = reader.get_modelspace(doc)
        else:
            layout = doc.layouts.get(layout_name)
        if layout is None:
            logger.warning("Layout {} not found in {}", layout_name, dxf_path.name)
            return []

        flat = flatten_entities(layout)
        labels = self._extract_labels(flat, dxf_path, layout_name)
        segments = self._extract_beam_segments(flat)
        logger.info(
            "{}: {} label(s), {} beam segment(s) in {}",
            dxf_path.name,
            len(labels),
            len(segments),
            layout_name,
        )

        assignments = assign_segments_greedy(
            [(label.beam_mark, label.x, label.y) for label in labels],
            segments,
            self._max_label_distance,
        )

        records: List[BeamCenterlineRecord] = []
        for label in labels:
            segment = assignments.get(label.beam_mark)
            confidence = 1.0 if segment is not None else 0.4
            entity_ids = [label.handle]
            if segment is not None:
                entity_ids.append(segment.handle)
            records.append(
                BeamCenterlineRecord(
                    beam_id=label.beam_mark,
                    beam_mark=label.beam_mark,
                    segment=segment,
                    label=label,
                    confidence=confidence,
                    entity_ids=entity_ids,
                    metadata={
                        "source_file": str(dxf_path),
                        "layout": layout_name,
                        "label_layer": label.layer,
                    },
                )
            )
            if segment is None:
                logger.warning(
                    "No centreline matched for {} at ({}, {})",
                    label.beam_mark,
                    label.x,
                    label.y,
                )

        records.sort(key=lambda item: beam_mark_sort_key(item.beam_mark))
        return records

    def extract_from_directory(self, framing_dir: Path) -> List[BeamCenterlineRecord]:
        records: List[BeamCenterlineRecord] = []
        for dxf_path in sorted(framing_dir.glob("*.dxf")):
            layout_records = self.extract_from_dxf(dxf_path, layout_name="Model")
            records.extend(layout_records)
        return self._dedupe_records(records)

    def extract_all_segments_from_directory(self, framing_dir: Path) -> List[LineSegment]:
        segments: List[LineSegment] = []
        for dxf_path in sorted(framing_dir.glob("*.dxf")):
            reader = DxfReader(dxf_path)
            doc = reader.read()
            layout = reader.get_modelspace(doc)
            if layout is None:
                continue
            segments.extend(self._extract_beam_segments(flatten_entities(layout)))
        return segments

    def _dedupe_records(self, records: List[BeamCenterlineRecord]) -> List[BeamCenterlineRecord]:
        by_mark: dict[str, BeamCenterlineRecord] = {}
        for record in records:
            existing = by_mark.get(record.beam_mark)
            if existing is None:
                by_mark[record.beam_mark] = record
                continue
            if existing.segment is None and record.segment is not None:
                by_mark[record.beam_mark] = record
        return sorted(by_mark.values(), key=lambda item: beam_mark_sort_key(item.beam_mark))

    def _extract_labels(
        self,
        entities: List[DXFGraphic],
        dxf_path: Path,
        layout_name: str,
    ) -> List[BeamLabelRecord]:
        labels: List[BeamLabelRecord] = []
        seen_marks: set[str] = set()
        for entity in entities:
            if entity.dxftype() not in _TEXT_TYPES:
                continue
            layer = str(entity.dxf.layer)
            if self._label_layers and layer not in self._label_layers:
                continue
            text = self._entity_text(entity).strip()
            match = BEAM_LABEL_PATTERN.match(text)
            if not match:
                continue
            mark = match.group(1).upper()
            if mark in seen_marks:
                continue
            seen_marks.add(mark)
            insert = entity.dxf.insert
            labels.append(
                BeamLabelRecord(
                    beam_mark=mark,
                    label_text=text,
                    width_mm=int(match.group(2)),
                    depth_mm=int(match.group(3)),
                    x=float(insert.x),
                    y=float(insert.y),
                    layer=layer,
                    handle=str(getattr(entity.dxf, "handle", "") or f"{entity.dxftype()}_{id(entity)}"),
                    source_file=str(dxf_path),
                    layout=layout_name,
                )
            )
        return labels

    def _extract_beam_segments(self, entities: List[DXFGraphic]) -> List[LineSegment]:
        segments: List[LineSegment] = []
        for entity in entities:
            entity_type = entity.dxftype()
            layer = str(entity.dxf.layer)
            if layer not in self._beam_layers:
                continue
            handle = str(getattr(entity.dxf, "handle", "") or f"{entity.dxftype()}_{id(entity)}")
            if entity_type == "LINE":
                start = entity.dxf.start
                end = entity.dxf.end
                segment = LineSegment(
                    x1=float(start.x),
                    y1=float(start.y),
                    x2=float(end.x),
                    y2=float(end.y),
                    layer=layer,
                    handle=handle,
                    entity_ids=(handle,),
                )
                if segment.length_mm >= self._min_segment:
                    segments.append(segment)
            elif entity_type == "ARC":
                segments.extend(self._arc_segments(entity, layer, handle))
            elif entity_type in ("LWPOLYLINE", "POLYLINE"):
                segments.extend(self._polyline_segments(entity, layer, handle))
        return segments

    def _polyline_segments(
        self, entity: DXFGraphic, layer: str, handle: str
    ) -> List[LineSegment]:
        segments: List[LineSegment] = []
        if entity.dxftype() == "LWPOLYLINE":
            points = [(float(x), float(y)) for x, y in entity.get_points(format="xy")]
        else:
            points = [
                (float(v.dxf.location.x), float(v.dxf.location.y))
                for v in entity.vertices
            ]
        for index in range(len(points) - 1):
            x1, y1 = points[index]
            x2, y2 = points[index + 1]
            segment = LineSegment(
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                layer=layer,
                handle=handle,
                entity_ids=(handle,),
            )
            if segment.length_mm >= self._min_segment:
                segments.append(segment)
        return segments

    def _arc_segments(
        self, entity: DXFGraphic, layer: str, handle: str
    ) -> List[LineSegment]:
        """Approximate arc as chord for centreline extraction."""
        center = entity.dxf.center
        radius = float(entity.dxf.radius)
        start_angle = math.radians(float(entity.dxf.start_angle))
        end_angle = math.radians(float(entity.dxf.end_angle))
        x1 = float(center.x) + radius * math.cos(start_angle)
        y1 = float(center.y) + radius * math.sin(start_angle)
        x2 = float(center.x) + radius * math.cos(end_angle)
        y2 = float(center.y) + radius * math.sin(end_angle)
        segment = LineSegment(
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            layer=layer,
            handle=handle,
            entity_ids=(handle,),
        )
        return [segment] if segment.length_mm >= self._min_segment else []

    def _entity_text(self, entity: DXFGraphic) -> str:
        if entity.dxftype() == "MTEXT":
            return self._cleaner.clean(str(entity.text))
        return self._cleaner.clean(str(entity.dxf.text))

    @staticmethod
    def _layer_list(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            if "," in value:
                return [part.strip() for part in value.split(",") if part.strip()]
            return [value.strip()]
        return []
