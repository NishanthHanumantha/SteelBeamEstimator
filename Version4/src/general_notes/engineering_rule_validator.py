"""Validate extracted General Notes engineering knowledge."""

from typing import Any, Dict, List, Optional

from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_value import (
    EngineeringValue,
    engineering_value_numeric,
    is_engineering_value,
)
from src.general_notes.metadata_validator import is_valid_project_name
from src.general_notes.project_knowledge_builder import metadata_value


class EngineeringRuleValidator:
    """Verify Phase E.3 outputs meet completeness and traceability requirements."""

    def validate(
        self,
        model: dict[str, Any],
        cache: Optional[EngineeringRuleCache] = None,
    ) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []

        ld_tables = model.get("development_tables") or model.get(
            "development_length_tables", {}
        )
        checks.append(self._check_ld_tables(ld_tables))
        checks.append(self._check_active_ld_table(model))
        checks.append(self._check_steel_grade_selection(model))
        checks.append(self._check_development_lookup(model, cache))
        checks.append(self._check_cover_tables(model.get("cover_tables", [])))
        checks.append(self._check_cover_lookup(model, cache))
        checks.append(self._check_material_grades(model.get("materials", {})))
        checks.append(self._check_project_defaults(model.get("project_defaults", {})))
        checks.append(self._check_structural_rules(model))
        checks.append(self._check_estimator_rules(model, cache))
        checks.append(self._check_spacer_rules_dual(model, cache))
        checks.append(self._check_member_normalization(model.get("cover_tables", [])))
        checks.append(self._check_metadata(model.get("project_information", {})))
        checks.append(self._check_project_name(model.get("project_information", {})))
        checks.append(self._check_metadata_confidence(model.get("project_information", {})))
        checks.append(self._check_constants(model.get("engineering_constants", {})))
        checks.append(self._check_bend_rules(model.get("bend_rules", [])))
        checks.append(self._check_anchorage_rules(model.get("anchorage_rules", [])))
        checks.append(self._check_knowledge_object(model))
        checks.append(self._check_engineering_provenance(model))
        checks.append(self._check_development_traceability(model, cache))
        checks.append(self._check_cover_traceability(model, cache))
        checks.append(self._check_estimator_traceability(model, cache))
        checks.append(self._check_decision_trail(model))
        checks.append(self._check_audit_report(model))

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
        if not table2:
            structural = model.get("structural_detailing_rules", {})
            table2 = structural.get("table2_information", {})
        defaults = model.get("project_defaults", {})
        steel = engineering_value_numeric(defaults.get("default_steel_grade")) or table2.get(
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
        concrete = engineering_value_numeric(
            model.get("project_defaults", {}).get("default_concrete_grade")
        ) or "M30"
        result = cache.get_active_ld(20, str(concrete))
        ok = result is not None and engineering_value_numeric(result) is not None
        sample = result.to_dict() if isinstance(result, EngineeringValue) else result
        return {
            "name": "Development Lookup",
            "status": "PASS" if ok else "FAIL",
            "sample": sample,
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
        ok = cover is not None and engineering_value_numeric(cover) is not None
        beam_cover = cover.to_dict() if isinstance(cover, EngineeringValue) else cover
        return {
            "name": "Cover Lookup",
            "status": "PASS" if ok else "FAIL",
            "beam_cover": beam_cover,
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
            "default_spacer_diameter_mm",
            "default_spacer_spacing_mm",
        )
        ok = all(defaults.get(key) is not None for key in required)
        return {
            "name": "Project Defaults",
            "status": "PASS" if ok else "FAIL",
            "defaults": defaults,
        }

    def _check_structural_rules(self, model: dict[str, Any]) -> dict[str, Any]:
        structural = model.get("structural_detailing_rules", {})
        spacer = structural.get("spacer_rules", model.get("spacer_rules", {}))
        ok = bool(structural) and (
            bool(spacer.get("rules"))
            or spacer.get("spacer_diameter_mm") is not None
            or spacer.get("chairs_required", False)
        )
        return {
            "name": "Structural Rules",
            "status": "PASS" if ok else "FAIL",
            "structural_spacer_diameter_mm": spacer.get("spacer_diameter_mm"),
        }

    def _check_estimator_rules(
        self,
        model: dict[str, Any],
        cache: Optional[EngineeringRuleCache],
    ) -> dict[str, Any]:
        embedded = model.get("estimator_rules", {})
        ok = bool(embedded.get("spacer")) and bool(embedded.get("steel"))
        if not ok and cache is not None:
            try:
                spacer = cache.get_estimator_spacer()
                ok = engineering_value_numeric(spacer) is not None
            except Exception:
                ok = False
        return {
            "name": "Estimator Rules",
            "status": "PASS" if ok else "FAIL",
            "estimator_rules": embedded,
        }

    def _check_spacer_rules_dual(
        self,
        model: dict[str, Any],
        cache: Optional[EngineeringRuleCache],
    ) -> dict[str, Any]:
        structural = model.get("structural_detailing_rules", {})
        structural_spacer = structural.get("spacer_rules", model.get("spacer_rules", {}))
        defaults = model.get("project_defaults", {})
        structural_dia = structural_spacer.get("spacer_diameter_mm") or defaults.get(
            "structural_spacer_diameter_mm"
        )
        estimator_dia = defaults.get("default_spacer_diameter_mm")
        if cache is not None:
            estimator = cache.get_estimator_spacer()
            estimator_dia = estimator_dia or engineering_value_numeric(estimator)
        ok = structural_dia is not None and estimator_dia is not None
        return {
            "name": "Spacer Rules",
            "status": "PASS" if ok else "FAIL",
            "structural_spacer_diameter_mm": structural_dia,
            "estimator_spacer_diameter_mm": estimator_dia,
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
        drawing_number = metadata_value(project_info.get("drawing_number"))
        has_drawing = bool(drawing_number)
        has_sheets = bool(project_info.get("sheet_numbers"))
        has_source = bool(project_info.get("source_file"))
        ok = has_drawing and has_sheets and has_source
        return {
            "name": "Metadata",
            "status": "PASS" if ok else "FAIL",
            "drawing_number": drawing_number,
            "revision": metadata_value(project_info.get("revision")),
            "company": metadata_value(project_info.get("company")),
        }

    def _check_project_name(self, project_info: dict[str, Any]) -> dict[str, Any]:
        field = project_info.get("project_name", {})
        name = metadata_value(field)
        source = field.get("source") if isinstance(field, dict) else None
        ok = (
            name is not None
            and is_valid_project_name(name)
            and source == "TITLE_BLOCK"
        )
        return {
            "name": "Project Name",
            "status": "PASS" if ok else "FAIL",
            "project_name": name,
            "source": source,
        }

    def _check_metadata_confidence(self, project_info: dict[str, Any]) -> dict[str, Any]:
        required = ("project_name", "drawing_number", "company", "consultant")
        wrapped = [
            key
            for key in required
            if isinstance(project_info.get(key), dict)
            and "confidence" in project_info[key]
            and "source" in project_info[key]
        ]
        ok = len(wrapped) >= 3 and project_info.get("project_name", {}).get(
            "confidence", 0
        ) >= 0.9
        return {
            "name": "Confidence",
            "status": "PASS" if ok else "FAIL",
            "wrapped_fields": wrapped,
        }

    def _check_constants(self, constants: dict[str, Any]) -> dict[str, Any]:
        formula = constants.get("unit_weight_formula")
        ok = bool(constants) and (
            is_engineering_value(formula) or formula is not None
        )
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
            "structural_detailing_rules",
            "estimator_rules",
            "development_tables",
            "cover_tables",
            "engineering_constants",
            "metadata",
        )
        ok = all(key in model for key in required)
        return {
            "name": "Knowledge Object",
            "status": "PASS" if ok else "FAIL",
            "phase": model.get("metadata", {}).get("phase"),
        }

    def _check_engineering_provenance(self, model: dict[str, Any]) -> dict[str, Any]:
        defaults = model.get("project_defaults", {})
        required = (
            "default_cover",
            "default_spacer_diameter",
            "default_steel_grade",
            "default_concrete_grade",
        )
        wrapped = sum(1 for key in required if is_engineering_value(defaults.get(key)))
        ok = wrapped >= len(required)
        return {
            "name": "Engineering Provenance",
            "status": "PASS" if ok else "FAIL",
            "wrapped_defaults": wrapped,
        }

    def _check_development_traceability(
        self,
        model: dict[str, Any],
        cache: Optional[EngineeringRuleCache],
    ) -> dict[str, Any]:
        tables = model.get("development_tables") or model.get("development_length_tables", {})
        sample = None
        for grade_table in tables.values():
            if not isinstance(grade_table, dict):
                continue
            for dia_map in grade_table.values():
                if not isinstance(dia_map, dict):
                    continue
                for cell in dia_map.values():
                    if is_engineering_value(cell):
                        sample = cell
                        break
                if sample:
                    break
            if sample:
                break
        cache_ok = False
        if cache is not None:
            concrete = engineering_value_numeric(
                model.get("project_defaults", {}).get("default_concrete_grade")
            ) or "M30"
            ld = cache.get_active_ld(20, str(concrete))
            cache_ok = isinstance(ld, EngineeringValue) and is_engineering_value(ld.to_dict())
        ok = sample is not None and sample.get("table") == "TABLE_1" and cache_ok
        return {
            "name": "Development Traceability",
            "status": "PASS" if ok else "FAIL",
            "sample": sample,
        }

    def _check_cover_traceability(
        self,
        model: dict[str, Any],
        cache: Optional[EngineeringRuleCache],
    ) -> dict[str, Any]:
        rows = model.get("cover_tables", [])
        row_ok = any(
            is_engineering_value(row.get("cover")) and row.get("cover", {}).get("table")
            == "COVER_TABLE"
            for row in rows
        )
        cache_ok = False
        if cache is not None:
            cover = cache.get_cover("BEAM")
            cache_ok = isinstance(cover, EngineeringValue) and cover.table == "COVER_TABLE"
        ok = row_ok and cache_ok
        return {
            "name": "Cover Traceability",
            "status": "PASS" if ok else "FAIL",
        }

    def _check_estimator_traceability(
        self,
        model: dict[str, Any],
        cache: Optional[EngineeringRuleCache],
    ) -> dict[str, Any]:
        spacer = model.get("estimator_rules", {}).get("spacer", {})
        embedded_ok = is_engineering_value(spacer.get("diameter")) and (
            spacer.get("diameter", {}).get("source") == "ESTIMATOR_RULES"
        )
        cache_ok = False
        if cache is not None:
            ev = cache.get_estimator_spacer()
            payload = ev.to_dict() if isinstance(ev, EngineeringValue) else {}
            cache_ok = (
                isinstance(ev, EngineeringValue)
                and ev.source == "ESTIMATOR_RULES"
                and (ev.extra.get("config") is not None or payload.get("config") is not None)
            )
        ok = embedded_ok and cache_ok
        return {
            "name": "Estimator Traceability",
            "status": "PASS" if ok else "FAIL",
        }

    def _check_decision_trail(self, model: dict[str, Any]) -> dict[str, Any]:
        trail = model.get("engineering_decision_trail", [])
        ok = isinstance(trail, list) and len(trail) >= 3
        if ok:
            ok = any(item.get("decision") == "Development Length Selection" for item in trail)
        return {
            "name": "Decision Trail",
            "status": "PASS" if ok else "FAIL",
            "decision_count": len(trail),
        }

    def _check_audit_report(self, model: dict[str, Any]) -> dict[str, Any]:
        report = model.get("engineering_traceability_report", {})
        chains = report.get("engineering_value_traceability", [])
        registry = model.get("engineering_value_registry", {})
        ok = bool(chains) and registry.get("entry_count", 0) >= 5
        return {
            "name": "Audit Report",
            "status": "PASS" if ok else "FAIL",
            "chain_count": len(chains),
            "registry_entries": registry.get("entry_count", 0),
        }
