"""Build project defaults and unified ProjectEngineeringKnowledge object."""

from datetime import datetime, timezone
from typing import Any, Optional

from src.general_notes.engineering_value import engineering_value_numeric

PARSER_VERSION = "GeneralNotesParser_v4"
KNOWLEDGE_VERSION = "1.3"
PHASE = "Phase E.3"


def metadata_value(field: Any) -> Optional[str]:
    """Resolve plain value from confidence-wrapped metadata field."""
    if field is None:
        return None
    if isinstance(field, dict) and "value" in field:
        return field.get("value")
    return str(field) if field else None


class ProjectKnowledgeBuilder:
    """Assemble project_defaults and ProjectEngineeringKnowledge."""

    def build_metadata(self) -> dict[str, Any]:
        return {
            "phase": PHASE,
            "knowledge_version": KNOWLEDGE_VERSION,
            "parser_version": PARSER_VERSION,
            "creation_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def build_structural_detailing_rules(self, extracted: dict[str, Any]) -> dict[str, Any]:
        return {
            "cover_rules": extracted.get("cover_tables", []),
            "bend_rules": extracted.get("bend_rules", []),
            "anchorage_rules": extracted.get("anchorage_rules", []),
            "fabrication_rules": extracted.get("fabrication_rules", []),
            "spacer_rules": extracted.get("spacer_rules", {}),
            "hook_rules": [
                rule
                for rule in extracted.get("anchorage_rules", [])
                if rule.get("rule_type") == "HOOK_ANCHORAGE"
                or "HOOK" in str(rule.get("description", "")).upper()
            ],
            "lap_rules": extracted.get("lap_rules", []),
            "coupler_rules": extracted.get("coupler_rules", []),
            "table2_information": extracted.get("table2_information", {}),
            "materials": extracted.get("materials", {}),
        }

    def build_project_defaults(
        self,
        materials: dict[str, Any],
        ld_selection: dict[str, Any],
        cover_tables: list[dict[str, Any]],
        constants: dict[str, Any],
        estimator_defaults: dict[str, Any],
        structural_spacer: dict[str, Any],
    ) -> dict[str, Any]:
        default_steel = materials.get("default_steel_grade", {})
        default_concrete = materials.get("default_concrete_grade", {})
        matched_key = ld_selection.get("matched_table_key")

        beam_cover = self._beam_cover_mm(cover_tables, constants)

        defaults: dict[str, Any] = {
            "default_cover_mm": beam_cover,
            "default_concrete_grade": (
                default_concrete.get("grade") if isinstance(default_concrete, dict) else None
            ),
            "default_steel_grade": (
                default_steel.get("grade") if isinstance(default_steel, dict) else None
            ),
            "default_development_table": matched_key,
            "default_spacer_diameter_mm": estimator_defaults.get(
                "default_spacer_diameter_mm"
            ),
            "default_spacer_spacing_mm": estimator_defaults.get(
                "default_spacer_spacing_mm"
            ),
            "structural_spacer_diameter_mm": structural_spacer.get(
                "spacer_diameter_mm"
            ),
            "structural_spacer_spacing_mm": structural_spacer.get(
                "spacer_spacing_mm"
            ),
            "unit_weight_formula": estimator_defaults.get("unit_weight_formula"),
            "rounding_precision": estimator_defaults.get("rounding_precision"),
        }
        return defaults

    def build_knowledge(
        self,
        project_information: dict[str, Any],
        extracted: dict[str, Any],
        ld_selection: dict[str, Any],
        metadata: dict[str, Any],
        estimator_rules: dict[str, Any],
        estimator_defaults: dict[str, Any],
    ) -> dict[str, Any]:
        structural_spacer = extracted.get("spacer_rules", {})
        structural_detailing_rules = self.build_structural_detailing_rules(extracted)

        project_defaults = self.build_project_defaults(
            extracted.get("materials", {}),
            ld_selection,
            extracted.get("cover_tables", []),
            extracted.get("engineering_constants", {}),
            estimator_defaults,
            structural_spacer,
        )

        active_table = ld_selection.get("active_development_length_table")
        matched_key = ld_selection.get("matched_table_key")

        return {
            "project_information": project_information,
            "project_defaults": project_defaults,
            "materials": extracted.get("materials", {}),
            "structural_detailing_rules": structural_detailing_rules,
            "estimator_rules": estimator_rules,
            "active_development_length_table": active_table,
            "active_development_length_grade": ld_selection.get(
                "active_development_length_grade"
            ),
            "active_development_length_base": ld_selection.get(
                "active_development_length_base"
            ),
            "matched_development_table_key": matched_key,
            "selection_reason": ld_selection.get("selection_reason"),
            "selection_source": ld_selection.get("selection_source"),
            "development_tables": ld_selection.get(
                "resolved_tables",
                extracted.get("development_length_tables", {}),
            ),
            "development_length_tables": ld_selection.get(
                "resolved_tables",
                extracted.get("development_length_tables", {}),
            ),
            "cover_tables": extracted.get("cover_tables", []),
            "engineering_constants": extracted.get("engineering_constants", {}),
            "bend_rules": extracted.get("bend_rules", []),
            "anchorage_rules": extracted.get("anchorage_rules", []),
            "fabrication_rules": extracted.get("fabrication_rules", []),
            "spacer_rules": extracted.get("spacer_rules", {}),
            "table2_information": extracted.get("table2_information", {}),
            "extraction_metadata": extracted.get("extraction_metadata", {}),
            "metadata": metadata,
        }

    def build_engineering_report(
        self,
        knowledge: dict[str, Any],
        traceability: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        defaults = knowledge.get("project_defaults", {})
        structural = knowledge.get("structural_detailing_rules", {})
        structural_spacer = structural.get("spacer_rules", {})
        estimator = knowledge.get("estimator_rules", {})
        project_info = knowledge.get("project_information", {})

        metadata_confidence = {
            key: value
            for key, value in project_info.items()
            if isinstance(value, dict) and "confidence" in value
        }

        return {
            "project": {
                "project_name": metadata_value(project_info.get("project_name")),
                "drawing_number": metadata_value(project_info.get("drawing_number")),
                "source_file": project_info.get("source_file"),
            },
            "project_metadata_confidence": metadata_confidence,
            "steel_grade": engineering_value_numeric(defaults.get("default_steel_grade")),
            "selected_ld_table": engineering_value_numeric(
                defaults.get("default_development_table")
            ),
            "selection_reason": knowledge.get("selection_reason"),
            "concrete_grade": engineering_value_numeric(defaults.get("default_concrete_grade")),
            "beam_cover_mm": engineering_value_numeric(defaults.get("default_cover")),
            "structural_detailing_rules": {
                "spacer_diameter_mm": structural_spacer.get("spacer_diameter_mm"),
                "spacer_spacing_mm": structural_spacer.get("spacer_spacing_mm"),
                "chairs_required": structural_spacer.get("chairs_required", False),
                "largest_bar_rule": structural_spacer.get("largest_bar_rule"),
            },
            "estimator_rules": estimator,
            "estimator_defaults": {
                "spacer_diameter_mm": engineering_value_numeric(
                    defaults.get("default_spacer_diameter")
                ),
                "spacer_spacing_mm": engineering_value_numeric(
                    defaults.get("default_spacer_spacing")
                ),
                "unit_weight_formula": engineering_value_numeric(
                    defaults.get("unit_weight_formula")
                ),
                "rounding_precision": engineering_value_numeric(
                    defaults.get("rounding_precision")
                ),
            },
            "engineering_defaults": defaults,
            "active_ld_sample": self._ld_sample(knowledge),
            "engineering_value_traceability": (
                traceability.get("engineering_value_traceability")
                if traceability
                else None
            ),
            "decision_trail": (
                traceability.get("decision_trail") if traceability else None
            ),
        }

    def build_project_metadata_export(self, knowledge: dict[str, Any]) -> dict[str, Any]:
        project_info = knowledge.get("project_information", {})
        wrapped = {
            key: value
            for key, value in project_info.items()
            if isinstance(value, dict) and "confidence" in value
        }
        return {
            "project_information": wrapped,
            "title_block_block": project_info.get("title_block_block"),
            "title_block_layout": project_info.get("title_block_layout"),
            "source_file": project_info.get("source_file"),
            "source_format": project_info.get("source_format"),
        }

    def _ld_sample(self, knowledge: dict[str, Any]) -> Optional[dict[str, Any]]:
        defaults = knowledge.get("project_defaults", {})
        concrete = engineering_value_numeric(defaults.get("default_concrete_grade"))
        active = knowledge.get("active_development_length_table")
        if not isinstance(active, dict) or not concrete:
            return None
        concrete_table = active.get(concrete)
        if not isinstance(concrete_table, dict):
            return None
        sample_diameter = 20
        raw = concrete_table.get(sample_diameter) or concrete_table.get(
            str(sample_diameter)
        )
        value = engineering_value_numeric(raw)
        if value is None:
            return None
        provenance = raw if isinstance(raw, dict) and "source" in raw else None
        sample = {
            "diameter_mm": sample_diameter,
            "concrete_grade": concrete,
            "development_length_mm": value,
        }
        if provenance:
            sample["provenance"] = provenance
        return sample

    def _beam_cover_mm(
        self,
        cover_tables: list[dict[str, Any]],
        constants: dict[str, Any],
    ) -> Optional[int]:
        for row in cover_tables:
            if row.get("normalized_member_type") == "BEAM":
                return row.get("cover_mm")
        return constants.get("default_beam_cover_mm")
