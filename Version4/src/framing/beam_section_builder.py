"""Build BeamSection engineering objects from resolved dimensions."""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

from src.framing.beam_section_model import (
    CLASS_UNKNOWN,
    SHAPE_RECTANGULAR,
    SHAPE_UNKNOWN,
    BeamSection,
    DimensionProperty,
    MetricValue,
)


class BeamSectionBuilder:
    """Promote F.2 resolved dimensions into permanent BeamSection objects."""

    def __init__(self, config: dict[str, Any]) -> None:
        sb = config.get("beam_section", {})
        self._enabled = bool(sb.get("enable", True))
        self._deep_ratio = float(sb.get("deep_section_ratio", 2.0))
        self._stats: Dict[str, int] = {
            "rectangular_sections": 0,
            "deep_sections": 0,
            "normal_sections": 0,
            "unknown_sections": 0,
        }

    def build_model(self, model: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            logger.info("BeamSection builder disabled in config")
            return model

        sections_export: List[dict[str, Any]] = []

        for beam in model.get("beams", []):
            section = self._build_section(beam)
            beam["beam_section"] = section.to_dict()
            sections_export.append(
                {
                    "beam_id": beam["beam_id"],
                    "beam_mark": beam["beam_mark"],
                    "section": section.to_dict(),
                }
            )
            self._count_section(section)

        model["beam_sections"] = sections_export
        model["beam_section_summary"] = dict(self._stats)
        logger.info(
            "BeamSection built — rectangular={}, deep={}, normal={}, unknown={}",
            self._stats["rectangular_sections"],
            self._stats["deep_sections"],
            self._stats["normal_sections"],
            self._stats["unknown_sections"],
        )
        return model

    def _build_section(self, beam: dict[str, Any]) -> BeamSection:
        resolved = beam.get("dimensions", {}).get("section", {})
        geometry = beam.get("geometry", {})

        designation = resolved.get("designation", "UNKNOWN")
        width_dim = resolved.get("width", {})
        depth_dim = resolved.get("depth", {})

        width_val = width_dim.get("value")
        depth_val = depth_dim.get("value")
        width_known = width_dim.get("status") == "KNOWN" and width_val is not None
        depth_known = depth_dim.get("status") == "KNOWN" and depth_val is not None

        source = resolved.get("resolution_source", "UNKNOWN")
        confidence = float(resolved.get("confidence", 0.0))

        if width_known and depth_known:
            shape = SHAPE_RECTANGULAR
            w = float(width_val)
            d = float(depth_val)
            area = w * d
            perimeter = 2.0 * (w + d)
            aspect = d / w if w > 0 else None
            classification = (
                BeamSection.classify_section(d, w)
                if aspect is not None
                else CLASS_UNKNOWN
            )
            if aspect is not None and aspect >= self._deep_ratio:
                classification = "DEEP_SECTION"
            elif aspect is not None:
                classification = "NORMAL_SECTION"
        else:
            shape = SHAPE_UNKNOWN
            area = None
            perimeter = None
            aspect = None
            classification = CLASS_UNKNOWN
            w = float(width_val) if width_val is not None else None
            d = float(depth_val) if depth_val is not None else None

        return BeamSection(
            designation=designation,
            shape=shape,
            classification=classification,
            width=DimensionProperty(
                value=w,
                unit="mm",
                source=width_dim.get("source", source),
                confidence=float(width_dim.get("confidence", confidence)),
            ),
            depth=DimensionProperty(
                value=d,
                unit="mm",
                source=depth_dim.get("source", source),
                confidence=float(depth_dim.get("confidence", confidence)),
            ),
            cross_section_area=MetricValue(value=area, unit="mm²"),
            perimeter=MetricValue(value=perimeter, unit="mm"),
            aspect_ratio=MetricValue(value=aspect, unit="ratio"),
            orientation=BeamSection.map_orientation(geometry.get("orientation")),
            source=source,
            confidence=confidence,
        )

    def _count_section(self, section: BeamSection) -> None:
        if section.shape == SHAPE_RECTANGULAR:
            self._stats["rectangular_sections"] += 1
        else:
            self._stats["unknown_sections"] += 1
            return
        if section.classification == "DEEP_SECTION":
            self._stats["deep_sections"] += 1
        elif section.classification == "NORMAL_SECTION":
            self._stats["normal_sections"] += 1

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)
