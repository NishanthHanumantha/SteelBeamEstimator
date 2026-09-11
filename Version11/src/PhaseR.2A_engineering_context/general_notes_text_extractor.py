"""
General Notes Text Extractor — MODEL_VERSION 7.5.3

Reads every TEXT, MTEXT, ATTRIB, ATTDEF from the General Notes DXF including
all content inside INSERT blocks (recursively expanded via virtual_entities).

Public interface unchanged: extract() returns List[DXFTextItem].
"""
from __future__ import annotations
import re
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


def _strip_dxf_codes(raw: str) -> str:
    """Remove DXF formatting control codes and fix common encoding issues."""
    raw = re.sub(r"\\[A-Za-z][^;]*;", "", raw)
    raw = re.sub(r"%%[A-Za-z]", "", raw)
    raw = raw.replace("\x00", "")
    raw = re.sub(r"\\[Pp]", " | ", raw)
    raw = re.sub(r"\^[I]", "", raw)
    raw = re.sub(r"[ \t]+", " ", raw)
    return raw.strip()


class DXFTextItem:
    """One text entity from the GN DXF (public interface — unchanged)."""
    __slots__ = ("text", "layer", "x", "y", "entity_type")

    def __init__(self, text: str, layer: str, x: float, y: float, entity_type: str):
        self.text = text
        self.layer = layer
        self.x = round(x, 2)
        self.y = round(y, 2)
        self.entity_type = entity_type

    def __repr__(self) -> str:
        return f"DXFTextItem(y={self.y:.1f} x={self.x:.1f} [{self.layer}] {self.text[:40]!r})"


@dataclass
class ExtractionRecord:
    """Full engineering entity inventory record (internal / export use)."""
    entity_id: str
    text: str
    layer: str
    x: float
    y: float
    entity_type: str
    parent_block: str
    nesting_depth: int
    rotation: Optional[float]
    source: str          # TOP_LEVEL | BLOCK | NESTED_BLOCK
    block_path: str = ""


# Text-bearing DXF entity types
_TEXT_TYPES = frozenset({"TEXT", "MTEXT", "ATTRIB", "ATTDEF"})


