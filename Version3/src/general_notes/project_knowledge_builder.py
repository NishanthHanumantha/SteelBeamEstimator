"""Build project defaults and unified ProjectEngineeringKnowledge object."""

from datetime import datetime, timezone
from typing import Any, Optional

PARSER_VERSION = "GeneralNotesParser_v2"
KNOWLEDGE_VERSION = "1.1"
PHASE = "Phase E.1"


class ProjectKnowledgeBuilder:
    """Assemble project_defaults and ProjectEngineeringKnowledge."""

    def build_metadata(self) -> dict[str, Any]:
        return {
            "phase": PHASE,
            "knowledge_version": KNOWLEDGE_VERSION,
            "parser_version": PARSER_VERSION,
            "creation_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def build_project_defaults(
        self,
        materials: dict[str, Any],
        ld_selection: dict[str, Any],
        cover_tables: list[dict[str, Any]],
        spacer_rules: dict[str, Any],
        constants: dict[str, Any],
    ) -> dict[str, Any]:
        default_steel = materials.get("default_steel_grade", {})
        default_concrete = materials.get("default_concrete_grade", {})
        matched_key = ld_selection.get("matched_table_key")

        beam_cover = self._beam_cover_mm(cover_tables, constants)
        spacer_diameter = spacer_rules.get("spacer_diameter_mm")
        spacer_spacing = spacer_rules.get("spacer_spacing_mm")

        defaults: dict[str, Any] = {
            "default_cover_mm": beam_cover,
            "default_concrete_grade": (
                default_concrete.get("grade") if isinstance(default_concrete, dict) else None
            ),
            "default_steel_grade": (
                default_steel.get("grade") if isinstance(default_steel, dict) else None
            ),
            "default_development_table": matched_key,
            "default_spacer_diameter_mm": spacer_diameter,
            "default_spacer_spacing_mm": spacer_spacing,
        }
        return defaults

    def build_knowledge(
        self,
        project_information: dict[str, Any],
        extracted: dict[str, Any],
        ld_selection: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        project_defaults = self.build_project_defaults(
            extracted.get("materials", {}),
            ld_selection,
            extracted.get("cover_tables", []),
            extracted.get("spacer_rules", {}),
            extracted.get("engineering_constants", {}),
        )

        active_table = ld_selection.get("active_development_length_table")
        matched_key = ld_selection.get("matched_table_key")

        return {
            "project_information": project_information,
            "project_defaults": project_defaults,
            "materials": extracted.get("materials", {}),
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

    def build_engineering_report(self, knowledge: dict[str, Any]) -> dict[str, Any]:
        defaults = knowledge.get("project_defaults", {})
        spacer = knowledge.get("spacer_rules", {})
        return {
            "project": {
                "drawing_number": knowledge.get("project_information", {}).get(
                    "drawing_number"
                ),
                "source_file": knowledge.get("project_information", {}).get(
                    "source_file"
                ),
            },
            "steel_grade": defaults.get("default_steel_grade"),
            "selected_ld_table": defaults.get("default_development_table"),
            "selection_reason": knowledge.get("selection_reason"),
            "concrete_grade": defaults.get("default_concrete_grade"),
            "beam_cover_mm": defaults.get("default_cover_mm"),
            "spacer_rules": {
                "diameter_mm": spacer.get("spacer_diameter_mm"),
                "spacing_mm": spacer.get("spacer_spacing_mm"),
                "chairs_required": spacer.get("chairs_required", False),
                "largest_bar_rule": spacer.get("largest_bar_rule"),
            },
            "engineering_defaults": defaults,
            "active_ld_sample": self._ld_sample(knowledge),
        }

    def _ld_sample(self, knowledge: dict[str, Any]) -> Optional[dict[str, Any]]:
        defaults = knowledge.get("project_defaults", {})
        concrete = defaults.get("default_concrete_grade")
        active = knowledge.get("active_development_length_table")
        if not isinstance(active, dict) or not concrete:
            return None
        concrete_table = active.get(concrete)
        if not isinstance(concrete_table, dict):
            return None
        sample_diameter = 20
        value = concrete_table.get(sample_diameter) or concrete_table.get(
            str(sample_diameter)
        )
        if value is None:
            return None
        return {
            "diameter_mm": sample_diameter,
            "concrete_grade": concrete,
            "development_length_mm": value,
        }

    def _beam_cover_mm(
        self,
        cover_tables: list[dict[str, Any]],
        constants: dict[str, Any],
    ) -> Optional[int]:
        for row in cover_tables:
            if row.get("normalized_member_type") == "BEAM":
                return row.get("cover_mm")
        return constants.get("default_beam_cover_mm")
