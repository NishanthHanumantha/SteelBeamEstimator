"""Entity extraction from ezdxf modelspace."""

from typing import Any, List, Optional, Tuple, TypedDict

from ezdxf.entities.dxfgfx import DXFGraphic
from loguru import logger

from src.utils.text_cleaner import TextCleaner

_TEXT_ENTITY_TYPES = frozenset({"TEXT", "MTEXT", "ATTRIB"})


class ExtractedEntity(TypedDict):
    """Normalized entity record for downstream steel-beam processing."""

    entity_type: str
    layer: str
    text: str
    raw_text: str
    clean_text: str
    handle: str
    x: float
    y: float


# Entity types requested for steel beam DXF extraction.
TARGET_ENTITY_TYPES: Tuple[str, ...] = (
    "TEXT",
    "MTEXT",
    "INSERT",
    "ATTRIB",
    "LINE",
    "LWPOLYLINE",
    "POLYLINE",
    "DIMENSION",
)

_QUERY_STRING = " ".join(TARGET_ENTITY_TYPES)


class EntityExtractor:
    """Extracts supported DXF entities from modelspace into normalized dicts."""

    def __init__(self, text_cleaner: Optional[TextCleaner] = None) -> None:
        self._text_cleaner = text_cleaner or TextCleaner()

    def extract(self, modelspace: Any) -> List[ExtractedEntity]:
        """
        Walk modelspace and return all supported entities.

        Args:
            modelspace: ezdxf layout object (typically doc.modelspace()).

        Returns:
            List of normalized entity dictionaries.
        """
        if modelspace is None:
            logger.error("Modelspace is None — nothing to extract")
            return []

        entities: List[ExtractedEntity] = []
        query = modelspace.query(_QUERY_STRING)

        logger.info("Scanning modelspace for entity types: {}", _QUERY_STRING)

        for entity in query:
            try:
                record = self._extract_entity(entity)
                if record is not None:
                    entities.append(record)
            except Exception as exc:
                handle = getattr(entity.dxf, "handle", "unknown")
                logger.warning(
                    "Skipped entity handle={} type={}: {}",
                    handle,
                    entity.dxftype(),
                    exc,
                )

        logger.info("Extracted {} entities from modelspace", len(entities))
        return entities

    def _extract_entity(self, entity: DXFGraphic) -> Optional[ExtractedEntity]:
        entity_type = entity.dxftype()
        if entity_type not in TARGET_ENTITY_TYPES:
            return None

        x, y = self._get_position(entity, entity_type)
        raw_text, clean_text = self._resolve_text_fields(entity, entity_type)

        return ExtractedEntity(
            entity_type=entity_type,
            layer=str(entity.dxf.layer),
            text=clean_text,
            raw_text=raw_text,
            clean_text=clean_text,
            handle=str(entity.dxf.handle),
            x=round(x, 6),
            y=round(y, 6),
        )

    def _resolve_text_fields(
        self, entity: DXFGraphic, entity_type: str
    ) -> Tuple[str, str]:
        """Return raw and cleaned text; cleaning runs before beam extraction."""
        if entity_type in _TEXT_ENTITY_TYPES:
            raw_text = self._get_raw_text(entity, entity_type)
            clean_text = self._text_cleaner.clean(raw_text)
            return raw_text, clean_text

        display_text = self._get_display_text(entity, entity_type)
        return display_text, display_text

    def _get_position(self, entity: DXFGraphic, entity_type: str) -> Tuple[float, float]:
        if entity_type in ("TEXT", "MTEXT", "INSERT", "ATTRIB"):
            insert = entity.dxf.insert
            return float(insert.x), float(insert.y)

        if entity_type == "LINE":
            start = entity.dxf.start
            return float(start.x), float(start.y)

        if entity_type == "LWPOLYLINE":
            return self._first_polyline_point(entity)

        if entity_type == "POLYLINE":
            return self._first_polyline_vertex(entity)

        if entity_type == "DIMENSION":
            return self._dimension_position(entity)

        logger.debug("No position rule for entity type {}", entity_type)
        return 0.0, 0.0

    def _first_polyline_point(self, entity: DXFGraphic) -> Tuple[float, float]:
        points = list(entity.get_points(format="xy"))
        if points:
            return float(points[0][0]), float(points[0][1])
        return 0.0, 0.0

    def _first_polyline_vertex(self, entity: DXFGraphic) -> Tuple[float, float]:
        vertices = entity.vertices
        if vertices:
            location = vertices[0].dxf.location
            return float(location.x), float(location.y)
        return 0.0, 0.0

    def _dimension_position(self, entity: DXFGraphic) -> Tuple[float, float]:
        if hasattr(entity.dxf, "text_midpoint"):
            point = entity.dxf.text_midpoint
            return float(point.x), float(point.y)
        if hasattr(entity.dxf, "defpoint"):
            point = entity.dxf.defpoint
            return float(point.x), float(point.y)
        return 0.0, 0.0

    def _get_raw_text(self, entity: DXFGraphic, entity_type: str) -> str:
        if entity_type == "TEXT":
            return str(entity.dxf.text).strip()

        if entity_type == "MTEXT":
            return str(entity.text).strip()

        if entity_type == "ATTRIB":
            return str(entity.dxf.text).strip()

        return ""

    def _get_display_text(self, entity: DXFGraphic, entity_type: str) -> str:
        if entity_type == "INSERT":
            return str(entity.dxf.name).strip()

        if entity_type == "DIMENSION":
            return self._dimension_text(entity)

        return ""

    def _dimension_text(self, entity: DXFGraphic) -> str:
        override = getattr(entity.dxf, "text", None)
        if override:
            return str(override).strip()

        if hasattr(entity, "get_measurement"):
            try:
                measurement = entity.get_measurement()
                if measurement is not None:
                    return str(measurement).strip()
            except Exception:
                pass

        return ""
