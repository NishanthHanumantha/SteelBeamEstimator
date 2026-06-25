"""Phase D.1.7G — global DXF search for SFR-related text entities."""

import re
from typing import Any, Dict, List, Optional, Tuple

from ezdxf.document import Drawing
from ezdxf.entities.dxfgfx import DXFGraphic
from loguru import logger

from src.parser.dxf_reader import DxfReader

TEXT_BEARING_TYPES = frozenset(
    {"TEXT", "MTEXT", "ATTRIB", "ATTDEF", "DIMENSION", "LEADER", "MLEADER", "INSERT"}
)

SFR_SEARCH_TERMS: Tuple[str, ...] = (
    "S.F.R",
    "SFR",
    "SIDE FACE",
    "SIDEFACE",
    "SIDE.FACE",
    "FACE REINF",
    "FACE REINFORCEMENT",
    "ON BOTH FACE",
    "ON BOTH FACES",
    "2-Y8 ON ONE FACE",
    "CURVED BEAM",
    "CURVED BEAMS",
)

_SFR_CONTEXT_FOR_BAR = (
    "SIDE FACE",
    "SFR",
    "S F R",
    "FACE REINF",
    "FACE REINFORCEMENT",
    "ON BOTH FACE",
    "ON BOTH FACES",
)

_ENGINEERING_BAR = re.compile(r"\d+\s*-?\s*Y\d+", re.IGNORECASE)


