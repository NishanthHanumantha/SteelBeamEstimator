"""Cached access layer for General Notes engineering rules."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from src.estimation.estimator_rule_loader import EstimatorRuleLoader
from src.general_notes.engineering_value import (
    EngineeringValue,
    coerce_engineering_value,
    engineering_value_numeric,
    is_engineering_value,
)
from src.general_notes.ld_table_selector import steel_base_numeric, steel_table_key
from src.general_notes.member_type_normalizer import member_lookup_aliases

DEFAULT_ESTIMATOR_CONFIG = Path("config/estimator_rules.yaml")


class EngineeringRuleCache:
    """
    Load, validate, and cache project engineering rules.

    Future phases must use this cache — never read JSON output files directly.
    """

    _instance: Optional["EngineeringRuleCache"] = None

    def __init__(
        self,
        rules_path: Optional[Path] = None,
        estimator_config_path: Optional[Path] = None,
    ) -> None:
        self._model: Optional[dict[str, Any]] = None
        self._source_path: Optional[Path] = None
        self._estimator_loader: Optional[EstimatorRuleLoader] = None
        self._estimator_config_path = (
            Path(estimator_config_path) if estimator_config_path else DEFAULT_ESTIMATOR_CONFIG
        )
        if rules_path is not None:
            self.load(rules_path)

    @classmethod
    def get_instance(
        cls,
        rules_path: Optional[Path] = None,
        estimator_config_path: Optional[Path] = None,
    ) -> "EngineeringRuleCache":
        if cls._instance is None:
            cls._instance = EngineeringRuleCache(rules_path, estimator_config_path)
        else:
            if rules_path is not None:
                cls._instance.load(rules_path)
            if estimator_config_path is not None:
                cls._instance._estimator_config_path = Path(estimator_config_path)
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

    def get_cover(self, member: str) -> Optional[EngineeringValue]:
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
                wrapped = row.get("cover") or row.get("provenance")
                coerced = coerce_engineering_value(wrapped)
                if coerced:
                    return coerced
                cover_mm = row.get("cover_mm")
                if cover_mm is not None:
                    return EngineeringValue(
                        value=cover_mm,
                        unit="mm",
                        source="GENERAL_NOTES",
                        table="COVER_TABLE",
                        sheet=row.get("sheet", "SH-02"),
                        confidence=1.0,
                        extra={"member": normalized},
                    )
        return None

    def get_ld(
        self,
        steel_grade: str,
        concrete_grade: str,
        diameter: int,
    ) -> Optional[EngineeringValue]:
        steel = steel_table_key(steel_grade)
        concrete = self._normalize_concrete_key(concrete_grade)
        tables = self.model.get("development_tables") or self.model.get(
            "development_length_tables", {}
        )
        return self._lookup_ld_in_tables(tables, steel, concrete, diameter)

    def get_active_ld(
        self,
        diameter: int,
        concrete_grade: str,
    ) -> Optional[EngineeringValue]:
        """Lookup Ld using the project's active development length table."""
        active = self.model.get("active_development_length_table")
        concrete = self._normalize_concrete_key(concrete_grade)
        if isinstance(active, dict) and active:
            result = self._lookup_ld_in_table(active, concrete, diameter)
            if result:
                return result

        matched_key = self.model.get("matched_development_table_key")
        tables = self.model.get("development_tables") or self.model.get(
            "development_length_tables", {}
        )
        if matched_key and matched_key in tables:
            result = self._lookup_ld_in_table(tables[matched_key], concrete, diameter)
            if result:
                return result

        defaults = self.model.get("project_defaults", {})
        steel = engineering_value_numeric(defaults.get("default_development_table"))
        if steel:
            return self.get_ld(str(steel), concrete_grade, diameter)
        return None

    def get_default_cover(self) -> Optional[EngineeringValue]:
        defaults = self.model.get("project_defaults", {})
        wrapped = defaults.get("default_cover")
        coerced = coerce_engineering_value(wrapped)
        if coerced:
            return coerced
        cover_mm = defaults.get("default_cover_mm")
        if cover_mm is not None:
            return EngineeringValue(
                value=cover_mm,
                unit="mm",
                source="GENERAL_NOTES",
                table="COVER_TABLE",
                confidence=1.0,
                extra={"member": "BEAM"},
            )
        constants = self.model.get("engineering_constants", {})
        return coerce_engineering_value(constants.get("default_cover"))

    def get_spacer_rule(self) -> dict[str, Any]:
        structural = self.model.get("structural_detailing_rules", {})
        if structural.get("spacer_rules"):
            return dict(structural["spacer_rules"])
        return dict(self.model.get("spacer_rules", {}))

    def get_estimator_spacer(self) -> EngineeringValue:
        embedded = self.model.get("estimator_rules", {})
        spacer = embedded.get("spacer", {})
        wrapped = spacer.get("diameter")
        coerced = coerce_engineering_value(wrapped)
        if coerced:
            return coerced

        defaults = self.model.get("project_defaults", {})
        wrapped_default = defaults.get("default_spacer_diameter")
        coerced_default = coerce_engineering_value(wrapped_default)
        if coerced_default:
            return coerced_default

        raw = self._estimator().get_estimator_spacer()
        return EngineeringValue(
            value=raw.get("diameter_mm"),
            unit="mm",
            source="ESTIMATOR_RULES",
            confidence=1.0,
            extra={"config": str(self._estimator_config_path)},
        )

    def get_estimator_defaults(self) -> dict[str, Any]:
        defaults = self.model.get("project_defaults", {})
        estimator_defaults = {
            "default_spacer_diameter": defaults.get("default_spacer_diameter"),
            "default_spacer_spacing": defaults.get("default_spacer_spacing"),
            "unit_weight_formula": defaults.get("unit_weight_formula"),
            "rounding_precision": defaults.get("rounding_precision"),
            "default_spacer_diameter_mm": engineering_value_numeric(
                defaults.get("default_spacer_diameter")
            ),
            "default_spacer_spacing_mm": engineering_value_numeric(
                defaults.get("default_spacer_spacing")
            ),
        }
        if estimator_defaults["default_spacer_diameter_mm"] is not None:
            return estimator_defaults
        loader_defaults = self._estimator().get_estimator_defaults()
        return {
            **loader_defaults,
            "default_spacer_diameter": EngineeringValue(
                value=loader_defaults.get("default_spacer_diameter_mm"),
                unit="mm",
                source="ESTIMATOR_RULES",
                confidence=1.0,
                extra={"config": str(self._estimator_config_path)},
            ).to_dict(),
            "default_spacer_spacing": EngineeringValue(
                value=loader_defaults.get("default_spacer_spacing_mm"),
                unit="mm",
                source="ESTIMATOR_RULES",
                confidence=1.0,
                extra={"config": str(self._estimator_config_path)},
            ).to_dict(),
        }

    def get_unit_weight_formula(self) -> Union[EngineeringValue, str]:
        defaults = self.model.get("project_defaults", {})
        wrapped = coerce_engineering_value(defaults.get("unit_weight_formula"))
        if wrapped:
            return wrapped
        embedded = self.model.get("estimator_rules", {})
        wrapped_embedded = coerce_engineering_value(
            embedded.get("steel", {}).get("unit_weight_formula_value")
        )
        if wrapped_embedded:
            return wrapped_embedded
        return self._estimator().get_unit_weight_formula()

    def get_rounding_precision(self) -> Union[EngineeringValue, int]:
        defaults = self.model.get("project_defaults", {})
        wrapped = coerce_engineering_value(defaults.get("rounding_precision"))
        if wrapped:
            return wrapped
        embedded = self.model.get("estimator_rules", {})
        wrapped_embedded = coerce_engineering_value(
            embedded.get("rounding", {}).get("precision_value")
        )
        if wrapped_embedded:
            return wrapped_embedded
        return self._estimator().get_rounding_precision()

    def _estimator(self) -> EstimatorRuleLoader:
        if self._estimator_loader is None:
            self._estimator_loader = EstimatorRuleLoader.get_instance(
                self._estimator_config_path
            )
            self._estimator_loader.load(self._estimator_config_path)
        return self._estimator_loader

    def get_hook_rule(self) -> List[dict[str, Any]]:
        structural = self.model.get("structural_detailing_rules", {})
        rules = structural.get("hook_rules")
        if rules:
            return list(rules)
        return [
            rule
            for rule in self.model.get("anchorage_rules", [])
            if rule.get("rule_type") == "HOOK_ANCHORAGE"
            or "HOOK" in str(rule.get("description", "")).upper()
        ]

    def get_bend_rule(self) -> List[dict[str, Any]]:
        structural = self.model.get("structural_detailing_rules", {})
        if structural.get("bend_rules"):
            return list(structural["bend_rules"])
        return list(self.model.get("bend_rules", []))

    def get_project_defaults(self) -> dict[str, Any]:
        return dict(self.model.get("project_defaults", {}))

    def get_materials(self) -> dict[str, Any]:
        return dict(self.model.get("materials", {}))

    def get_constants(self) -> dict[str, Any]:
        return dict(self.model.get("engineering_constants", {}))

    def get_default_steel_grade(self) -> Optional[str]:
        defaults = self.get_project_defaults()
        grade = engineering_value_numeric(defaults.get("default_steel_grade"))
        if grade:
            return str(grade)
        materials = self.get_materials()
        default = materials.get("default_steel_grade")
        if isinstance(default, dict):
            return default.get("grade")
        return None

    def get_default_concrete_grade(self) -> Optional[str]:
        defaults = self.get_project_defaults()
        grade = engineering_value_numeric(defaults.get("default_concrete_grade"))
        if grade:
            return str(grade)
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
    ) -> Optional[EngineeringValue]:
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
    ) -> Optional[EngineeringValue]:
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
        raw = table.get(diameter) or table.get(str(diameter))
        if raw is None:
            return None
        coerced = coerce_engineering_value(raw)
        if coerced:
            return coerced
        return EngineeringValue(
            value=raw,
            unit="mm",
            source="GENERAL_NOTES",
            table="TABLE_1",
            confidence=1.0,
            extra={
                "concrete_grade": concrete,
                "diameter_mm": diameter,
            },
        )

    def _normalize_concrete_key(self, grade: str) -> str:
        cleaned = grade.upper().replace(" ", "")
        if cleaned.startswith("M"):
            return cleaned
        return f"M{cleaned}"
