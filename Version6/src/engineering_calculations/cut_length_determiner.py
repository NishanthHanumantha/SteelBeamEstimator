"""Cut length determiner — Phase I.6."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_provenance.provenance_builder import (
    CalculationProvenanceBuilder,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState
from src.engineering_calculations.cut_length_types import (
    DETERMINATION_METHOD,
    ENGINE_NAME,
    RESULT_STATUS_DEPENDENCY_BLOCKED,
    RESULT_STATUS_LOOKUP_FAILED,
    RESULT_STATUS_PRESERVED,
    RESULT_STATUS_SUCCESS,
    SOURCE_ENGINE_VERSION,
    CutLengthState,
)
from src.engineering_calculations.formula_engine.cut_length_formula import (
    CutLengthFormulaEngine,
    CutLengthFormulaInput,
)
from src.engineering_calculations.rule_resolution.cut_length_rule_resolver import (
    CutLengthRuleResolver,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedCutLengthRule
from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_value import engineering_value_numeric
from src.reinforcement_calculation.reinforcement_types import ROLE_TO_BAR_TYPE


PREREQUISITE_CATEGORIES = (
    "DEVELOPMENT_LENGTH",
    "HOOK_LENGTH",
    "LAP_LENGTH",
)


def cut_length_applied(model: dict[str, Any]) -> bool:
    registry = model.get("cut_length_registry", {})
    if registry.get("phase") == "Phase I.6" and registry.get("determination_count", 0) >= 0:
        return True
    if model.get("cut_length_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("cut_length_complete"))


class CutLengthDeterminer:
    """Determine cut length for a single READY calculation result."""

    def __init__(
        self,
        cache: EngineeringRuleCache,
        dependency_graph: CalculationDependencyGraph,
        results_by_id: dict[str, dict[str, Any]],
    ) -> None:
        self._cache = cache
        self._dependency_graph = dependency_graph
        self._results_by_id = results_by_id
        self._rule_resolver = CutLengthRuleResolver(cache)
        self._formula_engine = CutLengthFormulaEngine()

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
            "CUT_LENGTH",
            bar,
            self._results_by_id,
        ):
            missing = self._dependency_graph.missing_dependencies(
                "CUT_LENGTH",
                bar,
                self._results_by_id,
            )
            reason = f"Cut length dependencies not satisfied: {', '.join(missing)}."
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
                CutLengthState.FAILED.value,
                RESULT_STATUS_DEPENDENCY_BLOCKED,
                dependency_consulted=True,
                missing_dependencies=missing,
            )
            return updated, record

        prerequisite_results, missing_prereqs = self._resolve_prerequisite_results(bar)
        if missing_prereqs:
            reason = (
                "Cut length prerequisite calculations not calculated: "
                f"{', '.join(missing_prereqs)}."
            )
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
                CutLengthState.FAILED.value,
                RESULT_STATUS_DEPENDENCY_BLOCKED,
                dependency_consulted=True,
                missing_dependencies=missing_prereqs,
            )
            return updated, record

        inputs, missing = self._resolve_inputs(context, bar, prerequisite_results)
        if missing:
            updated = self._build_failed_result(result, inputs, missing)
            record = self._build_record(
                result,
                context,
                bar,
                inputs,
                None,
                CutLengthState.FAILED.value,
                RESULT_STATUS_LOOKUP_FAILED,
                dependency_consulted=True,
            )
            return updated, record

        resolved_rule = self._rule_resolver.resolve(bar, context)
        inputs = self._finalize_inputs(inputs, resolved_rule, prerequisite_results)
        formula_input = CutLengthFormulaInput(
            clear_span_mm=int(inputs["clear_span_mm"]),
            effective_span_mm=int(inputs["effective_span_mm"]),
            development_length_mm=int(inputs["development_length_mm"]),
            hook_length_mm=int(inputs["hook_length_mm"]),
            lap_length_mm=int(inputs["lap_length_mm"]),
            beam_width_mm=int(inputs["beam_width_mm"]),
            beam_depth_mm=int(inputs["beam_depth_mm"]),
            cover_side_mm=int(inputs["cover_side_mm"]),
            resolved_rule=resolved_rule,
        )
        cut_mm = self._formula_engine.evaluate(formula_input)
        trace = self._build_trace(inputs, cut_mm, resolved_rule)
        cut_metadata = self._build_cut_metadata(inputs, cut_mm, resolved_rule)
        source_results = [
            prerequisite_results["DEVELOPMENT_LENGTH"],
            prerequisite_results["HOOK_LENGTH"],
            prerequisite_results["LAP_LENGTH"],
        ]
        provenance = CalculationProvenanceBuilder.build_from_source_results(source_results)
        updated = self._build_calculated_result(
            result,
            inputs,
            cut_mm,
            trace,
            cut_metadata,
            provenance,
        )
        record = self._build_record(
            result,
            context,
            bar,
            inputs,
            cut_mm,
            CutLengthState.CALCULATED.value,
            RESULT_STATUS_SUCCESS,
            cut_metadata=cut_metadata,
            dependency_consulted=True,
            calculation_provenance=provenance,
        )
        return updated, record

    def _resolve_prerequisite_results(
        self,
        bar: dict[str, Any],
    ) -> Tuple[dict[str, dict[str, Any]], List[str]]:
        index = bar.get("calculation_index") or {}
        references = index.get("references") or {}
        resolved: dict[str, dict[str, Any]] = {}
        missing: List[str] = []
        for category in PREREQUISITE_CATEGORIES:
            result_id = references.get(category)
            result = self._results_by_id.get(str(result_id)) if result_id else None
            if (
                not result
                or result.get("calculation_state") != CalculationResultState.CALCULATED.value
                or result.get("result_value") is None
            ):
                missing.append(category)
                continue
            resolved[category] = result
        return resolved, missing

    def _resolve_inputs(
        self,
        context: dict[str, Any],
        bar: dict[str, Any],
        prerequisite_results: dict[str, dict[str, Any]],
    ) -> Tuple[dict[str, Any], List[str]]:
        missing: List[str] = []
        diameter_raw = bar.get("diameter_mm")
        diameter = engineering_value_numeric(diameter_raw)
        if diameter is None:
            missing.append("Bar diameter unavailable.")
            diameter = 0

        clear_span = engineering_value_numeric(context.get("clear_span_mm"))
        if clear_span is None:
            missing.append("Clear span unavailable from calculation context.")
            clear_span = 0

        effective_span = engineering_value_numeric(context.get("effective_span_mm"))
        if effective_span is None:
            missing.append("Effective span unavailable from calculation context.")
            effective_span = 0

        beam_width = engineering_value_numeric(context.get("beam_width_mm"))
        if beam_width is None:
            missing.append("Beam width unavailable from calculation context.")
            beam_width = 0

        beam_depth = engineering_value_numeric(context.get("beam_depth_mm"))
        if beam_depth is None:
            missing.append("Beam depth unavailable from calculation context.")
            beam_depth = 0

        cover_side = engineering_value_numeric(context.get("cover_side_mm"))
        if cover_side is None:
            missing.append("Cover unavailable from calculation context.")
            cover_side = 0

        development_length_mm = self._result_value(prerequisite_results.get("DEVELOPMENT_LENGTH"))
        hook_length_mm = self._result_value(prerequisite_results.get("HOOK_LENGTH"))
        lap_length_mm = self._result_value(prerequisite_results.get("LAP_LENGTH"))
        if development_length_mm is None:
            missing.append("Development length unavailable from indexed result.")
        if hook_length_mm is None:
            missing.append("Hook length unavailable from indexed result.")
        if lap_length_mm is None:
            missing.append("Lap length unavailable from indexed result.")

        role = str(bar.get("role") or "UNKNOWN")
        bar_type = str(bar.get("bar_type") or ROLE_TO_BAR_TYPE.get(role, "MAIN_BAR"))

        inputs: dict[str, Any] = {
            "clear_span_mm": int(clear_span or 0),
            "effective_span_mm": int(effective_span or 0),
            "beam_width_mm": int(beam_width or 0),
            "beam_depth_mm": int(beam_depth or 0),
            "cover_side_mm": int(cover_side or 0),
            "bar_diameter_mm": int(diameter),
            "reinforcement_role": role,
            "bar_type": bar_type,
            "development_length_mm": int(development_length_mm or 0),
            "hook_length_mm": int(hook_length_mm or 0),
            "lap_length_mm": int(lap_length_mm or 0),
            "beam_geometry_reference": (
                (context.get("traceability") or {})
                .get("association_traceability", {})
                .get("beam_geometry_reference", {})
            ),
        }
        return inputs, missing

    @staticmethod
    def _result_value(result: Optional[dict[str, Any]]) -> Optional[int]:
        if not result:
            return None
        value = engineering_value_numeric(result.get("result_value"))
        return int(value) if value is not None else None

    @staticmethod
    def _finalize_inputs(
        inputs: dict[str, Any],
        rule: ResolvedCutLengthRule,
        prerequisite_results: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        finalized = dict(inputs)
        finalized.update(rule.to_formula_spec())
        finalized["cut_rule_source"] = str(rule.rule_source)
        finalized["reinforcement_position"] = str(rule.reinforcement_position)
        finalized["development_length_result_id"] = prerequisite_results[
            "DEVELOPMENT_LENGTH"
        ].get("result_id")
        finalized["hook_length_result_id"] = prerequisite_results["HOOK_LENGTH"].get("result_id")
        finalized["lap_length_result_id"] = prerequisite_results["LAP_LENGTH"].get("result_id")
        return finalized

    @staticmethod
    def _build_trace(
        inputs: dict[str, Any],
        cut_mm: int,
        rule: ResolvedCutLengthRule,
    ) -> List[str]:
        return [
            "Engineering Calculation Dependency Graph",
            "Development Length",
            "Hook Length",
            "Lap Length",
            "Rule Resolver",
            "Formula Engine",
            rule.rule_description,
            f"Role {inputs['reinforcement_role']}",
            f"Clear Span {inputs['clear_span_mm']} mm",
            f"Cut Length {cut_mm} mm",
        ]

    def _build_cut_metadata(
        self,
        inputs: dict[str, Any],
        cut_mm: int,
        rule: ResolvedCutLengthRule,
    ) -> dict[str, Any]:
        model_meta = self._cache.model.get("metadata", {})
        return {
            "value": cut_mm,
            "unit": "mm",
            "rule_source": str(rule.rule_source),
            "determination_method": DETERMINATION_METHOD,
            "rule_name": str(rule.rule_name),
            "rule_reference": str(rule.rule_reference),
            "development_length_used": int(inputs.get("development_length_mm", 0)),
            "hook_length_used": int(inputs.get("hook_length_mm", 0)),
            "lap_length_used": int(inputs.get("lap_length_mm", 0)),
            "clear_span_used": int(inputs.get("clear_span_mm", 0)),
            "effective_span_used": int(inputs.get("effective_span_mm", 0)),
            "reinforcement_role": str(inputs.get("reinforcement_role", "")),
            "bar_type": str(inputs.get("bar_type", "")),
            "diameter_mm": int(inputs.get("bar_diameter_mm", 0)),
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
        cut_mm: int,
        trace: List[str],
        cut_metadata: dict[str, Any],
        provenance: dict[str, Any],
    ) -> dict[str, Any]:
        updated = dict(result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = CalculationResultState.CALCULATED.value
        updated["result_status"] = RESULT_STATUS_SUCCESS
        updated["result_value"] = cut_mm
        updated["result_unit"] = "mm"
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = list(trace)
        updated["cut_length_metadata"] = dict(cut_metadata)
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.6"
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
        metadata["determination_phase"] = "I.6"
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
            determination_state = CutLengthState.BLOCKED.value
        elif state == CalculationResultState.DEFERRED.value:
            determination_state = CutLengthState.DEFERRED.value
        else:
            determination_state = CutLengthState.DEFERRED.value

        return CutLengthDeterminer._build_record(
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
        cut_mm: Optional[int],
        determination_state: str,
        result_status: str,
        cut_metadata: dict[str, Any] | None = None,
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
            "bar_type": inputs.get("bar_type") or bar.get("bar_type", ""),
            "reinforcement_role": inputs.get("reinforcement_role") or bar.get("role", ""),
            "clear_span_mm": inputs.get("clear_span_mm"),
            "development_length_mm": inputs.get("development_length_mm"),
            "hook_length_mm": inputs.get("hook_length_mm"),
            "lap_length_mm": inputs.get("lap_length_mm"),
            "cut_rule_source": inputs.get("cut_rule_source", ""),
            "cut_length_mm": cut_mm,
            "determination_state": determination_state,
            "result_status": result_status,
            "dependency_graph_consulted": dependency_consulted,
            "calculation_inputs": dict(inputs),
            "traceability": {
                "lineage": [
                    "Cut Length Determination",
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
        if cut_metadata:
            record["cut_length_metadata"] = dict(cut_metadata)
        if calculation_provenance:
            record["calculation_provenance"] = dict(calculation_provenance)
        return record
