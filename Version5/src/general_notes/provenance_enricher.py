"""Enrich engineering knowledge with provenance metadata (Phase E.3)."""

from __future__ import annotations

from typing import Any, Optional

from src.general_notes.engineering_value import EngineeringValue, engineering_value_numeric


def _sheet_from_position(y: float, x: float = 1600.0) -> str:
    if y >= 850 or x < 900:
        return "SH-01"
    return "SH-02"


def _section_from_text(text: str) -> Optional[str]:
    import re

    match = re.match(r"^\s*(\d+\.\d+)", text or "")
    if match:
        return match.group(1)
    return None


class ProvenanceEnricher:
    """Post-process knowledge model to attach provenance to every engineering value."""

    def enrich(self, knowledge: dict[str, Any]) -> dict[str, Any]:
        ld_meta = {
            "steel_grade": knowledge.get("active_development_length_grade"),
            "base_steel_grade": knowledge.get("active_development_length_base")
            or knowledge.get("matched_development_table_key"),
            "selection_method": knowledge.get("selection_source", "TABLE2_BINDING"),
            "selection_reason": knowledge.get("selection_reason"),
            "matched_table_key": knowledge.get("matched_development_table_key"),
        }

        knowledge["cover_tables"] = [
            self._enrich_cover_row(row) for row in knowledge.get("cover_tables", [])
        ]
        knowledge["development_tables"] = self._enrich_development_tables(
            knowledge.get("development_tables")
            or knowledge.get("development_length_tables", {}),
            ld_meta,
        )
        knowledge["development_length_tables"] = knowledge["development_tables"]

        knowledge["engineering_constants"] = self._enrich_constants(
            knowledge.get("engineering_constants", {}),
            knowledge.get("estimator_rules", {}),
        )
        knowledge["project_defaults"] = self._enrich_project_defaults(
            knowledge,
            ld_meta,
        )

        structural = knowledge.get("structural_detailing_rules", {})
        structural["cover_rules"] = knowledge["cover_tables"]
        structural["bend_rules"] = self._enrich_rules(
            structural.get("bend_rules", knowledge.get("bend_rules", [])),
            rule_kind="BEND",
        )
        structural["anchorage_rules"] = self._enrich_rules(
            structural.get("anchorage_rules", knowledge.get("anchorage_rules", [])),
            rule_kind="ANCHORAGE",
        )
        structural["fabrication_rules"] = self._enrich_rules(
            structural.get("fabrication_rules", knowledge.get("fabrication_rules", [])),
            rule_kind="FABRICATION",
        )
        structural["hook_rules"] = self._enrich_rules(
            structural.get("hook_rules", []),
            rule_kind="HOOK",
        )
        structural["spacer_rules"] = self._enrich_spacer_rules(
            structural.get("spacer_rules", knowledge.get("spacer_rules", {}))
        )
        knowledge["structural_detailing_rules"] = structural

        knowledge["bend_rules"] = structural["bend_rules"]
        knowledge["anchorage_rules"] = structural["anchorage_rules"]
        knowledge["fabrication_rules"] = structural["fabrication_rules"]
        knowledge["spacer_rules"] = structural["spacer_rules"]

        knowledge["estimator_rules"] = self._enrich_estimator_rules(
            knowledge.get("estimator_rules", {})
        )
        knowledge["materials"] = self._enrich_materials(knowledge.get("materials", {}))

        matched = knowledge.get("matched_development_table_key")
        if matched and matched in knowledge.get("development_tables", {}):
            knowledge["active_development_length_table"] = knowledge["development_tables"][
                matched
            ]

        return knowledge

    def _enrich_cover_row(self, row: dict[str, Any]) -> dict[str, Any]:
        y = float(row.get("y_position", 0))
        member = row.get("normalized_member_type") or row.get("member_type")
        cover_mm = row.get("cover_mm")
        provenance = EngineeringValue(
            value=cover_mm,
            unit="mm",
            source="GENERAL_NOTES",
            table="COVER_TABLE",
            sheet=_sheet_from_position(y),
            confidence=1.0,
            extra={"member": member},
        ).to_dict()
        enriched = dict(row)
        enriched["cover"] = provenance
        enriched["cover_mm"] = cover_mm
        enriched["provenance"] = provenance
        return enriched

    def _enrich_development_tables(
        self,
        tables: dict[str, Any],
        ld_meta: dict[str, Any],
    ) -> dict[str, Any]:
        enriched: dict[str, Any] = {}
        matched = ld_meta.get("matched_table_key")
        for steel_key, grade_table in tables.items():
            if not isinstance(grade_table, dict):
                enriched[steel_key] = grade_table
                continue
            enriched_grade: dict[str, Any] = {}
            for concrete, diameter_map in grade_table.items():
                if not isinstance(diameter_map, dict):
                    enriched_grade[concrete] = diameter_map
                    continue
                enriched_concrete: dict[str, Any] = {}
                for diameter, raw_value in diameter_map.items():
                    if is_wrapped_value(raw_value):
                        enriched_concrete[str(diameter)] = raw_value
                        continue
                    enriched_concrete[str(diameter)] = EngineeringValue(
                        value=raw_value,
                        unit="mm",
                        source="GENERAL_NOTES",
                        table="TABLE_1",
                        sheet="SH-02",
                        confidence=1.0,
                        extra={
                            "steel_grade": ld_meta.get("steel_grade"),
                            "base_steel_grade": ld_meta.get("base_steel_grade")
                            or steel_key,
                            "concrete_grade": concrete,
                            "diameter_mm": int(diameter),
                            "selection_method": ld_meta.get("selection_method"),
                            "physical_table_key": steel_key,
                            "active_table_key": matched,
                        },
                    ).to_dict()
                enriched_grade[concrete] = enriched_concrete
            enriched[steel_key] = enriched_grade
        return enriched

    def _enrich_constants(
        self,
        constants: dict[str, Any],
        estimator_rules: dict[str, Any],
    ) -> dict[str, Any]:
        enriched: dict[str, Any] = dict(constants)
        estimator_source = estimator_rules.get("source", "config/estimator_rules.yaml")

        if "default_beam_cover_mm" in constants:
            enriched["default_cover"] = EngineeringValue(
                value=constants["default_beam_cover_mm"],
                unit="mm",
                source="GENERAL_NOTES",
                table="COVER_TABLE",
                sheet="SH-02",
                confidence=1.0,
                extra={"member": "BEAM"},
            ).to_dict()

        if "steel_density_kg_per_m3" in constants:
            enriched["steel_density"] = EngineeringValue(
                value=constants["steel_density_kg_per_m3"],
                unit="kg/m³",
                source="ENGINEERING_STANDARD",
                confidence=1.0,
                extra={"reference": "IS Standard"},
            ).to_dict()

        formula = estimator_rules.get("steel", {}).get("unit_weight_formula") or constants.get(
            "unit_weight_formula"
        )
        if formula:
            enriched["unit_weight_formula"] = EngineeringValue(
                value=formula,
                source="ESTIMATOR_RULES",
                confidence=1.0,
                extra={"config": estimator_source},
            ).to_dict()

        if "minimum_lap_mm" in constants:
            enriched["minimum_lap"] = EngineeringValue(
                value=constants["minimum_lap_mm"],
                unit="mm",
                source="GENERAL_NOTES",
                sheet="SH-02",
                confidence=0.99,
                extra={"section": "fabrication_rules"},
            ).to_dict()

        return enriched

    def _enrich_project_defaults(
        self,
        knowledge: dict[str, Any],
        ld_meta: dict[str, Any],
    ) -> dict[str, Any]:
        raw = dict(knowledge.get("project_defaults", {}))
        estimator_rules = knowledge.get("estimator_rules", {})
        estimator_source = estimator_rules.get("source", "config/estimator_rules.yaml")
        structural = knowledge.get("structural_detailing_rules", {})
        structural_spacer = structural.get("spacer_rules", knowledge.get("spacer_rules", {}))

        beam_row = next(
            (
                row
                for row in knowledge.get("cover_tables", [])
                if row.get("normalized_member_type") == "BEAM"
            ),
            None,
        )
        cover_prov = (
            beam_row.get("cover")
            if beam_row and isinstance(beam_row.get("cover"), dict)
            else EngineeringValue(
                value=engineering_value_numeric(raw.get("default_cover_mm")),
                unit="mm",
                source="GENERAL_NOTES",
                table="COVER_TABLE",
                sheet="SH-02",
                confidence=1.0,
                extra={"member": "BEAM"},
            ).to_dict()
        )

        steel_grade = engineering_value_numeric(raw.get("default_steel_grade"))
        concrete_grade = engineering_value_numeric(raw.get("default_concrete_grade"))

        enriched: dict[str, Any] = {
            **raw,
            "default_cover": cover_prov,
            "default_concrete_grade": EngineeringValue(
                value=concrete_grade,
                source="GENERAL_NOTES",
                table="TABLE_2",
                sheet="SH-02",
                confidence=1.0,
            ).to_dict(),
            "default_steel_grade": EngineeringValue(
                value=steel_grade,
                source="GENERAL_NOTES",
                table="TABLE_2",
                sheet="SH-02",
                confidence=1.0,
                extra={
                    "base_steel_grade": ld_meta.get("base_steel_grade"),
                    "selection_method": ld_meta.get("selection_method"),
                },
            ).to_dict(),
            "default_development_table": EngineeringValue(
                value=raw.get("default_development_table"),
                source="GENERAL_NOTES",
                table="TABLE_1",
                sheet="SH-02",
                confidence=1.0,
                extra={
                    "selection_reason": ld_meta.get("selection_reason"),
                    "steel_grade": steel_grade,
                },
            ).to_dict(),
            "default_spacer_diameter": EngineeringValue(
                value=raw.get("default_spacer_diameter_mm"),
                unit="mm",
                source="ESTIMATOR_RULES",
                confidence=1.0,
                extra={"config": estimator_source},
            ).to_dict(),
            "default_spacer_spacing": EngineeringValue(
                value=raw.get("default_spacer_spacing_mm"),
                unit="mm",
                source="ESTIMATOR_RULES",
                confidence=1.0,
                extra={"config": estimator_source},
            ).to_dict(),
            "structural_spacer_diameter": EngineeringValue(
                value=raw.get("structural_spacer_diameter_mm")
                or structural_spacer.get("spacer_diameter_mm"),
                unit="mm",
                source="GENERAL_NOTES",
                sheet="SH-02",
                confidence=1.0,
                extra={"section": structural_spacer.get("section_reference", "9.01")},
            ).to_dict(),
            "unit_weight_formula": EngineeringValue(
                value=raw.get("unit_weight_formula"),
                source="ESTIMATOR_RULES",
                confidence=1.0,
                extra={"config": estimator_source},
            ).to_dict(),
            "rounding_precision": EngineeringValue(
                value=raw.get("rounding_precision"),
                source="ESTIMATOR_RULES",
                confidence=1.0,
                extra={"config": estimator_source},
            ).to_dict(),
        }

        enriched["default_cover_mm"] = engineering_value_numeric(cover_prov)
        enriched["default_spacer_diameter_mm"] = engineering_value_numeric(
            enriched["default_spacer_diameter"]
        )
        enriched["default_spacer_spacing_mm"] = engineering_value_numeric(
            enriched["default_spacer_spacing"]
        )
        enriched["structural_spacer_diameter_mm"] = engineering_value_numeric(
            enriched["structural_spacer_diameter"]
        )
        return enriched

    def _enrich_spacer_rules(self, spacer_rules: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(spacer_rules)
        section = spacer_rules.get("section_reference", "9.01")
        if spacer_rules.get("spacer_diameter_mm") is not None:
            prov = EngineeringValue(
                value=spacer_rules["spacer_diameter_mm"],
                unit="mm",
                source="GENERAL_NOTES",
                sheet="SH-02",
                confidence=1.0,
                extra={"section": section},
            ).to_dict()
            enriched["spacer_diameter"] = prov
        if spacer_rules.get("spacer_spacing_mm") is not None:
            enriched["spacer_spacing"] = EngineeringValue(
                value=spacer_rules["spacer_spacing_mm"],
                unit="mm",
                source="GENERAL_NOTES",
                sheet="SH-02",
                confidence=1.0,
                extra={"section": section},
            ).to_dict()
        return enriched

    def _enrich_estimator_rules(self, estimator_rules: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(estimator_rules)
        config = estimator_rules.get("source", "config/estimator_rules.yaml")
        spacer = dict(estimator_rules.get("spacer", {}))
        if spacer:
            spacer["diameter"] = EngineeringValue(
                value=spacer.get("diameter_mm"),
                unit="mm",
                source="ESTIMATOR_RULES",
                confidence=1.0,
                extra={"config": config},
            ).to_dict()
            spacer["spacing"] = EngineeringValue(
                value=spacer.get("spacing_mm"),
                unit="mm",
                source="ESTIMATOR_RULES",
                confidence=1.0,
                extra={"config": config},
            ).to_dict()
            enriched["spacer"] = spacer
        steel = dict(estimator_rules.get("steel", {}))
        if steel.get("unit_weight_formula"):
            steel["unit_weight_formula_value"] = EngineeringValue(
                value=steel["unit_weight_formula"],
                source="ESTIMATOR_RULES",
                confidence=1.0,
                extra={"config": config},
            ).to_dict()
            enriched["steel"] = steel
        rounding = dict(estimator_rules.get("rounding", {}))
        if "precision" in rounding:
            rounding["precision_value"] = EngineeringValue(
                value=rounding["precision"],
                source="ESTIMATOR_RULES",
                confidence=1.0,
                extra={"config": config},
            ).to_dict()
            enriched["rounding"] = rounding
        return enriched

    def _enrich_materials(self, materials: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(materials)
        default_steel = materials.get("default_steel_grade")
        if isinstance(default_steel, dict) and default_steel.get("grade"):
            enriched["default_steel_grade"] = {
                **default_steel,
                "provenance": EngineeringValue(
                    value=default_steel.get("grade"),
                    source="GENERAL_NOTES",
                    table="TABLE_2",
                    sheet="SH-02",
                    confidence=1.0,
                    extra={"base_grade": default_steel.get("base_grade")},
                ).to_dict(),
            }
        default_concrete = materials.get("default_concrete_grade")
        if isinstance(default_concrete, dict) and default_concrete.get("grade"):
            enriched["default_concrete_grade"] = {
                **default_concrete,
                "provenance": EngineeringValue(
                    value=default_concrete.get("grade"),
                    source="GENERAL_NOTES",
                    table="TABLE_2",
                    sheet="SH-02",
                    confidence=1.0,
                ).to_dict(),
            }
        return enriched

    def _enrich_rules(
        self,
        rules: list[dict[str, Any]],
        rule_kind: str,
    ) -> list[dict[str, Any]]:
        enriched_rules: list[dict[str, Any]] = []
        for rule in rules:
            item = dict(rule)
            description = str(rule.get("description") or rule.get("source_text", ""))
            section = _section_from_text(description)
            item["provenance"] = EngineeringValue(
                value=rule.get("multiplier_db")
                or rule.get("minimum_lap_mm")
                or rule.get("angle")
                or description[:120],
                source="GENERAL_NOTES",
                sheet="SH-02",
                confidence=0.99 if section else 0.95,
                extra={
                    "section": section,
                    "rule_type": rule.get("rule_type"),
                    "rule_kind": rule_kind,
                },
            ).to_dict()
            if rule.get("rule_type") == "BEND_MULTIPLIER":
                item["hook_multiplier"] = rule.get("multiplier_db")
            enriched_rules.append(item)
        return enriched_rules


def is_wrapped_value(data: Any) -> bool:
    return (
        isinstance(data, dict)
        and "value" in data
        and "source" in data
        and "confidence" in data
    )
