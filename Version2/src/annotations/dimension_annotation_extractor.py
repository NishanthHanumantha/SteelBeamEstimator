"""Phase D.1.7 — extract text from DIMENSION entities in reinforcement DXF files."""

from typing import List, TypedDict

from ezdxf.entities.dxfgfx import DXFGraphic
from loguru import logger

from src.parser.dxf_reader import DxfReader

_BLANK_OVERRIDE_VALUES = frozenset({"", "<>"})


class DimensionAnnotation(TypedDict):
    entity_type: str
    text: str
    raw_text: str
    x: float
    y: float
    layer: str


class DimensionAnnotationExtractor:
    """Load DIMENSION entities and resolve display text from override or measurement."""

    def extract_from_dxf(self, dxf_path: str) -> List[DimensionAnnotation]:
        doc = DxfReader(dxf_path).read()
        msp = doc.modelspace()
        records: List[DimensionAnnotation] = []

        for entity in msp.query("DIMENSION"):
            try:
                record = self._entity_to_record(entity)
                if record is not None:
                    records.append(record)
            except Exception as exc:
                handle = getattr(entity.dxf, "handle", "unknown")
                logger.warning(
                    "Skipped DIMENSION handle={}: {}", handle, exc
                )

        records.sort(key=lambda item: (-item["y"], item["x"], item["text"]))
        logger.info("Extracted {} DIMENSION annotation(s)", len(records))
        return records

    def _entity_to_record(self, entity: DXFGraphic) -> DimensionAnnotation | None:
        raw_text, normalized_text = self._resolve_text(entity)
        if not normalized_text:
            return None

        x, y = self._position(entity)
        return DimensionAnnotation(
            entity_type="DIMENSION",
            text=normalized_text,
            raw_text=raw_text,
            x=round(x, 1),
            y=round(y, 1),
            layer=str(entity.dxf.layer),
        )

    def _resolve_text(self, entity: DXFGraphic) -> tuple[str, str]:
        override = getattr(entity.dxf, "text", None)
        override_str = str(override).strip() if override is not None else ""

        if override_str and override_str not in _BLANK_OVERRIDE_VALUES:
            raw_text = override_str
            return raw_text, self._normalize_text(raw_text)

        measurement_text = self._measurement_text(entity)
        if measurement_text:
            return measurement_text, measurement_text

        return "", ""

    def _measurement_text(self, entity: DXFGraphic) -> str:
        measurement = getattr(entity.dxf, "actual_measurement", None)
        if measurement is not None:
            return self._format_measurement(float(measurement))

        if hasattr(entity, "get_measurement"):
            try:
                value = entity.get_measurement()
                if value is not None:
                    return self._format_measurement(float(value))
            except Exception:
                pass

        return ""

    @staticmethod
    def _format_measurement(value: float) -> str:
        if abs(value - round(value)) < 0.5:
            return str(int(round(value)))
        return str(round(value, 2))

    @staticmethod
    def _normalize_text(text: str) -> str:
        return text.replace("\\P", "").replace("\n", "").strip()

    @staticmethod
    def _position(entity: DXFGraphic) -> tuple[float, float]:
        if hasattr(entity.dxf, "text_midpoint"):
            point = entity.dxf.text_midpoint
            return float(point.x), float(point.y)
        if hasattr(entity.dxf, "defpoint"):
            point = entity.dxf.defpoint
            return float(point.x), float(point.y)
        return 0.0, 0.0
