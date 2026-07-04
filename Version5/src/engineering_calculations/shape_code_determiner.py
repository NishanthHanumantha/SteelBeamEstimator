"""Shape code determiner — Phase I.7."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_provenance.provenance_builder import (
    CalculationProvenanceBuilder,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState
from src.engineering_calculations.formula_engine.shape_code_classifier import (
    ShapeCodeClassificationInput,
    ShapeCodeClassifier,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedShapeCodeRule
from src.engineering_calculations.rule_resolution.shape_code_rule_resolver import (
    ShapeCodeRuleResolver,
)
from src.engineering_calculations.shape_code_types import (
    CALCULATION_TYPE,
    DETERMINATION_METHOD,
    ENGINE_NAME,
    RESULT_STATUS_DEPENDENCY_BLOCKED,
    RESULT_STATUS_LOOKUP_FAILED,
    RESULT_STATUS_PRESERVED,
    RESULT_STATUS_SUCCESS,
    SOURCE_ENGINE_VERSION,
    ShapeCodeState,
)
from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_value import engineering_value_numeric
from src.reinforcement_calculation.reinforcement_types import ROLE_TO_BAR_TYPE


DEPENDENCY_CATEGORY = "SHAPE_CODE"
PREREQUISITE_CATEGORIES = (
    "CUT_LENGTH",
    "HOOK_LENGTH",
)


def shape_code_applied(model: dict[str, Any]) -> bool:
    registry = model.get("shape_code_registry", {})
    if registry.get("phase") == "Phase I.7" and registry.get("determination_count", 0) >= 0:
        return True
    if model.get("shape_code_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("shape_code_complete"))


class ShapeCodeDeterminer:
    """Determine shape code for a single READY calculation result."""

    def __init__(
        self,
        cache: EngineeringRuleCache,
        dependency_graph: CalculationDependencyGraph,
        results_by_id: dict[str, dict[str, Any]],
    ) -> None:
        self._cache = cache
        self._dependency_graph = dependency_graph
        self._results_by_id = results_by_id
        self._rule_resolver = ShapeCodeRuleResolver(cache)
        self._classifier = ShapeCodeClassifier()

    def determine(
        self,
        result: dict[str, Any],
        context: dict[str, Any],
        bar: dict[str, Any],
    ) -> Tuple[dict[str, Any], dict[str, Any]]:
        state = str(result.get("calculation_state", ""))
        if state != CalculationResultState.READY.value:
            return result, self._build_preserved_record(result, context, bar, state)

        if not self._can_execute_shape_code(bar):
            missing = self._missing_shape_code_dependencies(bar)
            reason = f"Shape code dependencies not satisfied: {', '.join(missing)}."
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
                None,
                ShapeCodeState.FAILED.value,
                RESULT_STATUS_DEPENDENCY_BLOCKED,
                dependency_consulted=True,
                missing_dependencies=missing,
            )
            return updated, record

        prerequisite_results, missing_prereqs = self._resolve_prerequisite_results(bar)
        if missing_prereqs:
            reason = (
                "Shape code prerequisite calculations not calculated: "
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
                None,
                ShapeCodeState.FAILED.value,
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
                None,
                ShapeCodeState.FAILED.value,
                RESULT_STATUS_LOOKUP_FAILED,
                dependency_consulted=True,
            )
            return updated, record

        resolved_rule = self._rule_resolver.resolve(bar, context)
        inputs = self._finalize_inputs(inputs, resolved_rule, prerequisite_results, context)
        classification_input = ShapeCodeClassificationInput(
            reinforcement_role=str(inputs["reinforcement_role"]),
            bar_type=str(inputs["bar_type"]),
            hook_count=int(inputs["hook_count"]),
            bend_count=int(inputs["bend_count"]),
            closed_loop=bool(inputs["closed_loop"]),
            open_loop=bool(inputs["open_loop"]),
            hook_angle=int(inputs["hook_angle"]),
            cut_length_mm=int(inputs["cut_length_mm"]),
            clear_span_mm=int(inputs["clear_span_mm"]),
            resolved_rule=resolved_rule,
        )
        classification = self._classifier.classify(classification_input)
        trace = self._build_trace(inputs, classification.shape_code, resolved_rule)
        classification_metadata = self._build_classification_metadata(
            inputs,
            classification.shape_code,
            classification.shape_family,
            resolved_rule,
        )
        geometry_source = self._geometry_source_from_context(context, bar)
        source_results = [
            prerequisite_results["CUT_LENGTH"],
            prerequisite_results["HOOK_LENGTH"],
            geometry_source,
        ]
        provenance = CalculationProvenanceBuilder.build_from_source_results(source_results)
        updated = self._build_calculated_result(
            result,
            inputs,
            classification.shape_code,
            classification.shape_family,
            trace,
            classification_metadata,
            provenance,
        )
        record = self._build_record(
            result,
            context,
            bar,
            inputs,
            classification.shape_code,
            classification.shape_family,
            ShapeCodeState.CALCULATED.value,
            RESULT_STATUS_SUCCESS,
            classification_metadata=classification_metadata,
            dependency_consulted=True,
            calculation_provenance=provenance,
        )
        return updated, record

    def _can_execute_shape_code(self, bar: dict[str, Any]) -> bool:
        index = bar.get("calculation_index") or {}
        references = index.get("references") or {}
        for dependency in self._dependency_graph.depends_on(DEPENDENCY_CATEGORY):
            result_id = references.get(dependency)
            if not result_id:
                return False
            result = self._results_by_id.get(str(result_id))
            if not result:
                return False
            if str(result.get("calculation_state")) not in {
                CalculationResultState.CALCULATED.value,
                CalculationResultState.READY.value,
                CalculationResultState.DEFERRED.value,
                CalculationResultState.BLOCKED.value,
            }:
                return False
        return True

    def _missing_shape_code_dependencies(self, bar: dict[str, Any]) -> List[str]:
        missing: List[str] = []
        index = bar.get("calculation_index") or {}
        references = index.get("references") or {}
        for dependency in self._dependency_graph.depends_on(DEPENDENCY_CATEGORY):
            result_id = references.get(dependency)
            result = self._results_by_id.get(str(result_id)) if result_id else None
            if not result_id or not result:
                missing.append(dependency)
        return missing

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
            ):
                missing.append(category)
                continue
            if category == "CUT_LENGTH" and result.get("result_value") is None:
                missing.append(category)
                continue
            if category == "HOOK_LENGTH" and result.get("result_value") is None:
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

        cut_length_mm = self._cut_length_value(prerequisite_results.get("CUT_LENGTH"))
        hook_length_mm = self._result_value(prerequisite_results.get("HOOK_LENGTH"))
        hook_metadata = (prerequisite_results.get("HOOK_LENGTH") or {}).get("hook_length_metadata") or {}
        if cut_length_mm is None:
            missing.append("Cut length unavailable from indexed result.")
        if hook_length_mm is None:
            missing.append("Hook length unavailable from indexed result.")

        role = str(bar.get("role") or "UNKNOWN")
        bar_type = str(bar.get("bar_type") or ROLE_TO_BAR_TYPE.get(role, "MAIN_BAR"))
        hook_angle = int(hook_metadata.get("hook_angle") or context.get("hook_angle") or 90)

        inputs: dict[str, Any] = {
            "clear_span_mm": int(clear_span or 0),
            "effective_span_mm": int(effective_span or 0),
            "beam_width_mm": int(beam_width or 0),
            "beam_depth_mm": int(beam_depth or 0),
            "cover_side_mm": int(cover_side or 0),
            "bar_diameter_mm": int(diameter),
            "reinforcement_role": role,
            "bar_type": bar_type,
            "bar_position": str(bar.get("position") or context.get("position") or ""),
            "cut_length_mm": int(cut_length_mm or 0),
            "hook_length_mm": int(hook_length_mm or 0),
            "hook_angle": hook_angle,
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
    def _cut_length_value(result: Optional[dict[str, Any]]) -> Optional[int]:
        if not result:
            return None
        metadata = result.get("cut_length_metadata") or {}
        if metadata.get("value") is not None:
            return int(metadata["value"])
        value = engineering_value_numeric(result.get("result_value"))
        return int(value) if value is not None else None

    @staticmethod
    def _finalize_inputs(
        inputs: dict[str, Any],
        rule: ResolvedShapeCodeRule,
        prerequisite_results: dict[str, dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        finalized = dict(inputs)
        finalized.update(rule.to_classification_spec())
        finalized["shape_rule_source"] = str(rule.rule_source)
        finalized["cut_length_result_id"] = prerequisite_results["CUT_LENGTH"].get("result_id")
        finalized["hook_length_result_id"] = prerequisite_results["HOOK_LENGTH"].get("result_id")
        finalized["geometry_context_id"] = context.get("context_id")
        return finalized

    @staticmethod
    def _geometry_source_from_context(
        context: dict[str, Any],
        bar: dict[str, Any],
    ) -> dict[str, Any]:
        geometry_ref = (
            (context.get("traceability") or {})
            .get("association_traceability", {})
            .get("beam_geometry_reference", {})
        )
        geometry_id = str(
            geometry_ref.get("beam_geometry_id")
            or context.get("context_id")
            or bar.get("beam_id")
            or "BEAM_GEOMETRY"
        )
        return {
            "result_id": geometry_id,
            "calculation_type": "BEAM_GEOMETRY",
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": "GEOMETRY_ASSOCIATION",
            "source_engine_version": "H.2",
            "result_value": context.get("clear_span_mm"),
            "result_unit": "mm",
            "created_timestamp": str(context.get("created_timestamp") or ""),
            "result_metadata": {"determination_phase": "H.2"},
        }

    @staticmethod
    def _build_trace(
        inputs: dict[str, Any],
        shape_code: str,
        rule: ResolvedShapeCodeRule,
    ) -> List[str]:
        return [
            "Engineering Calculation Dependency Graph",
            "Cut Length",
            "Hook Length",
            "Bar Geometry",
            "Rule Resolver",
            "Classifier",
            rule.rule_description,
            f"Role {inputs['reinforcement_role']}",
            f"Shape Code {shape_code}",
        ]

    def _build_classification_metadata(
        self,
        inputs: dict[str, Any],
        shape_code: str,
        shape_family: str,
        rule: ResolvedShapeCodeRule,
    ) -> dict[str, Any]:
        model_meta = self._cache.model.get("metadata", {})
        return {
            "value": shape_code,
            "shape_code": shape_code,
            "shape_family": shape_family,
            "unit": "CODE",
            "rule_source": str(rule.rule_source),
            "determination_method": DETERMINATION_METHOD,
            "rule_name": str(rule.rule_name),
            "rule_reference": str(rule.rule_reference),
            "cut_length_used": int(inputs.get("cut_length_mm", 0)),
            "hook_length_used": int(inputs.get("hook_length_mm", 0)),
            "hook_count": int(inputs.get("hook_count", 0)),
            "bend_count": int(inputs.get("bend_count", 0)),
            "closed_loop": bool(inputs.get("closed_loop", False)),
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
        shape_code: str,
        shape_family: str,
        trace: List[str],
        classification_metadata: dict[str, Any],
        provenance: dict[str, Any],
    ) -> dict[str, Any]:
        updated = dict(result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = CalculationResultState.CALCULATED.value
        updated["result_status"] = RESULT_STATUS_SUCCESS
        updated["result_value"] = shape_code
        updated["result_unit"] = "CODE"
        updated["classification_inputs"] = dict(inputs)
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = list(trace)
        updated["shape_code_metadata"] = dict(classification_metadata)
        updated["classification_metadata"] = dict(classification_metadata)
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.7"
        metadata["framework_only"] = False
        metadata["dependency_graph_consulted"] = True
        metadata["shape_code"] = shape_code
        metadata["shape_family"] = shape_family
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
        updated["result_unit"] = "CODE"
        updated["classification_inputs"] = dict(inputs)
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = reasons
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.7"
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
            determination_state = ShapeCodeState.BLOCKED.value
        elif state == CalculationResultState.DEFERRED.value:
            determination_state = ShapeCodeState.DEFERRED.value
        else:
            determination_state = ShapeCodeState.DEFERRED.value

        return ShapeCodeDeterminer._build_record(
            result,
            context,
            bar,
            {},
            None,
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
        shape_code: Optional[str],
        shape_family: Optional[str],
        determination_state: str,
        result_status: str,
        classification_metadata: dict[str, Any] | None = None,
        dependency_consulted: bool = False,
        missing_dependencies: List[str] | None = None,
        calculation_provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "shape_code_id": None,
            "result_id": result.get("result_id"),
            "bar_id": bar.get("bar_id"),
            "beam_id": bar.get("beam_id"),
            "context_id": context.get("context_id"),
            "specification_id": bar.get("specification_id"),
            "bar_diameter_mm": inputs.get("bar_diameter_mm") or bar.get("diameter_mm"),
            "bar_type": inputs.get("bar_type") or bar.get("bar_type", ""),
            "reinforcement_role": inputs.get("reinforcement_role") or bar.get("role", ""),
            "cut_length_mm": inputs.get("cut_length_mm"),
            "hook_length_mm": inputs.get("hook_length_mm"),
            "shape_code": shape_code,
            "shape_family": shape_family,
            "shape_rule_source": inputs.get("shape_rule_source", ""),
            "determination_state": determination_state,
            "result_status": result_status,
            "dependency_graph_consulted": dependency_consulted,
            "classification_inputs": dict(inputs),
            "traceability": {
                "lineage": [
                    "Shape Code Determination",
                    "Rule Resolver",
                    "Classifier",
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
        if classification_metadata:
            record["classification_metadata"] = dict(classification_metadata)
            record["shape_code_metadata"] = dict(classification_metadata)
        if calculation_provenance:
            record["calculation_provenance"] = dict(calculation_provenance)
        return record
