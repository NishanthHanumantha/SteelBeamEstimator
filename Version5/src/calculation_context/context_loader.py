"""Load authoritative engineering inputs for calculation context — Phase I.1."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from src.framing.engineering_ids import RULE_ESTIMATOR, RULE_PROJECT
from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_value import engineering_value_numeric
from src.services.cover_service import CoverService

DEFAULT_RULES_PATH = Path("data/output/phase_e/general_notes_engineering_rules.json")


class CalculationContextLoader:
    """Resolve materials and rule references from authoritative sources."""

    def __init__(self, cache: EngineeringRuleCache) -> None:
        self._cache = cache
        self._cover = CoverService(cache)

    @classmethod
    def from_rules_path(cls, rules_path: Path | None = None) -> "CalculationContextLoader":
        path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        cache = EngineeringRuleCache.get_instance(path)
        return cls(cache)

    @property
    def cache(self) -> EngineeringRuleCache:
        return self._cache

    def resolve_materials(self) -> dict[str, Any]:
        """Materials precedence: General Notes → Project Defaults → Estimator override."""
        materials_block = self._cache.get_materials()
        defaults = self._cache.get_project_defaults()
        constants = self._cache.get_constants()

        concrete_grade, concrete_source = self._resolve_concrete_grade(materials_block, defaults)
        steel_grade, steel_source = self._resolve_steel_grade(materials_block, defaults)

        cover_mm, cover_source = self._resolve_cover(defaults, constants)
        cover_top = cover_mm
        cover_bottom = cover_mm
        cover_side = cover_mm

        return {
            "concrete_grade": concrete_grade,
            "steel_grade": steel_grade,
            "cover_top_mm": cover_top,
            "cover_bottom_mm": cover_bottom,
            "cover_side_mm": cover_side,
            "sources": {
                "concrete_grade": concrete_source,
                "steel_grade": steel_source,
                "cover_mm": cover_source,
            },
        }

    def resolve_rule_references(self) -> dict[str, dict[str, Any]]:
        """Rules precedence: Estimator Rules → General Notes → Project Defaults."""
        model = self._cache.model
        defaults = self._cache.get_project_defaults()
        structural = model.get("structural_detailing_rules", {})
        estimator_embedded = dict(model.get("estimator_rules", {}))

        development_length_table = self._development_length_reference(defaults, model)
        hook_rule = self._rule_bundle_reference(
            "hook_rules",
            self._cache.get_hook_rule(),
            structural.get("hook_rules", []),
            defaults,
            estimator_embedded.get("hook_rules"),
        )
        lap_rule = self._rule_bundle_reference(
            "lap_rules",
            structural.get("lap_rules", model.get("lap_rules", [])),
            structural.get("lap_rules", []),
            defaults,
            estimator_embedded.get("lap_rules"),
        )
        bend_rule = self._rule_bundle_reference(
            "bend_rules",
            self._cache.get_bend_rule(),
            structural.get("bend_rules", []),
            defaults,
            estimator_embedded.get("bend_rules"),
        )
        anchorage_rule = self._rule_bundle_reference(
            "anchorage_rules",
            structural.get("anchorage_rules", model.get("anchorage_rules", [])),
            structural.get("anchorage_rules", []),
            defaults,
            estimator_embedded.get("anchorage_rules"),
        )
        splice_rule = self._rule_bundle_reference(
            "splice_rules",
            structural.get("splice_rules", model.get("splice_rules", [])),
            structural.get("splice_rules", []),
            defaults,
            estimator_embedded.get("splice_rules"),
        )
        estimator_rules = self._estimator_rules_reference()

        return {
            "development_length_table": development_length_table,
            "hook_rule": hook_rule,
            "lap_rule": lap_rule,
            "bend_rule": bend_rule,
            "anchorage_rule": anchorage_rule,
            "splice_rule": splice_rule,
            "estimator_rules": estimator_rules,
        }

    def _resolve_concrete_grade(
        self,
        materials_block: dict[str, Any],
        defaults: dict[str, Any],
    ) -> tuple[Optional[str], str]:
        default_material = materials_block.get("default_concrete_grade")
        if isinstance(default_material, dict) and default_material.get("grade"):
            return str(default_material["grade"]), "GENERAL_NOTES"
        grade = engineering_value_numeric(defaults.get("default_concrete_grade"))
        if grade:
            return str(grade), "PROJECT_DEFAULTS"
        fallback = self._cache.get_default_concrete_grade()
        if fallback:
            return fallback, "PROJECT_DEFAULTS"
        return None, "UNKNOWN"

    def _resolve_steel_grade(
        self,
        materials_block: dict[str, Any],
        defaults: dict[str, Any],
    ) -> tuple[Optional[str], str]:
        default_material = materials_block.get("default_steel_grade")
        if isinstance(default_material, dict) and default_material.get("grade"):
            return str(default_material["grade"]), "GENERAL_NOTES"
        grade = engineering_value_numeric(defaults.get("default_steel_grade"))
        if grade:
            return str(grade), "PROJECT_DEFAULTS"
        fallback = self._cache.get_default_steel_grade()
        if fallback:
            return fallback, "PROJECT_DEFAULTS"
        return None, "UNKNOWN"

    def _resolve_cover(
        self,
        defaults: dict[str, Any],
        constants: dict[str, Any],
    ) -> tuple[Optional[float], str]:
        cover_value = self._cover.get_cover("BEAM")
        if cover_value and cover_value.value is not None:
            return float(cover_value.value), "GENERAL_NOTES"
        default_cover = self._cache.get_default_cover()
        if default_cover and default_cover.value is not None:
            return float(default_cover.value), "PROJECT_DEFAULTS"
        raw = engineering_value_numeric(defaults.get("default_cover_mm"))
        if raw is not None:
            return float(raw), "PROJECT_DEFAULTS"
        raw_constant = engineering_value_numeric(constants.get("default_cover"))
        if raw_constant is not None:
            return float(raw_constant), "PROJECT_DEFAULTS"
        return None, "UNKNOWN"

    @staticmethod
    def _development_length_reference(
        defaults: dict[str, Any],
        model: dict[str, Any],
    ) -> dict[str, Any]:
        matched_key = model.get("matched_development_table_key")
        if matched_key:
            return {
                "reference_id": f"{RULE_PROJECT}#development_tables",
                "active_table_key": str(matched_key),
                "source": "GENERAL_NOTES",
                "rule_count": 0,
            }
        default_table = engineering_value_numeric(defaults.get("default_development_table"))
        if default_table:
            return {
                "reference_id": f"{RULE_PROJECT}#development_tables",
                "active_table_key": str(default_table),
                "source": "PROJECT_DEFAULTS",
                "rule_count": 0,
            }
        return {
            "reference_id": f"{RULE_PROJECT}#development_tables",
            "active_table_key": "",
            "source": "UNKNOWN",
            "rule_count": 0,
        }

    @staticmethod
    def _rule_bundle_reference(
        rule_key: str,
        primary_rules: list,
        general_notes_rules: list,
        defaults: dict[str, Any],
        estimator_rules: Any,
    ) -> dict[str, Any]:
        if isinstance(estimator_rules, list) and estimator_rules:
            return {
                "reference_id": f"{RULE_ESTIMATOR}#structural_detailing_rules.{rule_key}",
                "source": "ESTIMATOR_RULES",
                "rule_count": len(estimator_rules),
            }
        if primary_rules:
            return {
                "reference_id": f"{RULE_PROJECT}#structural_detailing_rules.{rule_key}",
                "source": "GENERAL_NOTES",
                "rule_count": len(primary_rules),
            }
        if general_notes_rules:
            return {
                "reference_id": f"{RULE_PROJECT}#structural_detailing_rules.{rule_key}",
                "source": "GENERAL_NOTES",
                "rule_count": len(general_notes_rules),
            }
        default_rules = defaults.get(rule_key)
        if isinstance(default_rules, list) and default_rules:
            return {
                "reference_id": f"{RULE_PROJECT}#project_defaults.{rule_key}",
                "source": "PROJECT_DEFAULTS",
                "rule_count": len(default_rules),
            }
        return {
            "reference_id": f"{RULE_PROJECT}#structural_detailing_rules.{rule_key}",
            "source": "UNKNOWN",
            "rule_count": 0,
        }

    def _estimator_rules_reference(self) -> dict[str, Any]:
        defaults = self._cache.get_estimator_defaults()
        return {
            "reference_id": RULE_ESTIMATOR,
            "source": "ESTIMATOR_RULES",
            "resolved_scalars": {
                "default_spacer_diameter_mm": engineering_value_numeric(
                    defaults.get("default_spacer_diameter")
                ),
                "default_spacer_spacing_mm": engineering_value_numeric(
                    defaults.get("default_spacer_spacing")
                ),
                "rounding_precision": engineering_value_numeric(
                    defaults.get("rounding_precision")
                ),
            },
        }
