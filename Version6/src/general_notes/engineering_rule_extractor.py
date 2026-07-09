"""Extract normalized engineering rules from parsed General Notes."""

import re
from typing import Any, Dict, List, Optional

from src.general_notes.general_notes_parser import GeneralNotesDocument, TextAnnotation
from src.general_notes.ld_table_selector import LdTableSelector, steel_table_key
from src.general_notes.member_type_normalizer import normalize_member_type
from src.general_notes.normalizers import (
    extract_all_concrete_grades,
    extract_all_steel_grades,
    normalize_angle_degrees,
    normalize_db_multiplier,
    normalize_mm,
)
from src.general_notes.table2_extractor import Table2Extractor
from src.general_notes.table_extractor import CoverRow, TableExtractor

_MIN_LAP_RE = re.compile(r"lap\s+length\s+less\s+than\s+(\d+)\s*mm", re.IGNORECASE)
_COUPLER_RE = re.compile(r"mechanical\s+couplers?", re.IGNORECASE)
_DEFAULT_CONCRETE_RE = re.compile(
    r"CONCRETE\s+SHALL\s+BE\s+OF\s+GRADE\s+(M\d{2,3})", re.IGNORECASE
)
_SPACER_DIA_RE = re.compile(
    r"spacer.{0,80}?(\d{1,2})\s*mm", re.IGNORECASE | re.DOTALL
)
_SPACER_SPACING_RE = re.compile(
    r"(?:spacing|spaced).{0,80}?(\d{3,4})\s*mm", re.IGNORECASE | re.DOTALL
)
_STEEL_DENSITY_RE = re.compile(r"7850|7\.85", re.IGNORECASE)

_ANCHORAGE_INCLUDE = (
    "DEVELOPMENT LENGTH",
    "DEVELOPMENT LENGTHS",
    "'LD'",
    " LD ",
    "ANCHOR",
    "ANCHORAGE",
    "COMPRESSION",
    "TENSION",
    "HOOK",
    "TABLE-1",
    "TABLE 1",
)
_ANCHORAGE_EXCLUDE = (
    "CONSTRUCTION",
    "EXCAVATION",
    "FIRE",
    "WATERPROOF",
    "ARCHITECT",
    "TEMPORARY",
    "SAFETY",
    "DEWATERING",
    "FORMWORK",
    "SHORING",
    "SETTING OUT",
    "DESHUTTERING",
)

_FABRICATION_INCLUDE = (
    "LAP",
    "SPLICE",
    "COUPLER",
    "MECHANICAL COUPLER",
    "MINIMUM LAP",
    "BENDING",
    "FABRICATION",
    "KINKED",
    "CRANKED",
    "NO LAP",
    "WELD",
)
_FABRICATION_EXCLUDE = _ANCHORAGE_EXCLUDE


