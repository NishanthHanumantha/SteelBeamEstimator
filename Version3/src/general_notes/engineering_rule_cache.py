"""Cached access layer for General Notes engineering rules."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.general_notes.ld_table_selector import steel_base_numeric, steel_table_key
from src.general_notes.member_type_normalizer import member_lookup_aliases


class EngineeringRuleCache:
    """
    Load, validate, and cache project engineering rules.

    Future phases must use this cache — never read JSON output files directly.
    """

    _instance: Optional["EngineeringRuleCache"] = None

    def __init__(self, rules_path: Optional[Path] = None) -> None:
        self._model: Optional[dict[str, Any]] = None
        self._source_path: Optional[Path] = None
        if rules_path is not None:
            self.load(rules_path)

    @classmethod
    def get_instance(cls, rules_path: Optional[Path] = None) -> "EngineeringRuleCache":
        if cls._instance is None:
            cls._instance = EngineeringRuleCache(rules_path)
        elif rules_path is not None:
            cls._instance.load(rules_path)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def load(self, rules_path: Path) -> dict[str, Any]:
        path = Path(rules_path)
        if not path.exists():
            raise FileNotFoundError(f"Engineering rules not found: {path}")
        self._model = json.loads(path.read_text(encoding="utf-8"))
        self._source_path = path
        logger.info("Engineering rule cache loaded from {}", path)
        return self._model

    @property
    def model(self) -> dict[str, Any]:
        if self._model is None:
            raise RuntimeError(
                "Engineering rule cache is empty. Run Phase E or call load()."
            )
        return self._model

    def get_cover(self, member: str) -> Optional[dict[str, Any]]:
        member_upper = member.upper().replace("_", " ")
        normalized_target = member.upper().replace(" ", "_")

        for row in self.model.get("cover_tables", []):
            normalized = str(row.get("normalized_member_type", "")).upper()
            original = str(row.get("original_member_type", "")).upper()
            aliases = member_lookup_aliases(normalized)
            if (
                normalized_target == normalized
                or member_upper in original
                or any(member_upper in alias.upper() for alias in aliases)
                or normalized in member_upper
            ):
                return row.get("cover") or {
                    "value_mm": row.get("cover_mm"),
                    "unit": "mm",
                }
        return None

    def get_ld(
        self,
        steel_grade: str,
        concrete_grade: str,
        diameter: int,
    ) -> Optional[dict[str, Any]]:
        steel = steel_table_key(steel_grade)
        concrete = self._normalize_concrete_key(concrete_grade)
        tables = self.model.get("development_length_tables", {})
        return self._lookup_ld_in_tables(tables, steel, concrete, diameter)

    def get_active_ld(
        self,
        diameter: int,
        concrete_grade: str,
    ) -> Optional[dict[str, Any]]:
        """Lookup Ld using the project's active development length table."""
        active = self.model.get("active_development_length_table")
        if isinstance(active, dict) and active:
            concrete = self._normalize_concrete_key(concrete_grade)
            return self._lookup_ld_in_table(active, concrete, diameter)

        matched_key = self.model.get("matched_development_table_key")
        tables = self.model.get("development_length_tables", {})
        if matched_key and matched_key in tables:
            concrete = self._normalize_concrete_key(concrete_grade)
            return self._lookup_ld_in_table(tables[matched_key], concrete, diameter)

        defaults = self.model.get("project_defaults", {})
        steel = defaults.get("default_development_table")
        if steel:
            return self.get_ld(steel, concrete_grade, diameter)
        return None

    def get_default_cover(self) -> Optional[dict[str, Any]]:
        defaults = self.model.get("project_defaults", {})
        cover_mm = defaults.get("default_cover_mm")
        if cover_mm is not None:
            return {"value_mm": cover_mm, "unit": "mm"}
        constants = self.model.get("engineering_constants", {})
        return constants.get("default_cover")

    def get_spacer_rule(self) -> dict[str, Any]:
        return dict(self.model.get("spacer_rules", {}))

    def get_hook_rule(self) -> List[dict[str, Any]]:
        return [
            rule
            for rule in self.model.get("anchorage_rules", [])
            if rule.get("rule_type") == "HOOK_ANCHORAGE"
            or "HOOK" in str(rule.get("description", "")).upper()
        ]

    def get_bend_rule(self) -> List[dict[str, Any]]:
        return list(self.model.get("bend_rules", []))

    def get_project_defaults(self) -> dict[str, Any]:
        return dict(self.model.get("project_defaults", {}))

    def get_materials(self) -> dict[str, Any]:
        return dict(self.model.get("materials", {}))

    def get_constants(self) -> dict[str, Any]:
        return dict(self.model.get("engineering_constants", {}))

    def get_default_steel_grade(self) -> Optional[str]:
        defaults = self.get_project_defaults()
        if defaults.get("default_steel_grade"):
            return defaults["default_steel_grade"]
        materials = self.get_materials()
        default = materials.get("default_steel_grade")
        if isinstance(default, dict):
            return default.get("grade")
        return None

    def get_default_concrete_grade(self) -> Optional[str]:
        defaults = self.get_project_defaults()
        if defaults.get("default_concrete_grade"):
            return defaults["default_concrete_grade"]
        materials = self.get_materials()
        default = materials.get("default_concrete_grade")
        if isinstance(default, dict):
            return default.get("grade")
        return None

    def _lookup_ld_in_tables(
        self,
        tables: dict[str, Any],
        steel: str,
        concrete: str,
        diameter: int,
    ) -> Optional[dict[str, Any]]:
        grade_table = tables.get(steel)
        if not isinstance(grade_table, dict):
            numeric = steel_base_numeric(steel)
            for key, table in tables.items():
                if steel_base_numeric(key) == numeric:
                    grade_table = table
                    break
        if not isinstance(grade_table, dict):
            return None
        return self._lookup_ld_in_table(grade_table, concrete, diameter)

    def _lookup_ld_in_table(
        self,
        concrete_table: dict[str, Any],
        concrete: str,
        diameter: int,
    ) -> Optional[dict[str, Any]]:
        if not isinstance(concrete_table, dict):
            return None
        table = concrete_table.get(concrete)
        if not isinstance(table, dict):
            for key, candidate in concrete_table.items():
                if concrete.replace("M", "") in str(key):
                    table = candidate
                    break
        if not isinstance(table, dict):
            return None
        value = table.get(diameter) or table.get(str(diameter))
        if value is None:
            return None
        return {"value_mm": value, "unit": "mm"}

    def _normalize_concrete_key(self, grade: str) -> str:
        cleaned = grade.upper().replace(" ", "")
        if cleaned.startswith("M"):
            return cleaned
        return f"M{cleaned}"
