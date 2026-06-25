"""Phase D.1.6B — survey all text-bearing DXF entity types in reinforcement drawings."""

import re
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

from ezdxf.document import Drawing
from ezdxf.entities.dxfgfx import DXFGraphic
from loguru import logger

from src.parser.dxf_reader import DxfReader

SCAN_ENTITY_TYPES: Tuple[str, ...] = (
    "TEXT",
    "MTEXT",
    "ATTRIB",
    "ATTDEF",
    "DIMENSION",
    "LEADER",
    "MLEADER",
    "INSERT",
)

TEXT_BEARING_TYPES: frozenset[str] = frozenset(
    {"TEXT", "MTEXT", "ATTRIB", "ATTDEF", "DIMENSION", "LEADER", "MLEADER"}
)

SEARCH_PATTERNS: Tuple[str, ...] = (
    "@",
    "C/C",
    "LD",
    "LD+10DB",
    "1900",
    "500",
    "SFR",
    "SIDE FACE",
)

D1_EXTRACTED_TYPES: frozenset[str] = frozenset({"TEXT", "MTEXT"})


class TextInventoryItem(TypedDict):
    entity_type: str
    text: str
    x: float
    y: float
    layer: str
    block_name: Optional[str]


class PatternMatch(TypedDict):
    entity_type: str
    text: str
    x: float
    y: float


class PatternSearchResult(TypedDict):
    pattern: str
    matches: List[PatternMatch]


class EntityTypeSummary(TypedDict):
    stirrup_spacing_found: bool
    anchorage_found: bool
    dimension_found: bool
    stirrup_entity_types: List[str]
    anchorage_entity_types: List[str]
    dimension_entity_types: List[str]
    extracted_by_d1: List[str]
    not_extracted_by_d1: List[str]
    recommendation: str


class EntityTypeValidation(TypedDict):
    entity_types_scanned: List[str]
    total_text_entities_found: int
    pattern_matches_found: int
    status: str


class SurveyResult(TypedDict):
    inventory: Dict[str, int]
    text_inventory: List[TextInventoryItem]
    pattern_search: List[PatternSearchResult]
    summary: EntityTypeSummary
    validation: EntityTypeValidation
    report_text: str