class EngineeringRuleExtractor:
    """Build the unified engineering knowledge model."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._table_extractor = TableExtractor(config)
        self._table2_extractor = Table2Extractor(config)
        self._ld_selector = LdTableSelector()

    def extract(self, document: GeneralNotesDocument) -> dict[str, Any]:
        texts = document.texts
        blob = document.all_text_joined()

        table2_info = self._table2_extractor.extract(texts, blob)
        ld_tables_raw = self._table_extractor.extract_development_length_tables(texts)
        ld_grids = self._table_extractor.extract_development_length_grid_tables(texts)
        cover_rows = self._table_extractor.extract_cover_table(texts)

        steel_grades = extract_all_steel_grades(blob)
        concrete_grades = extract_all_concrete_grades(blob)

        table2_steel = table2_info.get("table2_steel_grade")
        default_concrete = table2_info.get("table2_concrete_grade") or self._default_concrete_grade(blob)
        default_steel = table2_steel or self._fallback_steel_grade(steel_grades, ld_tables_raw)

        materials = {
            "steel_grades": steel_grades,
            "concrete_grades": concrete_grades,
            "default_steel_grade": default_steel,
            "default_concrete_grade": default_concrete,
            "table2_steel_grade": table2_steel,
        }

        ld_selection = self._ld_selector.select(
            table2_steel, ld_tables_raw, default_steel
        )
        resolved_ld_tables = ld_selection.get("resolved_tables", ld_tables_raw)

        cover_table = [
            self._cover_row_to_dict(row) for row in cover_rows
        ]
        bend_rules = self._extract_bend_rules(texts, blob)
        anchorage_rules = self._extract_anchorage_rules(blob)
        fabrication_rules = self._extract_fabrication_rules(blob)
        spacer_rules = self._extract_spacer_rules(blob)
        constants = self._extract_engineering_constants(
            blob, cover_rows, fabrication_rules, bend_rules, spacer_rules
        )

        return {
            "materials": materials,
            "development_length_tables": resolved_ld_tables,
            "cover_tables": cover_table,
            "bend_rules": bend_rules,
            "anchorage_rules": anchorage_rules,
            "fabrication_rules": fabrication_rules,
            "spacer_rules": spacer_rules,
            "engineering_constants": constants,
            "table2_information": table2_info,
            "ld_selection": ld_selection,
            "extraction_metadata": {
                "ld_grid_count": len(ld_grids),
                "cover_row_count": len(cover_rows),
                "text_entity_count": len(texts),
                "sheet_ids": [s.sheet_id for s in document.sheets],
                "ld_table_keys": list(resolved_ld_tables.keys()),
                "matched_ld_table_key": ld_selection.get("matched_table_key"),
            },
            "_ld_grids": ld_grids,
            "_cover_rows": cover_rows,
            "_active_ld_grid": self._active_grid(ld_grids, ld_selection),
        }

    def _active_grid(
        self, grids: list, ld_selection: dict[str, Any]
    ) -> Optional[Any]:
        matched = ld_selection.get("matched_table_key")
        if not matched:
            return grids[0] if grids else None
        base = steel_table_key(matched)
        for grid in grids:
            if grid.metadata.get("steel_grade") == base:
                return grid
        return grids[0] if grids else None

    def _default_concrete_grade(self, blob: str) -> Optional[dict[str, str]]:
        match = _DEFAULT_CONCRETE_RE.search(blob)
        if match:
            return {"grade": match.group(1).upper().replace(" ", "")}
        grades = extract_all_concrete_grades(blob)
        return grades[0] if grades else {"grade": "M30"}

    def _fallback_steel_grade(
        self,
        steel_grades: List[dict[str, str]],
        ld_tables: Dict[str, Any],
    ) -> Optional[dict[str, str]]:
        for grade in steel_grades:
            if grade.get("grade") in ("Fe550D", "Fe550"):
                return grade
        if "Fe500" in ld_tables:
            return {"grade": "Fe500"}
        return steel_grades[-1] if steel_grades else None

    def _cover_row_to_dict(self, row: CoverRow) -> dict[str, Any]:
        normalized = normalize_member_type(row.member_type)
        return {
            "serial": row.serial,
            "member_type": row.member_type,
            "original_member_type": row.member_type,
            "normalized_member_type": normalized,
            "cover_mm": row.cover_mm,
            "cover": {"value_mm": row.cover_mm, "unit": "mm"},
            "notes": row.notes,
            "y_position": row.y_position,
        }

    def _extract_bend_rules(
        self, texts: List[TextAnnotation], blob: str
    ) -> List[dict[str, Any]]:
        rules: List[dict[str, Any]] = []
        seen: set[str] = set()

        for ann in texts:
            upper = ann.text.upper()
            if "BEND" in upper or "db" in ann.text.lower():
                angle = normalize_angle_degrees(ann.text)
                multiplier = normalize_db_multiplier(ann.text)
                if angle:
                    key = f"angle_{angle['angle_deg']}"
                    if key not in seen:
                        seen.add(key)
                        rules.append(
                            {
                                "rule_type": "STANDARD_BEND",
                                "angle": angle,
                                "source_text": ann.text,
                            }
                        )
                if multiplier:
                    key = f"mult_{multiplier['multiplier']}"
                    if key not in seen:
                        seen.add(key)
                        rules.append(
                            {
                                "rule_type": "BEND_MULTIPLIER",
                                "multiplier_db": multiplier["multiplier"],
                                "reference": multiplier["reference"],
                                "source_text": ann.text,
                            }
                        )
                if "STANDARD" in upper and "BEND" in upper:
                    key = ann.text[:40]
                    if key not in seen:
                        seen.add(key)
                        rules.append(
                            {
                                "rule_type": "STANDARD_BEND_NOTE",
                                "description": ann.text,
                                "angle": normalize_angle_degrees(ann.text),
                            }
                        )

        if "db=DIA OF BAR" in blob.upper():
            rules.append(
                {
                    "rule_type": "BEND_REFERENCE",
                    "description": "db = diameter of bar",
                    "reference": "bar_diameter",
                }
            )
        return rules

    def _extract_anchorage_rules(self, blob: str) -> List[dict[str, Any]]:
        rules: List[dict[str, Any]] = []
        for line in blob.splitlines():
            stripped = line.strip()
            if len(stripped) < 15:
                continue
            if not self._is_anchorage_line(stripped):
                continue
            upper = stripped.upper()
            rule_type = "ANCHORAGE_NOTE"
            if "COMPRESSION" in upper:
                rule_type = "COMPRESSION_LD"
            elif "TENSION" in upper:
                rule_type = "TENSION_LD"
            elif "HOOK" in upper:
                rule_type = "HOOK_ANCHORAGE"
            elif "DEVELOPMENT LENGTH" in upper or " LD " in upper:
                rule_type = "DEVELOPMENT_LENGTH"
            rules.append({"rule_type": rule_type, "description": stripped})

        if not rules:
            rules.append(
                {
                    "rule_type": "TABLE_REFERENCE",
                    "description": "Development lengths per TABLE 1",
                    "table": "TABLE_1",
                }
            )
        return rules[:25]

    def _is_anchorage_line(self, line: str) -> bool:
        upper = line.upper()
        if any(ex in upper for ex in _ANCHORAGE_EXCLUDE):
            return False
        return any(kw in upper for kw in _ANCHORAGE_INCLUDE)

    def _extract_fabrication_rules(self, blob: str) -> List[dict[str, Any]]:
        rules: List[dict[str, Any]] = []
        for line in blob.splitlines():
            stripped = line.strip()
            if len(stripped) < 20:
                continue
            if not self._is_fabrication_line(stripped):
                continue
            upper = stripped.upper()
            rule_type = "FABRICATION_NOTE"
            if "LAP" in upper or "SPLICE" in upper:
                rule_type = "LAP_SPLICE"
            if _COUPLER_RE.search(stripped):
                rule_type = "MECHANICAL_COUPLER"
            if "NO LAP" in upper:
                rule_type = "NO_LAP_ZONE"
            rules.append({"rule_type": rule_type, "description": stripped})

        min_lap = _MIN_LAP_RE.search(blob)
        if min_lap:
            rules.append(
                {
                    "rule_type": "MINIMUM_LAP_LENGTH",
                    "minimum_lap_mm": int(min_lap.group(1)),
                    "lap": {"value_mm": int(min_lap.group(1)), "unit": "mm"},
                }
            )
        return rules[:30]

    def _is_fabrication_line(self, line: str) -> bool:
        upper = line.upper()
        if any(ex in upper for ex in _FABRICATION_EXCLUDE):
            return False
        return any(kw in upper for kw in _FABRICATION_INCLUDE)

    def _extract_spacer_rules(self, blob: str) -> dict[str, Any]:
        rules: dict[str, Any] = {
            "rules": [],
            "chairs_required": False,
            "largest_bar_rule": None,
        }
        spacer_lines: List[str] = []
        for line in blob.splitlines():
            upper = line.upper()
            if any(kw in upper for kw in ("SPACER", "CHAIR", "PIN", "COVER BLOCK")):
                spacer_lines.append(line.strip())
                if "CHAIR" in upper or "PIN" in upper or "9.01" in line:
                    rules["chairs_required"] = True
                if "LARGEST" in upper and "BAR" in upper:
                    rules["largest_bar_rule"] = line.strip()

        rules["rules"] = spacer_lines[:15]
        if "9.01" in blob:
            rules["section_reference"] = "9.01"

        combined = "\n".join(spacer_lines)
        dia_match = _SPACER_DIA_RE.search(combined) or _SPACER_DIA_RE.search(blob)
        if dia_match:
            rules["spacer_diameter_mm"] = int(dia_match.group(1))
            rules["spacer_diameter"] = {
                "value_mm": int(dia_match.group(1)),
                "unit": "mm",
            }

        spacing_match = _SPACER_SPACING_RE.search(combined) or _SPACER_SPACING_RE.search(
            blob
        )
        if spacing_match:
            rules["spacer_spacing_mm"] = int(spacing_match.group(1))
            rules["spacer_spacing"] = {
                "value_mm": int(spacing_match.group(1)),
                "unit": "mm",
            }

        return rules

    def _extract_engineering_constants(
        self,
        blob: str,
        cover_rows: List[CoverRow],
        fabrication_rules: List[dict[str, Any]],
        bend_rules: List[dict[str, Any]],
        spacer_rules: dict[str, Any],
    ) -> dict[str, Any]:
        constants: dict[str, Any] = {}

        beam_cover = next(
            (
                row.cover_mm
                for row in cover_rows
                if normalize_member_type(row.member_type) == "BEAM"
            ),
            None,
        )
        if beam_cover is not None:
            constants["default_beam_cover_mm"] = beam_cover
            constants["default_cover"] = {"value_mm": beam_cover, "unit": "mm"}

        min_covers = [row.cover_mm for row in cover_rows]
        if min_covers:
            minimum = min(min_covers)
            constants["minimum_cover_mm"] = minimum
            constants["minimum_cover"] = {"value_mm": minimum, "unit": "mm"}

        agg_match = re.search(
            r"MAXIMUM SIZE OF AGGREGATE.*?(\d+)\s*mm",
            blob,
            re.IGNORECASE | re.DOTALL,
        )
        if agg_match:
            constants["maximum_aggregate_mm"] = int(agg_match.group(1))

        for rule in fabrication_rules:
            if rule.get("rule_type") == "MINIMUM_LAP_LENGTH":
                constants["minimum_lap_mm"] = rule.get("minimum_lap_mm")
                constants["minimum_lap"] = rule.get("lap")

        bend_multipliers = [
            rule["multiplier_db"]
            for rule in bend_rules
            if rule.get("rule_type") == "BEND_MULTIPLIER"
        ]
        if bend_multipliers:
            constants["standard_bend_multipliers_db"] = sorted(set(bend_multipliers))
            constants["standard_hook_multipliers_db"] = sorted(set(bend_multipliers))

        cement_match = re.search(
            r"MINIMUM CEMENT CONTENT.*?(\d+)\s*kg",
            blob,
            re.IGNORECASE | re.DOTALL,
        )
        if cement_match:
            constants["minimum_cement_content_kg_per_m3"] = int(cement_match.group(1))

        if _STEEL_DENSITY_RE.search(blob):
            constants["steel_density_kg_per_m3"] = 7850
        else:
            constants["steel_density_kg_per_m3"] = 7850
            constants["steel_density_source"] = "standard_reference"

        constants["unit_weight_formula"] = "d2/162"
        constants["unit_weight_formula_description"] = "Weight kg/m = d²/162 (d in mm)"

        if spacer_rules.get("spacer_diameter_mm"):
            constants["spacer_diameter_mm"] = spacer_rules["spacer_diameter_mm"]
        if spacer_rules.get("spacer_spacing_mm"):
            constants["spacer_spacing_mm"] = spacer_rules["spacer_spacing_mm"]

        return constants

    def split_outputs(self, model: dict[str, Any]) -> dict[str, Any]:
        materials = model.get("materials", {})
        return {
            "development_length_table": model.get("development_length_tables", {}),
            "cover_table": model.get("cover_tables", []),
            "material_specifications": materials,
            "engineering_constants": model.get("engineering_constants", {}),
            "project_defaults": model.get("project_defaults", {}),
        }
