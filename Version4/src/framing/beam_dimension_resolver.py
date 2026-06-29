"""Phase F.2 — Resolve engineering beam section dimensions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from loguru import logger

from src.framing.beam_centerline_extractor import BeamCenterlineRecord
from src.framing.beam_dimension_extractor import BeamDimensionExtractor, DimensionValue
from src.framing.beam_geometry import LineSegment
from src.framing.beam_section_parser import BeamSectionParser

SOURCE_LABEL = "LABEL"
SOURCE_ATTRIBUTE = "ATTRIBUTE"
SOURCE_PARALLEL_GEOMETRY = "PARALLEL_GEOMETRY"
SOURCE_GEOMETRY = "GEOMETRY"
SOURCE_UNKNOWN = "UNKNOWN"

CONF_LABEL = 1.0
CONF_ATTRIBUTE = 0.98
CONF_PARALLEL = 0.92
CONF_GEOMETRY = 0.85
CONF_UNKNOWN = 0.0


@dataclass
class ResolvedDimension:
    value: Optional[float]
    unit: str
    status: str
    source: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass
class ResolvedSection:
    designation: str
    width: ResolvedDimension
    depth: ResolvedDimension
    resolution_source: str
    confidence: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "designation": self.designation,
            "width": self.width.to_dict(),
            "depth": self.depth.to_dict(),
            "resolution_source": self.resolution_source,
            "confidence": self.confidence,
            "status": self.status,
        }


class BeamDimensionResolver:
    """Convert raw geometry and labels into reliable engineering beam sections."""

    def __init__(self, config: dict[str, Any]) -> None:
        dr = config.get("dimension_resolution", {})
        self._enabled = bool(dr.get("enable", True))
        self._use_label = bool(dr.get("use_label_dimensions", True))
        self._use_attribute = bool(dr.get("use_attribute_dimensions", True))
        self._use_parallel = bool(dr.get("use_parallel_edge_measurement", True))
        self._use_geometry = bool(dr.get("use_geometry_measurement", True))

        min_w = int(dr.get("minimum_reasonable_width", 100))
        max_w = int(dr.get("maximum_reasonable_width", 600))
        min_d = int(dr.get("minimum_reasonable_depth", 150))
        max_d = int(dr.get("maximum_reasonable_depth", 1500))

        self._section_parser = BeamSectionParser(min_w, max_w, min_d, max_d)
        self._geometry_extractor = BeamDimensionExtractor(self._geometry_config(config, dr))

        self._stats = {
            "resolved_from_labels": 0,
            "resolved_from_attributes": 0,
            "resolved_from_parallel_geometry": 0,
            "resolved_from_geometry": 0,
            "unknown_width": 0,
            "unknown_depth": 0,
        }

    @staticmethod
    def _geometry_config(root: dict[str, Any], dr: dict[str, Any]) -> dict[str, Any]:
        tol = float(dr.get("geometry_tolerance_mm", 20))
        return {
            **root,
            "parallel_width_min_mm": float(dr.get("minimum_reasonable_width", 100)) - tol,
            "parallel_width_max_mm": float(dr.get("maximum_reasonable_width", 600)) + tol,
            "orthogonal_tolerance_deg": root.get("orthogonal_tolerance_deg", 5.0),
        }

    def resolve_model(
        self,
        model: dict[str, Any],
        records: List[BeamCenterlineRecord],
        all_segments: List[LineSegment],
    ) -> dict[str, Any]:
        if not self._enabled:
            logger.info("Dimension resolution disabled in config")
            return model

        record_map = {r.beam_mark: r for r in records}
        beams = model.get("beams", [])

        for beam in beams:
            mark = beam.get("beam_mark", "")
            record = record_map.get(mark)
            f1_dims = beam.get("dimensions", {})
            raw_section = self._resolve_beam(beam, record, f1_dims, all_segments)
            beam["dimensions"] = {
                "section": raw_section.to_dict(),
                "f1_estimate": {
                    "width": f1_dims.get("width"),
                    "depth": f1_dims.get("depth"),
                },
            }

        model["phase"] = "Phase F.2"
        model["model_version"] = "1.1"
        model["dimension_resolution_summary"] = dict(self._stats)
        logger.info(
            "Dimension resolution — labels={}, attributes={}, parallel={}, geometry={}, "
            "unknown_width={}, unknown_depth={}",
            self._stats["resolved_from_labels"],
            self._stats["resolved_from_attributes"],
            self._stats["resolved_from_parallel_geometry"],
            self._stats["resolved_from_geometry"],
            self._stats["unknown_width"],
            self._stats["unknown_depth"],
        )
        return model

    def _resolve_beam(
        self,
        beam: dict[str, Any],
        record: Optional[BeamCenterlineRecord],
        f1_dims: dict[str, Any],
        all_segments: List[LineSegment],
    ) -> ResolvedSection:
        metadata = beam.get("metadata", {})
        label_text = metadata.get("label_text", "")

        width: Optional[ResolvedDimension] = None
        depth: Optional[ResolvedDimension] = None
        designation = "UNKNOWN"
        resolution_source = SOURCE_UNKNOWN
        confidence = CONF_UNKNOWN

        # Priority 1 — label designation
        if self._use_label and label_text:
            parsed = self._section_parser.parse(label_text)
            if parsed:
                width, depth = self._from_parsed(parsed)
                designation = parsed.designation
                resolution_source = SOURCE_LABEL
                confidence = CONF_LABEL
                self._stats["resolved_from_labels"] += 1

        # Priority 2 — attribute data
        if width is None or depth is None:
            attr_w, attr_d = self._attribute_dimensions(metadata, record)
            if self._use_attribute and (attr_w is not None or attr_d is not None):
                if width is None and attr_w is not None:
                    width = ResolvedDimension(
                        float(attr_w), "mm", "KNOWN", SOURCE_ATTRIBUTE, CONF_ATTRIBUTE
                    )
                if depth is None and attr_d is not None:
                    depth = ResolvedDimension(
                        float(attr_d), "mm", "KNOWN", SOURCE_ATTRIBUTE, CONF_ATTRIBUTE
                    )
                if width and depth and resolution_source == SOURCE_UNKNOWN:
                    designation = f"{int(width.value)}x{int(depth.value)}"
                    resolution_source = SOURCE_ATTRIBUTE
                    confidence = CONF_ATTRIBUTE
                    self._stats["resolved_from_attributes"] += 1

        # Priority 3 — parallel beam edges
        if record and (width is None or depth is None) and self._use_parallel:
            parallel = self._geometry_extractor.extract_width(record, all_segments)
            if parallel.status == "KNOWN" and parallel.value is not None:
                if width is None:
                    width = ResolvedDimension(
                        parallel.value, "mm", "KNOWN", SOURCE_PARALLEL_GEOMETRY, CONF_PARALLEL
                    )
                if resolution_source == SOURCE_UNKNOWN:
                    resolution_source = SOURCE_PARALLEL_GEOMETRY
                    confidence = CONF_PARALLEL
                    self._stats["resolved_from_parallel_geometry"] += 1

        # Priority 4 — existing F.1 geometry estimate
        if width is None and self._use_geometry:
            f1_w = f1_dims.get("width", {})
            if f1_w.get("status") == "KNOWN" and f1_w.get("value") is not None:
                width = ResolvedDimension(
                    float(f1_w["value"]),
                    "mm",
                    "KNOWN",
                    SOURCE_GEOMETRY,
                    CONF_GEOMETRY,
                )
                if resolution_source == SOURCE_UNKNOWN:
                    resolution_source = SOURCE_GEOMETRY
                    confidence = CONF_GEOMETRY
                    self._stats["resolved_from_geometry"] += 1

        if depth is None and self._use_geometry:
            f1_d = f1_dims.get("depth", {})
            if f1_d.get("status") == "KNOWN" and f1_d.get("value") is not None:
                depth = ResolvedDimension(
                    float(f1_d["value"]),
                    "mm",
                    "KNOWN",
                    SOURCE_GEOMETRY,
                    CONF_GEOMETRY,
                )
                if resolution_source == SOURCE_UNKNOWN:
                    resolution_source = SOURCE_GEOMETRY
                    confidence = CONF_GEOMETRY
                    if width and width.source == SOURCE_GEOMETRY:
                        self._stats["resolved_from_geometry"] += 1

        # Priority 5 — UNKNOWN
        if width is None:
            width = ResolvedDimension(None, "mm", "UNKNOWN", SOURCE_UNKNOWN, CONF_UNKNOWN)
            self._stats["unknown_width"] += 1
        if depth is None:
            depth = ResolvedDimension(None, "mm", "UNKNOWN", SOURCE_UNKNOWN, CONF_UNKNOWN)
            self._stats["unknown_depth"] += 1

        if designation == "UNKNOWN" and width.status == "KNOWN" and depth.status == "KNOWN":
            designation = f"{int(width.value)}x{int(depth.value)}"

        status = "KNOWN" if width.status == "KNOWN" and depth.status == "KNOWN" else "PARTIAL"
        if width.status == "UNKNOWN" and depth.status == "UNKNOWN":
            status = "UNKNOWN"

        return ResolvedSection(
            designation=designation,
            width=width,
            depth=depth,
            resolution_source=resolution_source,
            confidence=confidence,
            status=status,
        )

    def _from_parsed(self, parsed: Any) -> tuple[ResolvedDimension, ResolvedDimension]:
        return (
            ResolvedDimension(
                float(parsed.width), "mm", "KNOWN", SOURCE_LABEL, CONF_LABEL
            ),
            ResolvedDimension(
                float(parsed.depth), "mm", "KNOWN", SOURCE_LABEL, CONF_LABEL
            ),
        )

    def _attribute_dimensions(
        self,
        metadata: dict[str, Any],
        record: Optional[BeamCenterlineRecord],
    ) -> tuple[Optional[int], Optional[int]]:
        attr = metadata.get("attributes", {})
        if isinstance(attr, dict):
            w = attr.get("width_mm") or attr.get("WIDTH")
            d = attr.get("depth_mm") or attr.get("DEPTH")
            if w is not None or d is not None:
                return self._to_int(w), self._to_int(d)

        if record and record.metadata.get("attribute_width_mm"):
            return (
                self._to_int(record.metadata.get("attribute_width_mm")),
                self._to_int(record.metadata.get("attribute_depth_mm")),
            )
        return None, None

    @staticmethod
    def _to_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def build_resolved_export(self, model: dict[str, Any]) -> dict[str, Any]:
        beams = []
        for beam in model.get("beams", []):
            section = beam.get("dimensions", {}).get("section", {})
            beams.append(
                {
                    "beam_id": beam.get("beam_id"),
                    "beam_mark": beam.get("beam_mark"),
                    "section": section,
                }
            )
        return {
            "phase": "Phase F.2",
            "beam_count": len(beams),
            "beams": beams,
            "resolution_summary": model.get("dimension_resolution_summary", {}),
        }

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)
