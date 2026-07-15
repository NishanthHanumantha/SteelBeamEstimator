"""
General Notes Text Extractor.

Reads every TEXT and MTEXT entity from the General Notes DXF and returns a
normalised list of text items with their spatial coordinates and layer.
"""
from __future__ import annotations
import re
import pathlib
from typing import Any, Dict, List, Optional


def _strip_dxf_codes(raw: str) -> str:
    """Remove DXF formatting control codes and fix common encoding issues."""
    # Remove RTF-style codes: \\Axx; \\fFont;  \\Hxx.xx;  \\Cxxx;  etc.
    raw = re.sub(r"\\[A-Za-z][^;]*;", "", raw)
    # Remove %% escape sequences
    raw = re.sub(r"%%[A-Za-z]", "", raw)
    # Remove null bytes
    raw = raw.replace("\x00", "")
    # Collapse paragraph markers
    raw = re.sub(r"\\[Pp]", " | ", raw)
    raw = re.sub(r"\^[I]", "", raw)          # tab control code
    # Normalize whitespace
    raw = re.sub(r"[ \t]+", " ", raw)
    return raw.strip()


class DXFTextItem:
    """One text entity from the GN DXF."""
    __slots__ = ("text", "layer", "x", "y", "entity_type")

    def __init__(self, text: str, layer: str, x: float, y: float, entity_type: str):
        self.text = text
        self.layer = layer
        self.x = round(x, 2)
        self.y = round(y, 2)
        self.entity_type = entity_type

    def __repr__(self) -> str:
        return f"DXFTextItem(y={self.y:.1f} x={self.x:.1f} [{self.layer}] {self.text[:40]!r})"


class GeneralNotesTextExtractor:
    """
    Extracts and normalises all text from the General Notes DXF.

    Usage:
        extractor = GeneralNotesTextExtractor(path)
        items = extractor.extract()  # sorted top-to-bottom (desc y)
    """

    def __init__(self, gn_dxf_path: pathlib.Path):
        self._path = gn_dxf_path
        self._items: Optional[List[DXFTextItem]] = None

    def extract(self) -> List[DXFTextItem]:
        if self._items is not None:
            return self._items
        self._items = []
        try:
            import ezdxf
            doc = ezdxf.readfile(str(self._path))
            msp = doc.modelspace()
            for entity in msp:
                item = self._parse_entity(entity)
                if item:
                    self._items.append(item)
        except Exception as exc:
            print(f"[GNTextExtractor] DXF read error: {exc}")
        self._items.sort(key=lambda i: -i.y)
        return self._items

    def _parse_entity(self, entity: Any) -> Optional[DXFTextItem]:
        try:
            if entity.dxftype() == "TEXT":
                raw = entity.dxf.text
                x, y = entity.dxf.insert.x, entity.dxf.insert.y
                layer = entity.dxf.layer
                etype = "TEXT"
            elif entity.dxftype() == "MTEXT":
                raw = entity.plain_mtext() if hasattr(entity, "plain_mtext") else entity.text
                x, y = entity.dxf.insert.x, entity.dxf.insert.y
                layer = entity.dxf.layer
                etype = "MTEXT"
            else:
                return None

            cleaned = _strip_dxf_codes(raw)
            if not cleaned:
                return None
            return DXFTextItem(cleaned, layer, x, y, etype)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def items_in_x_range(
        self,
        x_min: float,
        x_max: float,
        items: Optional[List[DXFTextItem]] = None,
    ) -> List[DXFTextItem]:
        src = items or self.extract()
        return [i for i in src if x_min <= i.x <= x_max]

    def items_in_y_range(
        self,
        y_min: float,
        y_max: float,
        items: Optional[List[DXFTextItem]] = None,
    ) -> List[DXFTextItem]:
        src = items or self.extract()
        return [i for i in src if y_min <= i.y <= y_max]

    def items_in_region(
        self,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> List[DXFTextItem]:
        return [
            i for i in self.extract()
            if x_min <= i.x <= x_max and y_min <= i.y <= y_max
        ]

    def find_anchor(self, pattern: str) -> Optional[DXFTextItem]:
        """Find first item whose text matches the given regex pattern."""
        rx = re.compile(pattern, re.I)
        for item in self.extract():
            if rx.search(item.text):
                return item
        return None
