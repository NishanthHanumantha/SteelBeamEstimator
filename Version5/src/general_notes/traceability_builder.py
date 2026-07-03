"""Engineering decision trail, value registry, and traceability audit (Phase E.3)."""

from __future__ import annotations

from typing import Any, Optional

from src.general_notes.engineering_value import (
    EngineeringValue,
    engineering_value_numeric,
    is_engineering_value,
)
from src.general_notes.project_knowledge_builder import metadata_value


class TraceabilityBuilder:
    """Build decision trails and audit reports for engineering traceability."""

    def build_decision_trail(self, knowledge: dict[str, Any]) -> list[dict[str, Any]]:
        defaults = knowledge.get("project_defaults", {})
        trail: list[dict[str, Any]] = []

        trail.append(
            {
                "decision": "Development Length Table Selection",
                "inputs": {
                    "table2_steel_grade": knowledge.get("active_development_length_grade"),
                    "base_steel_grade": knowledge.get("active_development_length_base"),
                },
                "selected": knowledge.get("matched_development_table_key"),
                "source": "GENERAL_NOTES_TABLE_1",
                "reason": knowledge.get("selection_reason"),
                "selection_method": knowledge.get("selection_source"),
            }
        )

        sample = self._sample_ld(knowledge)
        if sample:
            trail.append(
                {
                    "decision": "Development Length Selection",
                    "inputs": sample.get("inputs", {}),
                    "selected": sample.get("value"),
                    "source": "GENERAL_NOTES_TABLE_1",
                    "reason": knowledge.get("selection_reason"),
                    "provenance": sample.get("provenance"),
                }
            )

        cover = defaults.get("default_cover") or {}
        trail.append(
            {
                "decision": "Default Beam Cover Selection",
                "inputs": {"member": "BEAM"},
                "selected": engineering_value_numeric(cover),
                "source": cover.get("source", "GENERAL_NOTES"),
                "reason": "Lowest normalized BEAM row in cover table",
                "provenance": cover,
            }
        )

        spacer = defaults.get("default_spacer_diameter") or {}
        trail.append(
            {
                "decision": "Estimator Spacer Diameter Selection",
                "inputs": {"methodology": "estimator_rules"},
                "selected": engineering_value_numeric(spacer),
                "source": spacer.get("source", "ESTIMATOR_RULES"),
                "reason": "Configured estimator business rule (not structural detailing note)",
                "provenance": spacer,
            }
        )

        structural_spacer = defaults.get("structural_spacer_diameter") or {}
        trail.append(
            {
                "decision": "Structural Spacer Diameter Extraction",
                "inputs": {"section": structural_spacer.get("section", "9.01")},
                "selected": engineering_value_numeric(structural_spacer),
                "source": structural_spacer.get("source", "GENERAL_NOTES"),
                "reason": "General Notes structural detailing rule",
                "provenance": structural_spacer,
            }
        )

        return trail

    def build_value_registry(self, knowledge: dict[str, Any]) -> dict[str, Any]:
        entries: list[dict[str, Any]] = []

        def register(path: str, payload: Any) -> None:
            if is_engineering_value(payload):
                entries.append({"path": path, **EngineeringValue.from_dict(payload).to_dict()})

        defaults = knowledge.get("project_defaults", {})
        for key, value in defaults.items():
            if is_engineering_value(value):
                register(f"project_defaults.{key}", value)

        for index, row in enumerate(knowledge.get("cover_tables", [])):
            if is_engineering_value(row.get("cover")):
                register(f"cover_tables[{index}].cover", row["cover"])

        for steel, grade_table in (knowledge.get("development_tables") or {}).items():
            if not isinstance(grade_table, dict):
                continue
            for concrete, dia_map in grade_table.items():
                if not isinstance(dia_map, dict):
                    continue
                for diameter, cell in dia_map.items():
                    if is_engineering_value(cell):
                        register(
                            f"development_tables.{steel}.{concrete}.{diameter}",
                            cell,
                        )

        for key, value in knowledge.get("engineering_constants", {}).items():
            if is_engineering_value(value):
                register(f"engineering_constants.{key}", value)

        estimator = knowledge.get("estimator_rules", {})
        spacer = estimator.get("spacer", {})
        if is_engineering_value(spacer.get("diameter")):
            register("estimator_rules.spacer.diameter", spacer["diameter"])
        if is_engineering_value(spacer.get("spacing")):
            register("estimator_rules.spacer.spacing", spacer["spacing"])

        return {
            "entry_count": len(entries),
            "entries": entries,
        }

    def build_traceability_report(self, knowledge: dict[str, Any]) -> dict[str, Any]:
        defaults = knowledge.get("project_defaults", {})
        project_info = knowledge.get("project_information", {})
        sample = self._sample_ld(knowledge)

        chains = [
            self._build_chain(
                label="Beam Cover",
                value=engineering_value_numeric(defaults.get("default_cover")),
                unit="mm",
                steps=[
                    "General Notes",
                    "Cover Table",
                    (defaults.get("default_cover") or {}).get("sheet", "SH-02"),
                    f"Confidence {(defaults.get('default_cover') or {}).get('confidence', 1.0)}",
                ],
                provenance=defaults.get("default_cover"),
            ),
            self._build_chain(
                label="Development Length",
                value=sample.get("value") if sample else None,
                unit="mm",
                steps=[
                    "Table 1",
                    knowledge.get("active_development_length_grade"),
                    sample.get("inputs", {}).get("concrete_grade") if sample else None,
                    f"{sample.get('inputs', {}).get('diameter')} mm Bar" if sample else None,
                    f"Confidence {(sample or {}).get('provenance', {}).get('confidence', 1.0)}",
                ],
                provenance=sample.get("provenance") if sample else None,
            ),
            self._build_chain(
                label="Spacer Diameter (Estimator)",
                value=engineering_value_numeric(defaults.get("default_spacer_diameter")),
                unit="mm",
                steps=[
                    "Estimator Rules",
                    (defaults.get("default_spacer_diameter") or {}).get(
                        "config", "estimator_rules.yaml"
                    ),
                    f"Confidence {(defaults.get('default_spacer_diameter') or {}).get('confidence', 1.0)}",
                ],
                provenance=defaults.get("default_spacer_diameter"),
            ),
            self._build_chain(
                label="Spacer Diameter (Structural)",
                value=engineering_value_numeric(defaults.get("structural_spacer_diameter")),
                unit="mm",
                steps=[
                    "General Notes",
                    f"Section {(defaults.get('structural_spacer_diameter') or {}).get('section', '9.01')}",
                    f"Confidence {(defaults.get('structural_spacer_diameter') or {}).get('confidence', 1.0)}",
                ],
                provenance=defaults.get("structural_spacer_diameter"),
            ),
        ]

        return {
            "project": {
                "name": metadata_value(project_info.get("project_name")),
                "drawing_number": metadata_value(project_info.get("drawing_number")),
            },
            "engineering_value_traceability": chains,
            "decision_trail": self.build_decision_trail(knowledge),
            "value_registry_summary": {
                "entry_count": self.build_value_registry(knowledge)["entry_count"],
            },
        }

    def _build_chain(
        self,
        label: str,
        value: Any,
        unit: Optional[str],
        steps: list[Any],
        provenance: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "label": label,
            "value": value,
            "unit": unit,
            "chain": [step for step in steps if step],
            "provenance": provenance,
        }

    def _sample_ld(self, knowledge: dict[str, Any]) -> Optional[dict[str, Any]]:
        defaults = knowledge.get("project_defaults", {})
        concrete = engineering_value_numeric(defaults.get("default_concrete_grade"))
        diameter = 20
        tables = knowledge.get("development_tables") or knowledge.get(
            "development_length_tables", {}
        )
        matched = knowledge.get("matched_development_table_key")
        if not matched or not concrete:
            return None
        grade_table = tables.get(matched)
        if not isinstance(grade_table, dict):
            return None
        dia_map = grade_table.get(concrete)
        if not isinstance(dia_map, dict):
            return None
        cell = dia_map.get(str(diameter)) or dia_map.get(diameter)
        if cell is None:
            return None
        if is_engineering_value(cell):
            return {
                "value": engineering_value_numeric(cell),
                "inputs": {
                    "steel_grade": knowledge.get("active_development_length_grade"),
                    "concrete_grade": concrete,
                    "diameter": diameter,
                },
                "provenance": cell,
            }
        return {
            "value": cell,
            "inputs": {
                "steel_grade": knowledge.get("active_development_length_grade"),
                "concrete_grade": concrete,
                "diameter": diameter,
            },
            "provenance": EngineeringValue(
                value=cell,
                unit="mm",
                source="GENERAL_NOTES",
                table="TABLE_1",
                sheet="SH-02",
                confidence=1.0,
            ).to_dict(),
        }