class DxfEntityTypeSurvey:
    """Read-only survey of text-bearing entities across the entire reinforcement DXF."""

    def survey(self, dxf_path: str) -> SurveyResult:
        doc = DxfReader(dxf_path).read()
        msp = doc.modelspace()

        inventory = self._build_inventory(doc, msp)
        text_inventory = self._collect_text_inventory(doc, msp)
        pattern_search = self._search_patterns(text_inventory)
        summary = self._build_summary(text_inventory, pattern_search)
        validation = self._build_validation(text_inventory, pattern_search)
        report_text = self._build_report_text(
            inventory, text_inventory, pattern_search, summary
        )

        logger.info(
            "Entity survey: {} text-bearing entities, {} pattern matches",
            validation["total_text_entities_found"],
            validation["pattern_matches_found"],
        )
        return SurveyResult(
            inventory=inventory,
            text_inventory=text_inventory,
            pattern_search=pattern_search,
            summary=summary,
            validation=validation,
            report_text=report_text,
        )

    def _build_inventory(self, doc: Drawing, msp: Any) -> Dict[str, int]:
        inventory: Dict[str, int] = {}
        flat_attrib = 0
        for entity, _ in self._walk_entities(msp):
            if entity.dxftype() == "ATTRIB":
                flat_attrib += 1

        attdef_count = 0
        for block in doc.blocks:
            if block.name.startswith("*"):
                continue
            attdef_count += len(list(block.query("ATTDEF")))

        for entity_type in SCAN_ENTITY_TYPES:
            if entity_type == "ATTRIB":
                inventory[entity_type] = flat_attrib
            elif entity_type == "ATTDEF":
                inventory[entity_type] = attdef_count
            else:
                inventory[entity_type] = len(list(msp.query(entity_type)))

        return inventory

    def _collect_text_inventory(
        self, doc: Drawing, msp: Any
    ) -> List[TextInventoryItem]:
        items: List[TextInventoryItem] = []

        for entity, block_name in self._walk_entities(msp):
            record = self._text_record_from_entity(entity, block_name)
            if record is not None:
                items.append(record)

        for block in doc.blocks:
            if block.name.startswith("*"):
                continue
            for entity in block.query("ATTDEF"):
                record = self._text_record_from_entity(entity, block.name)
                if record is not None:
                    items.append(record)

        items.sort(
            key=lambda item: (
                item["entity_type"],
                item["layer"],
                -item["y"],
                item["x"],
                item["text"],
            )
        )
        return items

    def _walk_entities(
        self, entities: Any, block_name: Optional[str] = None
    ) -> List[Tuple[DXFGraphic, Optional[str]]]:
        collected: List[Tuple[DXFGraphic, Optional[str]]] = []
        for entity in entities:
            entity_type = entity.dxftype()
            if entity_type == "INSERT":
                insert_name = str(entity.dxf.name)
                try:
                    for virtual in entity.virtual_entities():
                        collected.extend(
                            self._walk_entities([virtual], insert_name)
                        )
                except Exception as exc:
                    handle = getattr(entity.dxf, "handle", "unknown")
                    logger.warning(
                        "Could not expand INSERT handle={}: {}", handle, exc
                    )
                continue
            collected.append((entity, block_name))
        return collected

    def _text_record_from_entity(
        self,
        entity: DXFGraphic,
        block_name: Optional[str],
    ) -> Optional[TextInventoryItem]:
        entity_type = entity.dxftype()
        if entity_type not in TEXT_BEARING_TYPES:
            return None

        text = self._extract_text(entity, entity_type)
        if not text:
            return None

        x, y = self._extract_position(entity, entity_type)
        return TextInventoryItem(
            entity_type=entity_type,
            text=text,
            x=round(x, 2),
            y=round(y, 2),
            layer=str(entity.dxf.layer),
            block_name=block_name,
        )

    def _extract_text(self, entity: DXFGraphic, entity_type: str) -> str:
        if entity_type == "TEXT":
            return str(entity.dxf.text).strip()

        if entity_type == "MTEXT":
            return str(entity.text).strip()

        if entity_type in ("ATTRIB", "ATTDEF"):
            return str(entity.dxf.text).strip()

        if entity_type == "DIMENSION":
            return self._dimension_text(entity)

        if entity_type in ("LEADER", "MLEADER"):
            return self._leader_text(entity)

        return ""

    def _dimension_text(self, entity: DXFGraphic) -> str:
        override = getattr(entity.dxf, "text", None)
        if override is not None and str(override).strip():
            return self._normalize_display_text(str(override))

        measurement = getattr(entity.dxf, "actual_measurement", None)
        if measurement is not None:
            value = float(measurement)
            if abs(value - round(value)) < 0.5:
                return str(int(round(value)))
            return str(round(value, 2))

        if hasattr(entity, "get_measurement"):
            try:
                measurement = entity.get_measurement()
                if measurement is not None:
                    value = float(measurement)
                    if abs(value - round(value)) < 0.5:
                        return str(int(round(value)))
                    return str(round(value, 2))
            except Exception:
                pass

        return ""

    def _leader_text(self, entity: DXFGraphic) -> str:
        for attr in ("text", "annotation_text"):
            value = getattr(entity.dxf, attr, None)
            if value is not None and str(value).strip():
                return self._normalize_display_text(str(value))

        if hasattr(entity, "virtual_entities"):
            try:
                for virtual in entity.virtual_entities():
                    virtual_type = virtual.dxftype()
                    if virtual_type in ("MTEXT", "TEXT"):
                        return self._extract_text(virtual, virtual_type)
            except Exception:
                pass

        return ""

    @staticmethod
    def _normalize_display_text(text: str) -> str:
        return text.replace("\\P", "").replace("\n", "").strip()

    def _extract_position(
        self, entity: DXFGraphic, entity_type: str
    ) -> Tuple[float, float]:
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

    def _search_patterns(
        self, text_inventory: List[TextInventoryItem]
    ) -> List[PatternSearchResult]:
        results: List[PatternSearchResult] = []
        for pattern in SEARCH_PATTERNS:
            matches: List[PatternMatch] = []
            pattern_upper = pattern.upper()
            for item in text_inventory:
                normalized = self._normalize_for_search(item["text"])
                if self._pattern_matches(pattern, pattern_upper, normalized):
                    matches.append(
                        PatternMatch(
                            entity_type=item["entity_type"],
                            text=item["text"],
                            x=item["x"],
                            y=item["y"],
                        )
                    )
            results.append(PatternSearchResult(pattern=pattern, matches=matches))
        return results

    @staticmethod
    def _normalize_for_search(text: str) -> str:
        return text.replace("\\P", "").replace("\n", "").strip().upper()

    def _pattern_matches(
        self, pattern: str, pattern_upper: str, normalized_text: str
    ) -> bool:
        if pattern_upper == "LD":
            return bool(re.search(r"\bLD\b", normalized_text)) or normalized_text == "LD"
        return pattern_upper in normalized_text

    def _build_summary(
        self,
        text_inventory: List[TextInventoryItem],
        pattern_search: List[PatternSearchResult],
    ) -> EntityTypeSummary:
        stirrup_types: set[str] = set()
        anchorage_types: set[str] = set()
        dimension_types: set[str] = set()

        for item in text_inventory:
            normalized = self._normalize_for_search(item["text"])
            entity_type = item["entity_type"]

            if "@" in normalized or "C/C" in normalized:
                stirrup_types.add(entity_type)

            if re.search(r"\bLD\b", normalized) or normalized == "LD":
                anchorage_types.add(entity_type)

            if entity_type == "DIMENSION" and re.fullmatch(r"\d+", normalized):
                dimension_types.add(entity_type)
            elif re.fullmatch(r"\d+$", normalized) and entity_type != "DIMENSION":
                dimension_types.add(entity_type)

        stirrup_found = bool(stirrup_types)
        anchorage_found = bool(anchorage_types)
        dimension_found = bool(dimension_types) or any(
            item["entity_type"] == "DIMENSION"
            and re.fullmatch(r"\d+", self._normalize_for_search(item["text"]))
            for item in text_inventory
        )

        if not dimension_types and dimension_found:
            dimension_types.add("DIMENSION")

        all_types = {item["entity_type"] for item in text_inventory}
        extracted = sorted(t for t in all_types if t in D1_EXTRACTED_TYPES)
        not_extracted = sorted(t for t in all_types if t not in D1_EXTRACTED_TYPES)

        needs_extension = stirrup_found or anchorage_found or dimension_found
        if needs_extension and not_extracted:
            recommendation = "Extend D.1 extraction first"
        elif needs_extension:
            recommendation = "Extend D.1 extraction first"
        else:
            recommendation = "Proceed to D.2"

        return EntityTypeSummary(
            stirrup_spacing_found=stirrup_found,
            anchorage_found=anchorage_found,
            dimension_found=dimension_found,
            stirrup_entity_types=sorted(stirrup_types),
            anchorage_entity_types=sorted(anchorage_types),
            dimension_entity_types=sorted(dimension_types),
            extracted_by_d1=extracted,
            not_extracted_by_d1=not_extracted,
            recommendation=recommendation,
        )

    def _build_validation(
        self,
        text_inventory: List[TextInventoryItem],
        pattern_search: List[PatternSearchResult],
    ) -> EntityTypeValidation:
        pattern_matches = sum(len(result["matches"]) for result in pattern_search)
        return EntityTypeValidation(
            entity_types_scanned=list(SCAN_ENTITY_TYPES),
            total_text_entities_found=len(text_inventory),
            pattern_matches_found=pattern_matches,
            status="PASS",
        )

    def _build_report_text(
        self,
        inventory: Dict[str, int],
        text_inventory: List[TextInventoryItem],
        pattern_search: List[PatternSearchResult],
        summary: EntityTypeSummary,
    ) -> str:
        lines = [
            "======================================================================",
            "DXF Entity-Type Survey Report (Phase D.1.6B)",
            "======================================================================",
            "",
            "Entity inventory (modelspace / blocks):",
        ]
        for entity_type in SCAN_ENTITY_TYPES:
            lines.append(f"  {entity_type}: {inventory.get(entity_type, 0)}")

        lines.extend(
            [
                "",
                f"Total text-bearing entities: {len(text_inventory)}",
                "",
                "1. Where are stirrup spacing annotations stored?",
            ]
        )
        if summary["stirrup_spacing_found"]:
            lines.append(
                f"   Found in entity types: {', '.join(summary['stirrup_entity_types'])}"
            )
            stirrup_matches = next(
                (r for r in pattern_search if r["pattern"] == "@"), None
            )
            if stirrup_matches:
                for match in stirrup_matches["matches"][:5]:
                    lines.append(
                        f"   Example: {match['entity_type']} — {match['text'][:60]}"
                    )
        else:
            lines.append("   Not found in any surveyed text entity.")

        lines.extend(["", "2. Where are Ld / Ld+10db annotations stored?"])
        if summary["anchorage_found"]:
            lines.append(
                f"   Found in entity types: {', '.join(summary['anchorage_entity_types'])}"
            )
            for result in pattern_search:
                if result["pattern"] in ("LD", "LD+10DB") and result["matches"]:
                    for match in result["matches"][:3]:
                        lines.append(
                            f"   Example: {match['entity_type']} — {match['text']}"
                        )
        else:
            lines.append("   Not found in any surveyed text entity.")

        lines.extend(["", "3. Where are dimensions stored?"])
        if summary["dimension_found"]:
            lines.append(
                f"   Found in entity types: {', '.join(summary['dimension_entity_types'])}"
            )
            dim_examples = [
                item
                for item in text_inventory
                if item["entity_type"] == "DIMENSION"
                and re.fullmatch(
                    r"\d+",
                    self._normalize_for_search(item["text"]),
                )
            ]
            for item in dim_examples[:5]:
                lines.append(
                    f"   Example: DIMENSION — {item['text']} (layer {item['layer']})"
                )
        else:
            lines.append("   Not found as numeric dimension text.")

        lines.extend(
            [
                "",
                "4. Are they TEXT?",
                f"   Stirrup: {'yes' if 'TEXT' in summary['stirrup_entity_types'] else 'no'}",
                f"   Anchorage: {'yes' if 'TEXT' in summary['anchorage_entity_types'] else 'no'}",
                f"   Dimension: {'yes' if 'TEXT' in summary['dimension_entity_types'] else 'no'}",
                "",
                "5. Are they MTEXT?",
                f"   Stirrup: {'yes' if 'MTEXT' in summary['stirrup_entity_types'] else 'no'}",
                f"   Anchorage: {'yes' if 'MTEXT' in summary['anchorage_entity_types'] else 'no'}",
                f"   Dimension: {'yes' if 'MTEXT' in summary['dimension_entity_types'] else 'no'}",
                "",
                "6. Are they ATTRIB?",
                f"   Stirrup: {'yes' if 'ATTRIB' in summary['stirrup_entity_types'] else 'no'}",
                f"   Anchorage: {'yes' if 'ATTRIB' in summary['anchorage_entity_types'] else 'no'}",
                f"   Dimension: {'yes' if 'ATTRIB' in summary['dimension_entity_types'] else 'no'}",
                "",
                "7. Are they DIMENSION entities?",
                f"   Stirrup: {'yes' if 'DIMENSION' in summary['stirrup_entity_types'] else 'no'}",
                f"   Anchorage: {'yes' if 'DIMENSION' in summary['anchorage_entity_types'] else 'no'}",
                f"   Dimension: {'yes' if 'DIMENSION' in summary['dimension_entity_types'] else 'no'}",
                "",
                "8. Are they inside INSERT blocks?",
            ]
        )
        in_blocks = [
            item
            for item in text_inventory
            if item["block_name"] is not None
            and (
                "@" in self._normalize_for_search(item["text"])
                or "LD" in self._normalize_for_search(item["text"])
                or item["entity_type"] == "DIMENSION"
            )
        ]
        if in_blocks:
            for item in in_blocks[:5]:
                lines.append(
                    f"   {item['entity_type']} in block {item['block_name']}: {item['text'][:50]}"
                )
        else:
            lines.append("   No stirrup/anchorage/dimension text found inside INSERT blocks.")

        lines.extend(
            [
                "",
                "D.1 extraction coverage:",
                f"   Extracted by D.1 (TEXT/MTEXT): {', '.join(summary['extracted_by_d1']) or 'none'}",
                f"   Not extracted by D.1: {', '.join(summary['not_extracted_by_d1']) or 'none'}",
                "",
                f"Recommendation: {summary['recommendation']}",
                "",
                "======================================================================",
            ]
        )
        return "\n".join(lines) + "\n"