class SfrDiscoveryScanner:
    """Scan entire reinforcement DXF without ownership or sketch constraints."""

    def scan(self, dxf_path: str) -> List[dict[str, Any]]:
        doc = DxfReader(dxf_path).read()
        msp = doc.modelspace()
        inventory: List[dict[str, Any]] = []
        entity_index = 0

        for entity, block_name, expanded_from in self._walk_modelspace(msp):
            record = self._entity_record(entity, block_name, expanded_from, entity_index)
            if record is None:
                continue
            if not self._matches_sfr_search(record["clean_text"]):
                continue
            inventory.append(record)
            entity_index += 1

        for block in doc.blocks:
            if block.name.startswith("*"):
                continue
            for entity in block.query("ATTDEF"):
                record = self._entity_record(entity, block.name, False, entity_index)
                if record is None:
                    continue
                if not self._matches_sfr_search(record["clean_text"]):
                    continue
                inventory.append(record)
                entity_index += 1

        logger.info("D.1.7G DXF scan: {} SFR candidate entities", len(inventory))
        return inventory

    def _walk_modelspace(self, msp: Any) -> List[Tuple[DXFGraphic, Optional[str], bool]]:
        collected: List[Tuple[DXFGraphic, Optional[str], bool]] = []
        for entity in msp:
            self._walk_entity(entity, None, False, collected)
        return collected

    def _walk_entity(
        self,
        entity: DXFGraphic,
        block_name: Optional[str],
        expanded_from: bool,
        out: List[Tuple[DXFGraphic, Optional[str], bool]],
    ) -> None:
        entity_type = entity.dxftype()
        if entity_type == "INSERT":
            insert_name = str(entity.dxf.name)
            try:
                for virtual in entity.virtual_entities():
                    self._walk_entity(virtual, insert_name, True, out)
            except Exception:
                out.append((entity, block_name or insert_name, expanded_from))
            return
        out.append((entity, block_name, expanded_from))

    def _entity_record(
        self,
        entity: DXFGraphic,
        block_name: Optional[str],
        expanded_from_insert: bool,
        index: int,
    ) -> Optional[dict[str, Any]]:
        entity_type = entity.dxftype()
        if entity_type not in TEXT_BEARING_TYPES:
            return None

        raw_text = self._extract_text(entity, entity_type)
        if not raw_text:
            return None

        clean_text = self._clean_text(raw_text)
        if not clean_text:
            return None

        x, y = self._extract_position(entity, entity_type)
        handle = str(getattr(entity.dxf, "handle", f"IDX_{index:05d}"))
        bbox = self._estimate_bbox(entity, entity_type, x, y)

        return {
            "entity_id": f"DXF_{handle}",
            "entity_type": entity_type,
            "layer": str(entity.dxf.layer),
            "block_name": block_name,
            "inside_block": block_name is not None,
            "expanded_from_insert": expanded_from_insert,
            "raw_text": raw_text,
            "clean_text": clean_text,
            "x": round(x, 2),
            "y": round(y, 2),
            "rotation": self._extract_rotation(entity, entity_type),
            "height": self._extract_height(entity, entity_type),
            "bounding_box": bbox,
        }

    def _matches_sfr_search(self, clean_text: str) -> bool:
        normalized = self._normalize_for_search(clean_text)
        for term in SFR_SEARCH_TERMS:
            if term in normalized:
                return True
        if _ENGINEERING_BAR.search(normalized):
            return any(ctx in normalized for ctx in _SFR_CONTEXT_FOR_BAR)
        return False

    @staticmethod
    def _normalize_for_search(text: str) -> str:
        value = text.upper().replace(".", " ").replace("\\P", " ")
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @staticmethod
    def _clean_text(text: str) -> str:
        value = text.replace("\\P", " ").replace("\n", " ")
        value = re.sub(r"\\A\d+;", "", value)
        value = re.sub(r"\\[A-Za-z][^;]*;", "", value)
        value = re.sub(r"\{[^}]*\}", "", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    def _extract_text(self, entity: DXFGraphic, entity_type: str) -> str:
        if entity_type == "TEXT":
            return str(entity.dxf.text).strip()
        if entity_type == "MTEXT":
            return str(entity.text).strip()
        if entity_type in ("ATTRIB", "ATTDEF"):
            return str(entity.dxf.text).strip()
        if entity_type == "DIMENSION":
            override = getattr(entity.dxf, "text", None)
            if override is not None and str(override).strip():
                return str(override).strip()
            measurement = getattr(entity.dxf, "actual_measurement", None)
            if measurement is not None:
                value = float(measurement)
                if abs(value - round(value)) < 0.5:
                    return str(int(round(value)))
                return str(round(value, 2))
        if entity_type in ("LEADER", "MLEADER"):
            for attr in ("text", "annotation_text"):
                value = getattr(entity.dxf, attr, None)
                if value is not None and str(value).strip():
                    return str(value).strip()
        return ""

    def _extract_position(self, entity: DXFGraphic, entity_type: str) -> Tuple[float, float]:
        if entity_type in ("TEXT", "MTEXT", "ATTRIB", "ATTDEF", "INSERT"):
            insert = entity.dxf.insert
            return float(insert.x), float(insert.y)
        if entity_type == "DIMENSION":
            if hasattr(entity.dxf, "text_midpoint"):
                point = entity.dxf.text_midpoint
                return float(point.x), float(point.y)
            if hasattr(entity.dxf, "defpoint"):
                point = entity.dxf.defpoint
                return float(point.x), float(point.y)
        if entity_type in ("LEADER", "MLEADER"):
            for attr in ("text_midpoint", "insert", "start"):
                if hasattr(entity.dxf, attr):
                    point = entity.dxf.get(attr)
                    return float(point.x), float(point.y)
        return 0.0, 0.0

    def _extract_rotation(self, entity: DXFGraphic, entity_type: str) -> Optional[float]:
        if hasattr(entity.dxf, "rotation"):
            return float(entity.dxf.rotation)
        if entity_type == "MTEXT" and hasattr(entity.dxf, "text_direction"):
            return None
        return None

    def _extract_height(self, entity: DXFGraphic, entity_type: str) -> Optional[float]:
        if hasattr(entity.dxf, "height"):
            return float(entity.dxf.height)
        if hasattr(entity.dxf, "char_height"):
            return float(entity.dxf.char_height)
        return None

    def _estimate_bbox(
        self, entity: DXFGraphic, entity_type: str, x: float, y: float
    ) -> dict[str, float]:
        height = self._extract_height(entity, entity_type) or 250.0
        width = height * 8.0
        return {
            "xmin": round(x, 2),
            "ymin": round(y, 2),
            "xmax": round(x + width, 2),
            "ymax": round(y + height, 2),
        }
