"""Validate extracted General Notes engineering knowledge."""

from typing import Any, Dict, List, Optional

from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class EngineeringRuleValidator:
    """Verify Phase E.1 outputs meet completeness requirements."""

    def validate(
        self,
        model: dict[str, Any],
        cache: Optional[EngineeringRuleCache] = None,
    ) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []

        ld_tables = model.get("development_length_tables", {})
        checks.append(self._check_ld_tables(ld_tables))
        checks.append(self._check_active_ld_table(model))
        checks.append(self._check_steel_grade_selection(model))
        checks.append(self._check_development_lookup(model, cache))
        checks.append(self._check_cover_tables(model.get("cover_tables", [])))
        checks.append(self._check_cover_lookup(model, cache))
        checks.append(self._check_material_grades(model.get("materials", {})))
        checks.append(self._check_project_defaults(model.get("project_defaults", {})))
        checks.append(self._check_spacer_rules(model.get("spacer_rules", {})))
        checks.append(self._check_member_normalization(model.get("cover_tables", [])))
        checks.append(self._check_metadata(model.get("project_information", {})))
        checks.append(self._check_constants(model.get("engineering_constants", {})))
        checks.append(self._check_bend_rules(model.get("bend_rules", [])))
        checks.append(self._check_anchorage_rules(model.get("anchorage_rules", [])))
        checks.append(self._check_knowledge_object(model))

        failed = [c for c in checks if c["status"] == "FAIL"]
        status = "PASS" if not failed else "FAIL"

        return {
            "status": status,
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
            },
        }

    def _check_ld_tables(self, ld_tables: dict[str, Any]) -> dict[str, Any]:
        ok = bool(ld_tables) and any(
            isinstance(grade_table, dict) and len(grade_table) > 0
            for grade_table in ld_tables.values()
        )
        return {
            "name": "Development Tables",
            "status": "PASS" if ok else "FAIL",
            "steel_grade_count": len(ld_tables),
        }

    def _check_active_ld_table(self, model: dict[str, Any]) -> dict[str, Any]:
        active = model.get("active_development_length_table")
        matched = model.get("matched_development_table_key")
        ok = isinstance(active, dict) and bool(active) and matched is not None
        return {
            "name": "Active Development Table",
            "status": "PASS" if ok else "FAIL",
            "matched_table_key": matched,
            "selection_reason": model.get("selection_reason"),
        }

    def _check_steel_grade_selection(self, model: dict[str, Any]) -> dict[str, Any]:
        table2 = model.get("table2_information", {})
        defaults = model.get("project_defaults", {})
        steel = defaults.get("default_steel_grade") or table2.get(
            "table2_steel_grade", {}
        ).get("grade")
        ok = steel is not None
        return {
            "name": "Steel Grade Selection",
            "status": "PASS" if ok else "FAIL",
            "default_steel_grade": steel,
            "table2_source": table2.get("table2_steel_grade"),
        }

    def _check_development_lookup(
        self,
        model: dict[str, Any],
        cache: Optional[EngineeringRuleCache],
    ) -> dict[str, Any]:
        if cache is None:
            return {
                "name": "Development Lookup",
                "status": "FAIL",
                "reason": "cache not provided",
            }
        concrete = model.get("project_defaults", {}).get("default_concrete_grade", "M30")
        result = cache.get_active_ld(20, concrete)
        ok = result is not None and result.get("value_mm") is not None
        return {
            "name": "Development Lookup",
            "status": "PASS" if ok else "FAIL",
            "sample": result,
        }

    def _check_cover_tables(self, cover_tables: list) -> dict[str, Any]:
        ok = len(cover_tables) >= 5
        return {
            "name": "Cover Tables",
            "status": "PASS" if ok else "FAIL",
            "row_count": len(cover_tables),
        }

    def _check_cover_lookup(
        self,
        model: dict[str, Any],
        cache: Optional[EngineeringRuleCache],
    ) -> dict[str, Any]:
        if cache is None:
            return {"name": "Cover Lookup", "status": "FAIL"}
        cover = cache.get_cover("BEAM")
        ok = cover is not None
        return {
            "name": "Cover Lookup",
            "status": "PASS" if ok else "FAIL",
            "beam_cover": cover,
        }

    def _check_material_grades(self, materials: dict[str, Any]) -> dict[str, Any]:
        steel = materials.get("steel_grades", [])
        concrete = materials.get("concrete_grades", [])
        ok = len(steel) >= 1 and len(concrete) >= 1
        return {
            "name": "Material Grades",
            "status": "PASS" if ok else "FAIL",
            "steel_grade_count": len(steel),
            "concrete_grade_count": len(concrete),
        }

    def _check_project_defaults(self, defaults: dict[str, Any]) -> dict[str, Any]:
        required = (
            "default_steel_grade",
            "default_concrete_grade",
            "default_development_table",
        )
        ok = all(defaults.get(key) for key in required)
        return {
            "name": "Project Defaults",
            "status": "PASS" if ok else "FAIL",
            "defaults": defaults,
        }

    def _check_spacer_rules(self, spacer_rules: dict[str, Any]) -> dict[str, Any]:
        rules = spacer_rules.get("rules", [])
        ok = bool(rules) or spacer_rules.get("chairs_required", False)
        return {
            "name": "Spacer Rules",
            "status": "PASS" if ok else "FAIL",
            "chairs_required": spacer_rules.get("chairs_required", False),
        }

    def _check_member_normalization(self, cover_tables: list) -> dict[str, Any]:
        normalized = sum(
            1 for row in cover_tables if row.get("normalized_member_type")
        )
        ok = normalized >= 5
        return {
            "name": "Member Normalization",
            "status": "PASS" if ok else "FAIL",
            "normalized_count": normalized,
        }

    def _check_metadata(self, project_info: dict[str, Any]) -> dict[str, Any]:
        has_drawing = bool(project_info.get("drawing_number"))
        has_sheets = bool(project_info.get("sheet_numbers"))
        has_source = bool(project_info.get("source_file"))
        ok = has_drawing and has_sheets and has_source
        return {
            "name": "Metadata",
            "status": "PASS" if ok else "FAIL",
            "drawing_number": project_info.get("drawing_number"),
            "revision": project_info.get("revision"),
            "company": project_info.get("company"),
        }

    def _check_constants(self, constants: dict[str, Any]) -> dict[str, Any]:
        ok = bool(constants) and "unit_weight_formula" in constants
        return {
            "name": "Engineering Constants",
            "status": "PASS" if ok else "FAIL",
            "constant_count": len(constants),
        }

    def _check_bend_rules(self, bend_rules: list) -> dict[str, Any]:
        ok = len(bend_rules) >= 1
        return {
            "name": "Bend Rules",
            "status": "PASS" if ok else "FAIL",
            "rule_count": len(bend_rules),
        }

    def _check_anchorage_rules(self, anchorage_rules: list) -> dict[str, Any]:
        ok = len(anchorage_rules) >= 1
        return {
            "name": "Anchorage Rules",
            "status": "PASS" if ok else "FAIL",
            "rule_count": len(anchorage_rules),
        }

    def _check_knowledge_object(self, model: dict[str, Any]) -> dict[str, Any]:
        required = (
            "project_information",
            "project_defaults",
            "materials",
            "active_development_length_table",
            "development_length_tables",
            "cover_tables",
            "metadata",
        )
        ok = all(key in model for key in required)
        return {
            "name": "Knowledge Object",
            "status": "PASS" if ok else "FAIL",
            "phase": model.get("metadata", {}).get("phase"),
        }