class GeneralNotesTextExtractor:
    """
    Extracts and normalises all text from the General Notes DXF.

    Expands INSERT blocks recursively using ezdxf virtual_entities() so that
    nested engineering tables (e.g. LD FOR FY-550 inside block A$C15514357)
    appear in world coordinates exactly as AutoCAD displays them.

    Usage:
        extractor = GeneralNotesTextExtractor(path)
        items = extractor.extract()              # List[DXFTextItem] — unchanged API
        inventory = extractor.extract_inventory() # full metadata for audit exports
    """

    def __init__(self, gn_dxf_path: pathlib.Path):
        self._path = gn_dxf_path
        self._items: Optional[List[DXFTextItem]] = None
        self._inventory: Optional[List[ExtractionRecord]] = None
        self._expansion_report: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API (unchanged)
    # ------------------------------------------------------------------

    def extract(self) -> List[DXFTextItem]:
        if self._items is not None:
            return self._items
        self._run_extraction()
        return self._items

    def extract_inventory(self) -> List[ExtractionRecord]:
        if self._inventory is None:
            self._run_extraction()
        return list(self._inventory)

    def get_expansion_report(self) -> Dict[str, Any]:
        if not self._expansion_report:
            self._run_extraction()
        return dict(self._expansion_report)

    def get_block_hierarchy(self) -> Dict[str, Any]:
        if not self._expansion_report:
            self._run_extraction()
        return self._expansion_report.get("block_hierarchy", {})

    # ------------------------------------------------------------------
    # Core extraction engine
    # ------------------------------------------------------------------

    def _run_extraction(self) -> None:
        self._items = []
        self._inventory = []
        self._expansion_report = {
            "top_level_entities": 0,
            "insert_blocks_expanded": 0,
            "nested_inserts_expanded": 0,
            "virtual_entities_extracted": 0,
            "recursion_guards_triggered": 0,
            "duplicates_skipped": 0,
            "block_hierarchy": {"inserts": [], "nested_paths": []},
        }

        seen_keys: Set[Tuple] = set()
        block_hierarchy_inserts: List[Dict] = []

        try:
            import ezdxf
            doc = ezdxf.readfile(str(self._path))
            msp = doc.modelspace()

            for entity in msp:
                self._expansion_report["top_level_entities"] += 1
                dt = entity.dxftype()

                if dt in _TEXT_TYPES:
                    rec = self._parse_text_entity(
                        entity, depth=0, parent_block="",
                        source="TOP_LEVEL", block_path="",
                    )
                    if rec and self._register(rec, seen_keys):
                        self._append_record(rec)

                elif dt == "INSERT":
                    insert_info = {
                        "block_name": entity.dxf.name,
                        "insert_x": round(entity.dxf.insert.x, 4),
                        "insert_y": round(entity.dxf.insert.y, 4),
                        "xscale": round(float(entity.dxf.xscale), 6),
                        "yscale": round(float(entity.dxf.yscale), 6),
                        "rotation": round(float(entity.dxf.rotation), 4),
                        "layer": entity.dxf.layer,
                        "handle": entity.dxf.handle,
                    }
                    block_hierarchy_inserts.append(insert_info)
                    self._expansion_report["insert_blocks_expanded"] += 1

                    visited: Set[str] = set()
                    self._expand_insert(
                        entity,
                        depth=1,
                        parent_block=entity.dxf.name,
                        block_path=entity.dxf.name,
                        seen_keys=seen_keys,
                        visited_inserts=visited,
                        block_hierarchy_inserts=block_hierarchy_inserts,
                    )

        except Exception as exc:
            print(f"[GNTextExtractor] DXF read error: {exc}")
            self._expansion_report["error"] = str(exc)

        self._expansion_report["block_hierarchy"]["inserts"] = block_hierarchy_inserts
        self._items.sort(key=lambda i: -i.y)

    def _expand_insert(
        self,
        insert_entity: Any,
        depth: int,
        parent_block: str,
        block_path: str,
        seen_keys: Set[Tuple],
        visited_inserts: Set[str],
        block_hierarchy_inserts: List[Dict],
    ) -> None:
        """
        Expand an INSERT using ezdxf virtual_entities() for world-coordinate
        transformation (rotation, scale, mirror, translation applied).
        Guard against circular block references via visited_inserts registry.
        """
        guard_key = f"{insert_entity.dxf.handle}:{insert_entity.dxf.name}:{depth}"
        if guard_key in visited_inserts:
            self._expansion_report["recursion_guards_triggered"] += 1
            return
        visited_inserts.add(guard_key)

        try:
            virtuals = list(insert_entity.virtual_entities())
        except Exception:
            virtuals = []

        for ve in virtuals:
            self._expansion_report["virtual_entities_extracted"] += 1
            vtype = ve.dxftype()

            if vtype in _TEXT_TYPES:
                source = "NESTED_BLOCK" if depth > 1 else "BLOCK"
                rec = self._parse_text_entity(
                    ve, depth=depth, parent_block=parent_block,
                    source=source, block_path=block_path,
                )
                if rec and self._register(rec, seen_keys):
                    self._append_record(rec)

            elif vtype == "INSERT":
                self._expansion_report["nested_inserts_expanded"] += 1
                nested_path = f"{block_path}>{ve.dxf.name}"
                nested_info = {
                    "block_name": ve.dxf.name,
                    "parent_block": parent_block,
                    "nesting_depth": depth + 1,
                    "block_path": nested_path,
                    "insert_x": round(ve.dxf.insert.x, 4),
                    "insert_y": round(ve.dxf.insert.y, 4),
                }
                block_hierarchy_inserts.append(nested_info)
                self._expansion_report["block_hierarchy"]["nested_paths"].append(nested_path)

                self._expand_insert(
                    ve,
                    depth=depth + 1,
                    parent_block=ve.dxf.name,
                    block_path=nested_path,
                    seen_keys=seen_keys,
                    visited_inserts=visited_inserts,
                    block_hierarchy_inserts=block_hierarchy_inserts,
                )

    def _parse_text_entity(
        self,
        entity: Any,
        depth: int,
        parent_block: str,
        source: str,
        block_path: str,
    ) -> Optional[ExtractionRecord]:
        try:
            etype = entity.dxftype()
            if etype == "TEXT":
                raw = entity.dxf.text
            elif etype == "MTEXT":
                raw = entity.plain_mtext() if hasattr(entity, "plain_mtext") else entity.text
            elif etype in ("ATTRIB", "ATTDEF"):
                raw = entity.dxf.text
            else:
                return None

            cleaned = _strip_dxf_codes(raw)
            if not cleaned:
                return None

            x = round(entity.dxf.insert.x, 4)
            y = round(entity.dxf.insert.y, 4)
            layer = entity.dxf.layer
            rotation = None
            try:
                rotation = round(float(entity.dxf.rotation), 4)
            except Exception:
                pass

            handle = ""
            try:
                handle = entity.dxf.handle or ""
            except Exception:
                pass

            entity_id = handle or f"{source}:{block_path}:{x}:{y}:{cleaned[:20]}"

            return ExtractionRecord(
                entity_id=entity_id,
                text=cleaned,
                layer=layer,
                x=x,
                y=y,
                entity_type=etype,
                parent_block=parent_block,
                nesting_depth=depth,
                rotation=rotation,
                source=source,
                block_path=block_path,
            )
        except Exception:
            return None

    def _register(self, rec: ExtractionRecord, seen_keys: Set[Tuple]) -> bool:
        """Deduplicate by world position + text + layer."""
        key = (round(rec.x, 2), round(rec.y, 2), rec.text[:80], rec.layer)
        if key in seen_keys:
            self._expansion_report["duplicates_skipped"] += 1
            return False
        seen_keys.add(key)
        return True

    def _append_record(self, rec: ExtractionRecord) -> None:
        self._inventory.append(rec)
        self._items.append(
            DXFTextItem(rec.text, rec.layer, rec.x, rec.y, rec.entity_type)
        )

    # ------------------------------------------------------------------
    # Convenience helpers (unchanged signatures)
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

    def find_table_title(self, n: int) -> Optional[DXFTextItem]:
        """Prefer a short 'TABLE n' label over a notes paragraph that mentions it."""
        exact = re.compile(rf"^\s*TABLE\s*[-:]?\s*{n}\s*$", re.I)
        mentioned = re.compile(rf"TABLE\s*[-:]?\s*{n}\b", re.I)
        short: Optional[DXFTextItem] = None
        for item in self.extract():
            t = item.text.strip()
            if exact.match(t):
                return item
            if short is None and len(t) <= 24 and mentioned.search(t):
                short = item
        return short
