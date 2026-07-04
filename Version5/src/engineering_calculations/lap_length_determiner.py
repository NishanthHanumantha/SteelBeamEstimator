"""Lap length determiner — Phase I.5."""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_provenance.provenance_builder import (
    CalculationProvenanceBuilder,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState
from src.engineering_calculations.formula_engine.lap_length_formula import LapLengthFormulaEngine
from src.engineering_calculations.lap_length_types import (
    DETERMINATION_METHOD,
    ENGINE_NAME,
    RESULT_STATUS_DEPENDENCY_BLOCKED,
    RESULT_STATUS_LOOKUP_FAILED,
    RESULT_STATUS_PRESERVED,
    RESULT_STATUS_SUCCESS,
    RULE_SOURCE_GENERAL_NOTES,
    SOURCE_ENGINE_VERSION,
    LapLengthState,
)
from src.engineering_calculations.rule_resolution.lap_rule_resolver import LapRuleResolver
from src.engineering_calculations.rule_resolution.rule_types import ResolvedLapRule
from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_value import engineering_value_numeric
from src.general_notes.ld_table_selector import steel_table_key


def lap_length_applied(model: dict[str, Any]) -> bool:
    registry = model.get("lap_length_registry", {})
    if registry.get("phase") == "Phase I.5" and registry.get("determination_count", 0) >= 0:
        return True
    if model.get("lap_length_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("lap_length_complete"))


class LapLengthDeterminer:
    """Determine lap length for a single READY calculation result."""

    def __init__(
        self,
        cache: EngineeringRuleCache,
        dependency_graph: CalculationDependencyGraph,
        results_by_id: dict[str, dict[str, Any]],
    ) -> None:
        self._cache = cache
        self._dependency_graph = dependency_graph
        self._results_by_id = results_by_id
        self._rule_resolver = LapRuleResolver(cache)
        self._formula_engine = LapLengthFormulaEngine()

    def determine(
        self,
        result: dict[str, Any],
        context: dict[str, Any],
        bar: dict[str, Any],
    ) -> Tuple[dict[str, Any], dict[str, Any]]:
        state = str(result.get("calculation_state", ""))
        if state != CalculationResultState.READY.value:
            return result, self._build_preserved_record(result, context, bar, state)

        if not self._dependency_graph.can_execute(
            "LAP_LENGTH",
            bar,
            self._results_by_id,
        ):
            missing = self._dependency_graph.missing_dependencies(
                "LAP_LENGTH",
                bar,
                self._results_by_id,
            )
            reason = f"Lap length dependencies not satisfied: {', '.join(missing)}."
            updated = self._build_failed_result(
                result,
                {},
                [reason],
                RESULT_STATUS_DEPENDENCY_BLOCKED,
            )
            record = self._build_record(
                result,
                context,
                bar,
                {},
                None,
                LapLengthState.FAILED.value,
                RESULT_STATUS_DEPENDENCY_BLOCKED,
                dependency_consulted=True,
                missing_dependencies=missing,
            )
            return updated, record

        inputs, missing = self._resolve_inputs(context, bar)
        if missing:
            updated = self._build_failed_result(result, inputs, missing)
            record = self._build_record(
                result,
                context,
                bar,
                inputs,
                None,
                LapLengthState.FAILED.value,
                RESULT_STATUS_LOOKUP_FAILED,
                dependency_consulted=True,
            )
            return updated, record

        resolved_rule = self._rule_resolver.resolve(bar, context)
        inputs = self._finalize_inputs(inputs, resolved_rule)
        lap_mm = self._formula_engine.evaluate(
            int(inputs["development_length_mm"]),
            float(inputs["lap_factor"]),
            int(inputs["minimum_lap_mm"]),
        )
        trace = self._build_trace(inputs, lap_mm, resolved_rule)
        lap_metadata = self._build_lap_metadata(inputs, lap_mm, resolved_rule)
        development_result = self._resolve_development_length_result(bar)
        provenance = CalculationProvenanceBuilder.build_from_source_results(
            [development_result] if development_result else []
        )
        updated = self._build_calculated_result(
            result,
            inputs,
            lap_mm,
            trace,
            lap_metadata,
            provenance,
        )
        record = self._build_record(
            result,
            context,
            bar,
            inputs,
            lap_mm,
            LapLengthState.CALCULATED.value,
            RESULT_STATUS_SUCCESS,
            lap_metadata=lap_metadata,
            dependency_consulted=True,
            calculation_provenance=provenance,
        )
        return updated, record

    def _resolve_inputs(
        self,
        context: dict[str, Any],
        bar: dict[str, Any],
    ) -> Tuple[dict[str, Any], List[str]]:
        missing: List[str] = []
        diameter_raw = bar.get("diameter_mm")
        diameter = engineering_value_numeric(diameter_raw)
        if diameter is None:
            missing.append("Bar diameter unavailable.")
            diameter = 0

        steel_grade = bar.get("steel_grade") or context.get("steel_grade")
        if not steel_grade:
            missing.append("Steel grade unavailable.")

        concrete_grade = context.get("concrete_grade")
        if not concrete_grade:
            missing.append("Concrete grade unavailable.")

        development_length_mm = self._resolve_development_length(bar)
        if development_length_mm is None:
            missing.append("Development length unavailable from indexed result.")

        inputs: dict[str, Any] = {
            "bar_diameter_mm": int(diameter),
            "steel_grade": str(steel_grade or ""),
            "concrete_grade": str(concrete_grade or ""),
            "development_length_mm": int(development_length_mm or 0),
            "reinforcement_position": self._rule_resolver._resolve_reinforcement_position(
                bar,
                context,
            ),
        }
        return inputs, missing

    def _resolve_development_length(self, bar: dict[str, Any]) -> Optional[int]:
        result = self._resolve_development_length_result(bar)
        if not result:
            return None
        value = engineering_value_numeric(result.get("result_value"))
        return int(value) if value is not None else None

    def _resolve_development_length_result(self, bar: dict[str, Any]) -> Optional[dict[str, Any]]:
        index = bar.get("calculation_index") or {}
        references = index.get("references") or {}
        result_id = references.get("DEVELOPMENT_LENGTH")
        if not result_id:
            return None
        result = self._results_by_id.get(str(result_id))
        if not result:
            return None
        if result.get("calculation_state") != CalculationResultState.CALCULATED.value:
            return None
        return result

    @staticmethod
    def _finalize_inputs(inputs: dict[str, Any], rule: ResolvedLapRule) -> dict[str, Any]:
        finalized = dict(inputs)
        finalized.update(rule.to_inputs())
        return finalized

    @staticmethod
    def _build_trace(
        inputs: dict[str, Any],
        lap_mm: int,
        rule: ResolvedLapRule,
    ) -> List[str]:
        return [
            "Engineering Calculation Dependency Graph",
            "Development Length",
            "Rule Resolver",
            "Formula Engine",
            rule.rule_description,
            f"Position {inputs['reinforcement_position']}",
            f"Factor {inputs['lap_factor']}",
            f"Development Length {inputs['development_length_mm']} mm",
            f"Lap Length {lap_mm} mm",
        ]

    def _build_lap_metadata(
        self,
        inputs: dict[str, Any],
        lap_mm: int,
        rule: ResolvedLapRule,
    ) -> dict[str, Any]:
        normalized_steel = steel_table_key(str(inputs.get("steel_grade", "")))
        model_meta = self._cache.model.get("metadata", {})
        return {
            "value": lap_mm,
            "unit": "mm",
            "rule_source": str(rule.rule_source),
            "determination_method": DETERMINATION_METHOD,
            "development_length": int(inputs.get("development_length_mm", 0)),
            "lap_factor": float(inputs.get("lap_factor", 1.0)),
            "minimum_lap_mm": int(inputs.get("minimum_lap_mm", 0)),
            "steel_grade": str(inputs.get("steel_grade", "")),
            "normalized_steel_grade": normalized_steel,
            "concrete_grade": str(inputs.get("concrete_grade", "")),
            "diameter_mm": int(inputs.get("bar_diameter_mm", 0)),
            "reinforcement_position": str(inputs.get("reinforcement_position", "")),
            "rule_name": rule.rule_name,
            "rule_reference": rule.rule_reference,
            "lookup_path": list(rule.lookup_path),
            "rule_cache_version": str(
                model_meta.get("knowledge_version")
                or self._cache.model.get("knowledge_version")
                or SOURCE_ENGINE_VERSION
            ),
        }

    @staticmethod
    def _build_calculated_result(
        result: dict[str, Any],
        inputs: dict[str, Any],
        lap_mm: int,
        trace: List[str],
        lap_metadata: dict[str, Any],
        provenance: dict[str, Any],
    ) -> dict[str, Any]:
        updated = dict(result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = CalculationResultState.CALCULATED.value
        updated["result_status"] = RESULT_STATUS_SUCCESS
        updated["result_value"] = lap_mm
        updated["result_unit"] = "mm"
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = list(trace)
        updated["lap_length_metadata"] = dict(lap_metadata)
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.5"
        metadata["framework_only"] = False
        metadata["dependency_graph_consulted"] = True
        updated["result_metadata"] = metadata
        return CalculationProvenanceBuilder.attach(updated, provenance)

    @staticmethod
    def _build_failed_result(
        result: dict[str, Any],
        inputs: dict[str, Any],
        reasons: List[str],
        result_status: str = RESULT_STATUS_LOOKUP_FAILED,
    ) -> dict[str, Any]:
        updated = dict(result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = CalculationResultState.FAILED.value
        updated["result_status"] = result_status
        updated["result_value"] = None
        updated["result_unit"] = "mm"
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = reasons
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.5"
        metadata["lookup_failed"] = True
        metadata["dependency_graph_consulted"] = True
        updated["result_metadata"] = metadata
        return updated

    @staticmethod
    def _build_preserved_record(
        result: dict[str, Any],
        context: dict[str, Any],
        bar: dict[str, Any],
        state: str,
    ) -> dict[str, Any]:
        if state == CalculationResultState.BLOCKED.value:
            determination_state = LapLengthState.BLOCKED.value
        elif state == CalculationResultState.DEFERRED.value:
            determination_state = LapLengthState.DEFERRED.value
        else:
            determination_state = LapLengthState.DEFERRED.value

        return LapLengthDeterminer._build_record(
            result,
            context,
            bar,
            {},
            None,
            determination_state,
            RESULT_STATUS_PRESERVED,
        )

    @staticmethod
    def _build_record(
        result: dict[str, Any],
        context: dict[str, Any],
        bar: dict[str, Any],
        inputs: dict[str, Any],
        lap_mm: Optional[int],
        determination_state: str,
        result_status: str,
        lap_metadata: dict[str, Any] | None = None,
        dependency_consulted: bool = False,
        missing_dependencies: List[str] | None = None,
        calculation_provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "result_id": result.get("result_id"),
            "bar_id": bar.get("bar_id"),
            "beam_id": bar.get("beam_id"),
            "context_id": context.get("context_id"),
            "specification_id": bar.get("specification_id"),
            "bar_diameter_mm": inputs.get("bar_diameter_mm") or bar.get("diameter_mm"),
            "steel_grade": inputs.get("steel_grade", bar.get("steel_grade", "")),
            "concrete_grade": inputs.get("concrete_grade", context.get("concrete_grade", "")),
            "development_length_mm": inputs.get("development_length_mm"),
            "lap_factor": inputs.get("lap_factor"),
            "minimum_lap_mm": inputs.get("minimum_lap_mm"),
            "lap_rule_source": inputs.get("lap_rule_source", ""),
            "reinforcement_position": inputs.get("reinforcement_position", ""),
            "lap_length_mm": lap_mm,
            "determination_state": determination_state,
            "result_status": result_status,
            "dependency_graph_consulted": dependency_consulted,
            "calculation_inputs": dict(inputs),
            "traceability": {
                "lineage": [
                    "Lap Length Determination",
                    "Rule Resolver",
                    "Formula Engine",
                    "Calculation Provenance",
                    "Engineering Calculation Dependency Graph",
                    "Engineering Calculation Result Framework",
                    "Calculation Readiness",
                    "Reinforcement Calculation",
                    "Engineering Calculation Context",
                ],
                "result_id": result.get("result_id"),
                "context_id": context.get("context_id"),
                "bar_id": bar.get("bar_id"),
                "bar_traceability": bar.get("traceability", {}),
                "context_traceability": context.get("traceability", {}),
            },
        }
        if missing_dependencies:
            record["missing_dependencies"] = list(missing_dependencies)
        if lap_metadata:
            record["lap_length_metadata"] = dict(lap_metadata)
        if calculation_provenance:
            record["calculation_provenance"] = dict(calculation_provenance)
        return record
