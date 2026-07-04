"""Validate calculation provenance integrity."""

from __future__ import annotations

from typing import Any, List, Set

from src.engineering_calculations.calculation_provenance.provenance_builder import (
    CalculationProvenanceBuilder,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState
from src.engineering_calculations.formula_engine.lap_length_formula import LapLengthFormulaEngine
from src.engineering_calculations.rule_resolution.lap_rule_resolver import LapRuleResolver


class CalculationProvenanceValidator:
    """Verify calculation provenance integrity across engineering results."""

    CALCULATED_TYPES_WITH_EMPTY_SOURCES = {"DEVELOPMENT_LENGTH", "HOOK"}

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        results = model.get("engineering_calculation_results", [])
        if not results:
            return {
                "phase": "Phase I.5.A",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "no engineering calculation results"},
            }

        results_by_id = {
            str(item.get("result_id", "")): item
            for item in results
            if item.get("result_id")
        }

        checks: List[dict[str, Any]] = []
        checks.append(self._check_calculated_results_have_provenance(results))
        checks.append(self._check_provenance_structure(results))
        checks.append(self._check_referenced_sources_exist(results, results_by_id))
        checks.append(self._check_referenced_calculation_types_match(results, results_by_id))
        checks.append(self._check_no_circular_provenance(results))
        checks.append(self._check_provenance_immutable_flag(results))
        checks.append(self._check_development_length_empty_sources(results))
        checks.append(self._check_hook_length_empty_sources(results))
        checks.append(self._check_lap_length_development_source(results, results_by_id))
        checks.append(self._check_provenance_reproducibility(results))
        checks.append(self._check_formula_engine_has_no_rule_cache_dependency())
        checks.append(self._check_rule_resolver_performs_no_mathematics())
        checks.append(self._check_lap_outputs_unchanged_with_formula_engine(results))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.5.A",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "result_count": len(results),
            },
        }

    @staticmethod
    def _check_calculated_results_have_provenance(results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_provenance")
        ]
        return {
            "name": "Calculated Results Have Provenance",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_provenance_structure(results: list) -> dict[str, Any]:
        invalid = []
        for item in results:
            provenance = item.get("calculation_provenance")
            if not provenance:
                continue
            if not isinstance(provenance.get("sources"), list):
                invalid.append(item.get("result_id"))
            elif provenance.get("immutable") is not True:
                invalid.append(item.get("result_id"))
        return {
            "name": "Provenance Structure Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_referenced_sources_exist(
        results: list,
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        missing = []
        for item in results:
            provenance = item.get("calculation_provenance") or {}
            for source in provenance.get("sources", []):
                source_id = str(source.get("result_id", ""))
                if source_id and source_id not in results_by_id:
                    missing.append(source_id)
        return {
            "name": "Referenced Source Results Exist",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(set(missing)),
        }

    @staticmethod
    def _check_referenced_calculation_types_match(
        results: list,
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        mismatches = []
        for item in results:
            provenance = item.get("calculation_provenance") or {}
            for source in provenance.get("sources", []):
                source_id = str(source.get("result_id", ""))
                actual = results_by_id.get(source_id)
                if not actual:
                    continue
                if str(source.get("calculation_type", "")) != str(actual.get("calculation_type", "")):
                    mismatches.append(source_id)
        return {
            "name": "Referenced Calculation Types Match",
            "status": "PASS" if not mismatches else "FAIL",
            "mismatch_count": len(mismatches),
        }

    @staticmethod
    def _check_no_circular_provenance(results: list) -> dict[str, Any]:
        violations = []
        for item in results:
            result_id = str(item.get("result_id", ""))
            provenance = item.get("calculation_provenance") or {}
            for source in provenance.get("sources", []):
                if str(source.get("result_id", "")) == result_id:
                    violations.append(result_id)
        return {
            "name": "No Circular Provenance",
            "status": "PASS" if not violations else "FAIL",
            "violation_count": len(violations),
        }

    @staticmethod
    def _check_provenance_immutable_flag(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_provenance")
            and item.get("calculation_provenance", {}).get("immutable") is not True
        ]
        return {
            "name": "Provenance Immutable After Creation",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_development_length_empty_sources(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") == "DEVELOPMENT_LENGTH"
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and (item.get("calculation_provenance") or {}).get("sources")
        ]
        return {
            "name": "Development Length Has Empty Sources",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_hook_length_empty_sources(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") == "HOOK"
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and (item.get("calculation_provenance") or {}).get("sources")
        ]
        return {
            "name": "Hook Length Has Empty Sources",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_lap_length_development_source(
        results: list,
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        invalid = []
        for item in results:
            if item.get("calculation_type") != "LAP_LENGTH":
                continue
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            sources = (item.get("calculation_provenance") or {}).get("sources", [])
            if len(sources) != 1:
                invalid.append(item.get("result_id"))
                continue
            source_id = str(sources[0].get("result_id", ""))
            source = results_by_id.get(source_id)
            if not source or source.get("calculation_type") != "DEVELOPMENT_LENGTH":
                invalid.append(item.get("result_id"))
        return {
            "name": "Lap Length References Development Length Source",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_provenance_reproducibility(results: list) -> dict[str, Any]:
        invalid = []
        for item in results:
            provenance = item.get("calculation_provenance")
            if not provenance:
                continue
            rebuilt = CalculationProvenanceBuilder.build_from_source_results(
                [
                    {
                        "result_id": source.get("result_id"),
                        "calculation_type": source.get("calculation_type"),
                        "engine_name": source.get("engine_name"),
                        "source_engine_version": source.get("engine_version"),
                        "calculation_state": source.get("result_state"),
                        "result_value": source.get("value"),
                        "result_unit": source.get("unit"),
                        "created_timestamp": source.get("timestamp"),
                        "result_metadata": {"determination_phase": source.get("source_phase")},
                    }
                    for source in provenance.get("sources", [])
                ]
            )
            if rebuilt.get("sources") != provenance.get("sources"):
                invalid.append(item.get("result_id"))
        return {
            "name": "Provenance Reproducible Across Runs",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_formula_engine_has_no_rule_cache_dependency() -> dict[str, Any]:
        import inspect

        source = inspect.getsource(LapLengthFormulaEngine)
        forbidden = ("EngineeringRuleCache", "general_notes", "fabrication_rules")
        violations = [token for token in forbidden if token in source]
        return {
            "name": "Formula Engine Never Reads EngineeringRuleCache",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
        }

    @staticmethod
    def _check_rule_resolver_performs_no_mathematics() -> dict[str, Any]:
        import inspect

        source = inspect.getsource(LapRuleResolver)
        forbidden = ("round(", "max(", "min(", "* ", "development_length_mm *")
        violations = [token for token in forbidden if token in source]
        return {
            "name": "Rule Resolver Performs No Mathematics",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
        }

    @staticmethod
    def _check_lap_outputs_unchanged_with_formula_engine(results: list) -> dict[str, Any]:
        invalid = []
        for item in results:
            if item.get("calculation_type") != "LAP_LENGTH":
                continue
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            inputs = item.get("calculation_inputs") or {}
            expected = LapLengthFormulaEngine.evaluate(
                int(inputs.get("development_length_mm", 0)),
                float(inputs.get("lap_factor", 0)),
                int(inputs.get("minimum_lap_mm", 0)),
            )
            if expected != item.get("result_value"):
                invalid.append(item.get("result_id"))
        return {
            "name": "Lap Outputs Unchanged With Formula Engine",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }
