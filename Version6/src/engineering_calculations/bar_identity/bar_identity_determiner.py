"""Bar identity determiner — Phase I.8."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.engineering_calculations.bar_identity.bar_identity_types import (
    CALCULATION_TYPE,
    DETERMINATION_METHOD,
    ENGINE_NAME,
    RESULT_STATUS_DEPENDENCY_BLOCKED,
    RESULT_STATUS_LOOKUP_FAILED,
    RESULT_STATUS_PRESERVED,
    RESULT_STATUS_SUCCESS,
    SOURCE_ENGINE_VERSION,
    BarIdentityState,
)
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_provenance.provenance_builder import (
    CalculationProvenanceBuilder,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState
from src.engineering_calculations.formula_engine.bar_identity_classifier import (
    BarIdentityClassificationInput,
    BarIdentityClassifier,
)
from src.engineering_calculations.rule_resolution.bar_identity_rule_resolver import (
    BarIdentityRuleResolver,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedBarIdentityRule
from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_value import engineering_value_numeric
from src.reinforcement_calculation.reinforcement_types import ROLE_TO_BAR_TYPE


DEPENDENCY_CATEGORY = "BAR_IDENTITY"
PREREQUISITE_CATEGORIES = (
    "CUT_LENGTH",
    "HOOK_LENGTH",
    "DEVELOPMENT_LENGTH",
    "LAP_LENGTH",
)
SHAPE_CODE_TYPE = "SHAPE_CODE"


def bar_identity_applied(model: dict[str, Any]) -> bool:
    registry = model.get("bar_identity_registry", {})
    if registry.get("phase") == "Phase I.8" and registry.get("determination_count", 0) >= 0:
        return True
    if model.get("bar_identity_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("bar_identity_complete"))


class BarIdentityDeterminer:
    """Determine bar identity for a single READY calculation result."""

    def __init__(
        self,
        cache: EngineeringRuleCache,
        dependency_graph: CalculationDependencyGraph,
        results_by_id: dict[str, dict[str, Any]],
        assignment_plan: dict[str, dict[str, Any]],
    ) -> None:
        self._cache = cache
        self._dependency_graph = dependency_graph
        self._results_by_id = results_by_id
        self._assignment_plan = assignment_plan
        self._rule_resolver = BarIdentityRuleResolver(cache)
        self._classifier = BarIdentityClassifier()

    def determine(
        self,
        result: dict[str, Any],
        context: dict[str, Any],
        bar: dict[str, Any],
    ) -> Tuple[dict[str, Any], dict[str, Any]]:
        state = str(result.get("calculation_state", ""))
        if state != CalculationResultState.READY.value:
            return result, self._build_preserved_record(result, context, bar, state)

        if not self._can_execute_bar_identity(bar):
            missing = self._missing_bar_identity_dependencies(bar)
            reason = f"Bar identity dependencies not satisfied: {', '.join(missing)}."
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
                BarIdentityState.FAILED.value,
                RESULT_STATUS_DEPENDENCY_BLOCKED,
                dependency_consulted=True,
                missing_dependencies=missing,
            )
            return updated, record

        prerequisite_results, missing_prereqs = self._resolve_prerequisite_results(bar)
        shape_result = self._resolve_shape_code_result(bar)
        if not shape_result:
            missing_prereqs = list(missing_prereqs) + ["SHAPE_CODE"]
        if missing_prereqs:
            reason = (
                "Bar identity prerequisite calculations not calculated: "
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
                BarIdentityState.FAILED.value,
                RESULT_STATUS_DEPENDENCY_BLOCKED,
                dependency_consulted=True,
                missing_dependencies=missing_prereqs,
            )
            return updated, record

        inputs, missing = self._resolve_inputs(
            context,
            bar,
            prerequisite_results,
            shape_result,
        )
        if missing:
            updated = self._build_failed_result(result, inputs, missing)
            record = self._build_record(
                result,
                context,
                bar,
                inputs,
                None,
                BarIdentityState.FAILED.value,
                RESULT_STATUS_LOOKUP_FAILED,
                dependency_consulted=True,
            )
            return updated, record

        resolved_rule = self._rule_resolver.resolve(bar, context)
        inputs = self._finalize_inputs(
            inputs,
            resolved_rule,
            prerequisite_results,
            shape_result,
            context,
        )
        assignment = self._assignment_plan.get(str(bar.get("bar_id", "")), {})
        classification_input = BarIdentityClassificationInput(
            bar_id=str(bar.get("bar_id", "")),
            equivalence_signature=str(inputs.get("equivalence_signature", "")),
            identity_sequence=int(assignment.get("identity_sequence", 0)),
            group_sequence=int(assignment.get("group_sequence", 0)),
            instance_index_in_group=int(assignment.get("instance_index_in_group", 0)),
            group_member_count=int(assignment.get("group_member_count", 0)),
            resolved_rule=resolved_rule,
        )
        classification = self._classifier.classify(classification_input)
        trace = self._build_trace(inputs, classification, resolved_rule)
        identity_metadata = self._build_identity_metadata(
            inputs,
            classification,
            resolved_rule,
        )
        geometry_source = self._geometry_source_from_context(context, bar)
        source_results = [
            shape_result,
            prerequisite_results["CUT_LENGTH"],
            geometry_source,
        ]
        provenance = CalculationProvenanceBuilder.build_from_source_results(source_results)
        updated = self._build_calculated_result(
            result,
            inputs,
            classification,
            trace,
            identity_metadata,
            provenance,
        )
        record = self._build_record(
            result,
            context,
            bar,
            inputs,
            classification,
            BarIdentityState.CALCULATED.value,
            RESULT_STATUS_SUCCESS,
            identity_metadata=identity_metadata,
            dependency_consulted=True,
            calculation_provenance=provenance,
        )
        return updated, record

    def _can_execute_bar_identity(self, bar: dict[str, Any]) -> bool:
        index = bar.get("calculation_index") or {}
        references = index.get("references") or {}
        graph_dependencies = [
            dependency
            for dependency in self._dependency_graph.depends_on(DEPENDENCY_CATEGORY)
            if dependency != "SHAPE_CODE"
        ]
        for dependency in graph_dependencies:
            result_id = references.get(dependency)
            if not result_id:
                return False
            result = self._results_by_id.get(str(result_id))
            if not result:
                return False
        if not self._resolve_shape_code_result(bar):
            return False
        return True

    def _missing_bar_identity_dependencies(self, bar: dict[str, Any]) -> List[str]:
        missing: List[str] = []
        index = bar.get("calculation_index") or {}
        references = index.get("references") or {}
        for dependency in self._dependency_graph.depends_on(DEPENDENCY_CATEGORY):
            if dependency == "SHAPE_CODE":
                if not self._resolve_shape_code_result(bar):
                    missing.append(dependency)
                continue
            result_id = references.get(dependency)
            result = self._results_by_id.get(str(result_id)) if result_id else None
            if not result_id or not result:
                missing.append(dependency)
        return missing

    def _resolve_shape_code_result(self, bar: dict[str, Any]) -> Optional[dict[str, Any]]:
        bar_id = str(bar.get("bar_id", ""))
        for result in self._results_by_id.values():
            if (
                str(result.get("input_bar_id", "")) == bar_id
                and result.get("calculation_type") == SHAPE_CODE_TYPE
                and result.get("calculation_state") == CalculationResultState.CALCULATED.value
            ):
                return result
        return None

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
            resolved[category] = result
        return resolved, missing

    def _resolve_inputs(
        self,
        context: dict[str, Any],
        bar: dict[str, Any],
        prerequisite_results: dict[str, dict[str, Any]],
        shape_result: dict[str, Any],
    ) -> Tuple[dict[str, Any], List[str]]:
        missing: List[str] = []
        diameter = engineering_value_numeric(bar.get("diameter_mm"))
        if diameter is None:
            missing.append("Bar diameter unavailable.")
            diameter = 0

        role = str(bar.get("role") or "UNKNOWN")
        bar_type = str(bar.get("bar_type") or ROLE_TO_BAR_TYPE.get(role, "MAIN_BAR"))
        shape_code = str(shape_result.get("result_value") or "")
        if not shape_code:
            missing.append("Shape code unavailable from indexed result.")

        cut_length_mm = self._numeric_result_value(prerequisite_results.get("CUT_LENGTH"))
        hook_length_mm = self._numeric_result_value(prerequisite_results.get("HOOK_LENGTH"))
        development_length_mm = self._numeric_result_value(
            prerequisite_results.get("DEVELOPMENT_LENGTH")
        )
        lap_length_mm = self._numeric_result_value(prerequisite_results.get("LAP_LENGTH"))
        if cut_length_mm is None:
            missing.append("Cut length unavailable.")
        if hook_length_mm is None:
            missing.append("Hook length unavailable.")
        if development_length_mm is None:
            missing.append("Development length unavailable.")
        if lap_length_mm is None:
            missing.append("Lap length unavailable.")

        geometry_signature = self._build_geometry_signature(context)
        support_configuration = self._build_support_configuration(context)

        inputs: dict[str, Any] = {
            "beam_id": str(bar.get("beam_id", "")),
            "reinforcement_role": role,
            "bar_type": bar_type,
            "bar_diameter_mm": int(diameter),
            "shape_code": shape_code,
            "shape_family": str(
                (shape_result.get("classification_metadata") or {}).get("shape_family", "")
            ),
            "cut_length_mm": int(cut_length_mm or 0),
            "hook_length_mm": int(hook_length_mm or 0),
            "development_length_mm": int(development_length_mm or 0),
            "lap_length_mm": int(lap_length_mm or 0),
            "geometry_signature": geometry_signature,
            "support_configuration": support_configuration,
            "reinforcement_object_id": str(bar.get("bar_id", "")),
            "original_uuid": str(bar.get("uuid") or bar.get("object_uuid") or ""),
            "beam_geometry_reference": (
                (context.get("traceability") or {})
                .get("association_traceability", {})
                .get("beam_geometry_reference", {})
            ),
        }
        assignment = self._assignment_plan.get(str(bar.get("bar_id", "")), {})
        inputs["equivalence_signature"] = str(assignment.get("equivalence_signature", ""))
        inputs["identity_sequence"] = int(assignment.get("identity_sequence", 0))
        inputs["group_sequence"] = int(assignment.get("group_sequence", 0))
        inputs["instance_index_in_group"] = int(assignment.get("instance_index_in_group", 0))
        inputs["group_member_count"] = int(assignment.get("group_member_count", 0))
        return inputs, missing

    @staticmethod
    def _numeric_result_value(result: Optional[dict[str, Any]]) -> Optional[int]:
        if not result:
            return None
        metadata = result.get("cut_length_metadata") or result.get("classification_metadata") or {}
        if metadata.get("value") is not None and str(result.get("calculation_type")) == "CUT_LENGTH":
            return int(metadata["value"])
        value = engineering_value_numeric(result.get("result_value"))
        return int(value) if value is not None else None

    @staticmethod
    def build_equivalence_signature(
        bar: dict[str, Any],
        context: dict[str, Any],
        results_by_id: dict[str, dict[str, Any]],
    ) -> str:
        index = bar.get("calculation_index") or {}
        references = index.get("references") or {}
        role = str(bar.get("role") or "UNKNOWN")
        bar_type = str(bar.get("bar_type") or ROLE_TO_BAR_TYPE.get(role, "MAIN_BAR"))
        diameter = int(engineering_value_numeric(bar.get("diameter_mm")) or 0)

        shape_code = ""
        for result in results_by_id.values():
            if (
                str(result.get("input_bar_id", "")) == str(bar.get("bar_id", ""))
                and result.get("calculation_type") == SHAPE_CODE_TYPE
            ):
                shape_code = str(result.get("result_value") or "")
                break

        def value_for(category: str) -> int:
            result_id = references.get(category)
            result = results_by_id.get(str(result_id)) if result_id else None
            if not result:
                return 0
            if category == "CUT_LENGTH":
                metadata = result.get("cut_length_metadata") or {}
                if metadata.get("value") is not None:
                    return int(metadata["value"])
            numeric = engineering_value_numeric(result.get("result_value"))
            return int(numeric) if numeric is not None else 0

        geometry_signature = BarIdentityDeterminer._build_geometry_signature(context)
        support_configuration = BarIdentityDeterminer._build_support_configuration(context)
        parts = [
            str(bar.get("beam_id", "")),
            role,
            bar_type,
            str(diameter),
            shape_code,
            str(value_for("CUT_LENGTH")),
            str(value_for("HOOK_LENGTH")),
            str(value_for("DEVELOPMENT_LENGTH")),
            str(value_for("LAP_LENGTH")),
            geometry_signature,
            support_configuration,
        ]
        return "|".join(parts)

    @staticmethod
    def _build_geometry_signature(context: dict[str, Any]) -> str:
        parts = [
            str(engineering_value_numeric(context.get("clear_span_mm")) or 0),
            str(engineering_value_numeric(context.get("effective_span_mm")) or 0),
            str(engineering_value_numeric(context.get("beam_width_mm")) or 0),
            str(engineering_value_numeric(context.get("beam_depth_mm")) or 0),
            str(engineering_value_numeric(context.get("cover_side_mm")) or 0),
        ]
        return "|".join(parts)

    @staticmethod
    def _build_support_configuration(context: dict[str, Any]) -> str:
        geometry_ref = (
            (context.get("traceability") or {})
            .get("association_traceability", {})
            .get("beam_geometry_reference", {})
        )
        start = str(geometry_ref.get("support_start_id", ""))
        end = str(geometry_ref.get("support_end_id", ""))
        return f"{start}|{end}"

    @staticmethod
    def _finalize_inputs(
        inputs: dict[str, Any],
        rule: ResolvedBarIdentityRule,
        prerequisite_results: dict[str, dict[str, Any]],
        shape_result: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        finalized = dict(inputs)
        finalized.update(rule.to_grouping_spec())
        finalized["identity_rule_source"] = str(rule.rule_source)
        finalized["cut_length_result_id"] = prerequisite_results["CUT_LENGTH"].get("result_id")
        finalized["hook_length_result_id"] = prerequisite_results["HOOK_LENGTH"].get("result_id")
        finalized["development_length_result_id"] = prerequisite_results[
            "DEVELOPMENT_LENGTH"
        ].get("result_id")
        finalized["lap_length_result_id"] = prerequisite_results["LAP_LENGTH"].get("result_id")
        finalized["shape_code_result_id"] = shape_result.get("result_id")
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
        classification: Any,
        rule: ResolvedBarIdentityRule,
    ) -> List[str]:
        return [
            "Engineering Calculation Dependency Graph",
            "Shape Code",
            "Cut Length",
            "Bar Geometry",
            "Rule Resolver",
            "Classifier",
            rule.rule_description,
            f"Role {inputs['reinforcement_role']}",
            f"Engineering Bar {classification.engineering_bar_id}",
            f"Bar Mark {classification.engineering_bar_mark}",
        ]

    def _build_identity_metadata(
        self,
        inputs: dict[str, Any],
        classification: Any,
        rule: ResolvedBarIdentityRule,
    ) -> dict[str, Any]:
        model_meta = self._cache.model.get("metadata", {})
        return {
            "value": classification.engineering_bar_id,
            "engineering_bar_id": classification.engineering_bar_id,
            "engineering_bar_mark": classification.engineering_bar_mark,
            "engineering_group_id": classification.engineering_group_id,
            "instance_index_in_group": classification.instance_index_in_group,
            "group_member_count": classification.group_member_count,
            "is_duplicate": classification.is_duplicate,
            "equivalence_signature": str(inputs.get("equivalence_signature", "")),
            "unit": "IDENTITY",
            "rule_source": str(rule.rule_source),
            "determination_method": DETERMINATION_METHOD,
            "rule_name": str(rule.rule_name),
            "rule_reference": str(rule.rule_reference),
            "shape_code": str(inputs.get("shape_code", "")),
            "cut_length_used": int(inputs.get("cut_length_mm", 0)),
            "hook_length_used": int(inputs.get("hook_length_mm", 0)),
            "development_length_used": int(inputs.get("development_length_mm", 0)),
            "lap_length_used": int(inputs.get("lap_length_mm", 0)),
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
        classification: Any,
        trace: List[str],
        identity_metadata: dict[str, Any],
        provenance: dict[str, Any],
    ) -> dict[str, Any]:
        updated = dict(result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = CalculationResultState.CALCULATED.value
        updated["result_status"] = RESULT_STATUS_SUCCESS
        updated["result_value"] = classification.engineering_bar_id
        updated["result_unit"] = "IDENTITY"
        updated["classification_inputs"] = dict(inputs)
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = list(trace)
        updated["bar_identity_metadata"] = dict(identity_metadata)
        updated["identity_metadata"] = dict(identity_metadata)
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.8"
        metadata["framework_only"] = False
        metadata["dependency_graph_consulted"] = True
        metadata["engineering_bar_id"] = classification.engineering_bar_id
        metadata["engineering_bar_mark"] = classification.engineering_bar_mark
        metadata["engineering_group_id"] = classification.engineering_group_id
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
        updated["result_unit"] = "IDENTITY"
        updated["classification_inputs"] = dict(inputs)
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = reasons
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.8"
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
            determination_state = BarIdentityState.BLOCKED.value
        elif state == CalculationResultState.DEFERRED.value:
            determination_state = BarIdentityState.DEFERRED.value
        else:
            determination_state = BarIdentityState.DEFERRED.value

        return BarIdentityDeterminer._build_record(
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
        classification: Any | None,
        determination_state: str,
        result_status: str,
        identity_metadata: dict[str, Any] | None = None,
        dependency_consulted: bool = False,
        missing_dependencies: List[str] | None = None,
        calculation_provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "bar_identity_id": None,
            "result_id": result.get("result_id"),
            "bar_id": bar.get("bar_id"),
            "beam_id": bar.get("beam_id"),
            "context_id": context.get("context_id"),
            "specification_id": bar.get("specification_id"),
            "bar_diameter_mm": inputs.get("bar_diameter_mm") or bar.get("diameter_mm"),
            "bar_type": inputs.get("bar_type") or bar.get("bar_type", ""),
            "reinforcement_role": inputs.get("reinforcement_role") or bar.get("role", ""),
            "shape_code": inputs.get("shape_code"),
            "cut_length_mm": inputs.get("cut_length_mm"),
            "engineering_bar_id": classification.engineering_bar_id if classification else None,
            "engineering_bar_mark": classification.engineering_bar_mark if classification else None,
            "engineering_group_id": classification.engineering_group_id if classification else None,
            "instance_index_in_group": (
                classification.instance_index_in_group if classification else None
            ),
            "group_member_count": classification.group_member_count if classification else None,
            "is_duplicate": classification.is_duplicate if classification else None,
            "equivalence_signature": inputs.get("equivalence_signature"),
            "identity_rule_source": inputs.get("identity_rule_source", ""),
            "determination_state": determination_state,
            "result_status": result_status,
            "dependency_graph_consulted": dependency_consulted,
            "classification_inputs": dict(inputs),
            "traceability": {
                "lineage": [
                    "Bar Identity Determination",
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
                "reinforcement_object_id": bar.get("bar_id"),
                "bar_traceability": bar.get("traceability", {}),
                "context_traceability": context.get("traceability", {}),
            },
        }
        if classification:
            record["shape_code"] = inputs.get("shape_code")
        if missing_dependencies:
            record["missing_dependencies"] = list(missing_dependencies)
        if identity_metadata:
            record["identity_metadata"] = dict(identity_metadata)
            record["bar_identity_metadata"] = dict(identity_metadata)
        if calculation_provenance:
            record["calculation_provenance"] = dict(calculation_provenance)
        return record
