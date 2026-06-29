"""Assemble the BeamGeometryModel knowledge object."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

from src.framing.beam_centerline_extractor import BeamCenterlineRecord
from src.framing.beam_connectivity_builder import BeamConnectivityBuilder
from src.framing.beam_dimension_extractor import BeamDimensionExtractor, DimensionValue
from src.framing.beam_geometry import LineSegment
from src.framing.beam_support_detector import BeamSupportDetector

PHASE = "Phase F.1"
MODEL_VERSION = "1.0"


@dataclass
class BeamGeometryObject:
    beam_id: str
    beam_mark: str
    start_point: Optional[dict[str, float]]
    end_point: Optional[dict[str, float]]
    centerline: Optional[dict[str, Any]]
    length_mm: Optional[float]
    width: DimensionValue
    depth: DimensionValue
    orientation: Optional[str]
    bbox: Optional[dict[str, float]]
    layer: Optional[str]
    confidence: float
    entity_ids: List[str] = field(default_factory=list)
    connectivity: dict[str, Any] = field(default_factory=dict)
    supports: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "beam_id": self.beam_id,
            "beam_mark": self.beam_mark,
            "geometry": {
                "start_point": self.start_point,
                "end_point": self.end_point,
                "centerline": self.centerline,
                "length_mm": self.length_mm,
                "orientation": self.orientation,
                "bbox": self.bbox,
                "layer": self.layer,
                "confidence": self.confidence,
                "entity_ids": self.entity_ids,
            },
            "dimensions": {
                "width": self.width.to_dict(),
                "depth": self.depth.to_dict(),
            },
            "connectivity": self.connectivity,
            "supports": self.supports,
            "metadata": self.metadata,
        }


class BeamGeometryBuilder:
    """Build complete beam geometry models from extracted framing records."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._dimension_extractor = BeamDimensionExtractor(config)
        self._support_detector = BeamSupportDetector(config)
        self._connectivity_builder = BeamConnectivityBuilder()

    def build(
        self,
        records: List[BeamCenterlineRecord],
        all_segments: List[LineSegment],
        structural_context: dict[str, Any],
    ) -> dict[str, Any]:
        supports = []
        connectivity_graph = {"nodes": [], "edges": [], "adjacency": {}}
        if self._config.get("detect_supports", True):
            supports = self._support_detector.detect_supports(
                records, structural_context, all_segments
            )
        if self._config.get("detect_connectivity", True):
            connectivity_graph = self._connectivity_builder.build(records, supports)

        beams: List[BeamGeometryObject] = []
        for record in records:
            width = (
                self._dimension_extractor.extract_width(record, all_segments)
                if self._config.get("extract_dimensions", True)
                else DimensionValue(None, "mm", 0.0, "FRAMING_GEOMETRY", "UNKNOWN")
            )
            depth = (
                self._dimension_extractor.extract_depth(record)
                if self._config.get("extract_dimensions", True)
                else DimensionValue(None, "mm", 0.0, "FRAMING_LABEL", "UNKNOWN")
            )
            segment = record.segment
            centerline = segment.as_centerline_dict() if segment else None
            beam_supports = [s for s in supports if s.beam_id == record.beam_id]
            beam_edges = [
                edge
                for edge in connectivity_graph.get("edges", [])
                if edge.get("from_beam") == record.beam_id
            ]
            beams.append(
                BeamGeometryObject(
                    beam_id=record.beam_id,
                    beam_mark=record.beam_mark,
                    start_point=centerline["start_point"] if centerline else None,
                    end_point=centerline["end_point"] if centerline else None,
                    centerline=centerline,
                    length_mm=centerline["length_mm"] if centerline else None,
                    width=width,
                    depth=depth,
                    orientation=centerline["orientation"] if centerline else None,
                    bbox=segment.bbox if segment else None,
                    layer=segment.layer if segment else record.label.layer,
                    confidence=record.confidence,
                    entity_ids=record.entity_ids,
                    connectivity={"edges": beam_edges},
                    supports={
                        "left": self._support_by_end(beam_supports, "start"),
                        "right": self._support_by_end(beam_supports, "end"),
                        "records": [item.to_dict() for item in beam_supports],
                    },
                    metadata={
                        **record.metadata,
                        "label_text": record.label.label_text,
                        "label_position": {
                            "x": record.label.x,
                            "y": record.label.y,
                        },
                    },
                )
            )

        return {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "creation_timestamp": datetime.now(timezone.utc).isoformat(),
            "beam_count": len(beams),
            "beams": [beam.to_dict() for beam in beams],
            "connectivity_graph": connectivity_graph,
            "supports": [support.to_dict() for support in supports],
        }

    @staticmethod
    def _support_by_end(
        supports: List[Any], end_name: str
    ) -> Optional[dict[str, Any]]:
        for support in supports:
            if support.end == end_name:
                return support.to_dict()
        return None

    def split_outputs(self, model: dict[str, Any]) -> dict[str, Any]:
        beams = model.get("beams", [])
        return {
            "beam_geometry_model": model,
            "beam_centerlines": [
                {
                    "beam_id": beam["beam_id"],
                    "beam_mark": beam["beam_mark"],
                    **beam.get("geometry", {}),
                }
                for beam in beams
            ],
            "beam_dimensions": [
                {
                    "beam_id": beam["beam_id"],
                    "beam_mark": beam["beam_mark"],
                    **beam.get("dimensions", {}),
                }
                for beam in beams
            ],
            "beam_connectivity": model.get("connectivity_graph", {}),
            "beam_supports": model.get("supports", []),
        }
