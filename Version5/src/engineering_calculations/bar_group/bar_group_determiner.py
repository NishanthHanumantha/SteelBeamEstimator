"""Bar group determiner — Phase I.9."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.engineering_calculations.bar_group.bar_group_types import (
    CALCULATION_TYPE,
    DETERMINATION_METHOD,
    ENGINE_NAME,
    RESULT_STATUS_DEPENDENCY_BLOCKED,
    RESULT_STATUS_LOOKUP_FAILED,
    RESULT_STATUS_PRESERVED,
    RESULT_STATUS_SUCCESS,
    SOURCE_ENGINE_VERSION,
    compute_engineering_signature_from_inputs,
    format_engineering_group_id,
    BarGroupState,
)
from src.engineering_calculations.bar_identity.bar_identity_types import BarIdentityState
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_provenance.provenance_builder import (
    CalculationProvenanceBuilder,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState
from src.engineering_calculations.formula_engine.bar_group_classifier import (
    BarGroupMembership,
)
from src.engineering_calculations.rule_resolution.bar_group_rule_resolver import (
    BarGroupRuleResolver,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedBarGroupRule
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


DEPENDENCY_CATEGORY = "BAR_GROUP"
IDENTITY_TYPE = "BAR_IDENTITY"
SHAPE_CODE_TYPE = "SHAPE_CODE"
CUT_LENGTH_TYPE = "CUT_LENGTH"


def bar_group_applied(model: dict[str, Any]) -> bool:
    registry = model.get("bar_group_registry", {})
    if registry.get("phase") == "Phase I.9" and registry.get("determination_count", 0) >= 0:
        return True
    if model.get("bar_group_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("bar_group_complete"))


class BarGroupDeterminer:
    """Determine engineering bar group for aggregated identity members."""

    def __init__(
        self,
        cache: EngineeringRuleCache,
        dependency_graph: CalculationDependencyGraph,
        results_by_id: dict[str, dict[str, Any]],
        identity_records_by_bar: dict[str, dict[str, Any]],
    ) -> None:
        self._cache = cache
        self._dependency_graph = dependency_graph
        self._results_by_id = results_by_id
        self._identity_records_by_bar = identity_records_by_bar
        self._rule_resolver = BarGroupRuleResolver(cache)

    def determine_group(
        self,
        membership: BarGroupMembership,
        group_sequence: int,
        member_results: List[dict[str, Any]],
        context: dict[str, Any],
        resolved_rule: ResolvedBarGroupRule,
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        missing = self._missing_identity_prerequisites(membership.member_bar_ids)
        if missing:
            updated = [
                self._build_failed_result(
                    result,
                    {},
                    [f"Bar group identity prerequisites not calculated: {', '.join(missing)}."],
                )
                for result in member_results
            ]
            record = self._build_record(
                membership,
                group_sequence,
                resolved_rule,
                {},
                BarGroupState.FAILED.value,
                RESULT_STATUS_DEPENDENCY_BLOCKED,
                dependency_consulted=True,
                missing_dependencies=missing,
            )
            return updated, record

        inputs = self._build_group_inputs(membership, group_sequence, resolved_rule)
        expected_signature = compute_engineering_signature_from_inputs(inputs)
        if expected_signature != membership.engineering_signature:
            updated = [
                self._build_failed_result(
                    result,
                    inputs,
                    ["Engineering signature mismatch during group determination."],
                )
                for result in member_results
            ]
            record = self._build_record(
                membership,
                group_sequence,
                resolved_rule,
                inputs,
                BarGroupState.FAILED.value,
                RESULT_STATUS_LOOKUP_FAILED,
                dependency_consulted=True,
            )
            return updated, record

        source_results = self._resolve_provenance_sources(membership, context)
        if len(source_results) < 5:
            updated = [
                self._build_failed_result(
                    result,
                    inputs,
                    ["Insufficient provenance sources for bar group determination."],
                )
                for result in member_results
            ]
            record = self._build_record(
                membership,
                group_sequence,
                resolved_rule,
                inputs,
                BarGroupState.FAILED.value,
                RESULT_STATUS_LOOKUP_FAILED,
                dependency_consulted=True,
            )
            return updated, record

        provenance = CalculationProvenanceBuilder.build_from_source_results(source_results)
        group_metadata = self._build_group_metadata(inputs, membership, resolved_rule)
        trace = self._build_trace(inputs, membership, resolved_rule)
        updated_results = [
            self._build_calculated_result(
                result,
                inputs,
                membership,
                group_sequence,
                trace,
                group_metadata,
                provenance,
            )
            for result in member_results
        ]
        record = self._build_record(
            membership,
            group_sequence,
            resolved_rule,
            inputs,
            BarGroupState.CALCULATED.value,
            RESULT_STATUS_SUCCESS,
            group_metadata=group_metadata,
            dependency_consulted=True,
            calculation_provenance=provenance,
        )
        return updated_results, record

    def determine_preserved(
        self,
        result: dict[str, Any],
        context: dict[str, Any],
        bar: dict[str, Any],
        state: str,
    ) -> Tuple[dict[str, Any], dict[str, Any]]:
        if state == CalculationResultState.BLOCKED.value:
            determination_state = BarGroupState.BLOCKED.value
        else:
            determination_state = BarGroupState.DEFERRED.value

        updated = dict(result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = state
        updated["result_status"] = RESULT_STATUS_PRESERVED
        updated["result_unit"] = "GROUP"
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.9"
        metadata["framework_only"] = False
        metadata["preserved"] = True
        updated["result_metadata"] = metadata

        record = self._build_preserved_record(result, context, bar, determination_state)
        return updated, record

    def resolve_rule(self, context: dict[str, Any]) -> ResolvedBarGroupRule:
        return self._rule_resolver.resolve(context)

    def classify_memberships(
        self,
        identity_records: List[dict[str, Any]],
        context: dict[str, Any],
    ) -> tuple[Any, ...]:
        from src.engineering_calculations.formula_engine.bar_group_classifier import (
            BarGroupClassificationInput,
            BarGroupClassifier,
        )

        resolved_rule = self._rule_resolver.resolve(context)
        return BarGroupClassifier.classify(
            BarGroupClassificationInput(
                resolved_rule=resolved_rule,
                identity_records=tuple(identity_records),
            )
        )

    def _missing_identity_prerequisites(self, member_bar_ids: tuple[str, ...]) -> List[str]:
        missing: List[str] = []
        for bar_id in member_bar_ids:
            identity_record = self._identity_records_by_bar.get(str(bar_id))
            if not identity_record:
                missing.append(str(bar_id))
                continue
            if identity_record.get("determination_state") != BarIdentityState.CALCULATED.value:
                missing.append(str(bar_id))
        return missing

    def _build_group_inputs(
        self,
        membership: BarGroupMembership,
        group_sequence: int,
        rule: ResolvedBarGroupRule,
    ) -> dict[str, Any]:
        representative = self._identity_records_by_bar.get(
            str(membership.member_bar_ids[0] if membership.member_bar_ids else ""),
            {},
        )
        inputs = dict(representative.get("classification_inputs") or {})
        inputs.setdefault("reinforcement_role", representative.get("reinforcement_role"))
        inputs.setdefault("bar_diameter_mm", representative.get("bar_diameter_mm"))
        inputs.setdefault("shape_code", representative.get("shape_code"))
        inputs.setdefault("cut_length_mm", representative.get("cut_length_mm"))
        inputs.setdefault("hook_length_mm", inputs.get("hook_length_mm", 0))
        inputs.setdefault("development_length_mm", inputs.get("development_length_mm", 0))
        inputs.setdefault("lap_length_mm", inputs.get("lap_length_mm", 0))
        inputs["engineering_signature"] = membership.engineering_signature
        inputs["engineering_group_id"] = format_engineering_group_id(group_sequence)
        inputs["group_sequence"] = group_sequence
        inputs["member_bar_ids"] = list(membership.member_bar_ids)
        inputs["member_identity_ids"] = list(membership.member_identity_ids)
        inputs["member_beams"] = list(membership.member_beams)
        inputs["member_roles"] = list(membership.member_roles)
        inputs["diameter"] = membership.diameter_mm
        inputs["member_count"] = len(membership.member_bar_ids)
        inputs["is_duplicate_group"] = len(membership.member_bar_ids) > 1
        inputs.update(rule.to_grouping_spec())
        inputs["rule_source"] = str(rule.rule_source)
        return inputs

    def _resolve_provenance_sources(
        self,
        membership: BarGroupMembership,
        context: dict[str, Any],
    ) -> List[dict[str, Any]]:
        representative_bar = membership.member_bar_ids[0] if membership.member_bar_ids else ""
        identity_record = self._identity_records_by_bar.get(representative_bar, {})
        identity_result = self._resolve_identity_result(representative_bar)
        shape_result = self._resolve_shape_code_result(representative_bar)
        cut_result = self._resolve_cut_length_result(representative_bar)
        geometry_source = self._geometry_source_from_context(context, representative_bar)
        signature_source = self._signature_source_from_inputs(
            membership.engineering_signature,
            identity_record,
        )
        return [
            identity_result,
            shape_result,
            cut_result,
            geometry_source,
            signature_source,
        ]

    def _resolve_identity_result(self, bar_id: str) -> Optional[dict[str, Any]]:
        for result in self._results_by_id.values():
            if (
                str(result.get("input_bar_id", "")) == str(bar_id)
                and result.get("calculation_type") == IDENTITY_TYPE
                and result.get("calculation_state") == CalculationResultState.CALCULATED.value
            ):
                return result
        return None

    def _resolve_shape_code_result(self, bar_id: str) -> Optional[dict[str, Any]]:
        for result in self._results_by_id.values():
            if (
                str(result.get("input_bar_id", "")) == str(bar_id)
                and result.get("calculation_type") == SHAPE_CODE_TYPE
                and result.get("calculation_state") == CalculationResultState.CALCULATED.value
            ):
                return result
        return None

    def _resolve_cut_length_result(self, bar_id: str) -> Optional[dict[str, Any]]:
        for result in self._results_by_id.values():
            if (
                str(result.get("input_bar_id", "")) == str(bar_id)
                and result.get("calculation_type") == CUT_LENGTH_TYPE
                and result.get("calculation_state") == CalculationResultState.CALCULATED.value
            ):
                return result
        return None

    @staticmethod
    def _geometry_source_from_context(
        context: dict[str, Any],
        bar_id: str,
    ) -> dict[str, Any]:
        geometry_ref = (
            (context.get("traceability") or {})
            .get("association_traceability", {})
            .get("beam_geometry_reference", {})
        )
        geometry_id = str(
            geometry_ref.get("beam_geometry_id")
            or context.get("context_id")
            or bar_id
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
    def _signature_source_from_inputs(
        engineering_signature: str,
        identity_record: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "result_id": f"ENGINEERING_SIGNATURE::{engineering_signature}",
            "calculation_type": "ENGINEERING_SIGNATURE",
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": "ENGINEERING_SIGNATURE_ENGINE",
            "source_engine_version": "I.9",
            "result_value": engineering_signature,
            "result_unit": "SIGNATURE",
            "created_timestamp": str(identity_record.get("created_timestamp") or ""),
            "result_metadata": {"determination_phase": "I.9", "immutable": True},
        }

    @staticmethod
    def _build_trace(
        inputs: dict[str, Any],
        membership: BarGroupMembership,
        rule: ResolvedBarGroupRule,
    ) -> List[str]:
        return [
            "Engineering Calculation Dependency Graph",
            "Bar Identity",
            "Shape Code",
            "Cut Length",
            "Bar Geometry",
            "Engineering Signature",
            "Rule Resolver",
            "Classifier",
            rule.rule_description,
            f"Signature {membership.engineering_signature}",
            f"Group {inputs['engineering_group_id']}",
            f"Members {len(membership.member_bar_ids)}",
        ]

    def _build_group_metadata(
        self,
        inputs: dict[str, Any],
        membership: BarGroupMembership,
        rule: ResolvedBarGroupRule,
    ) -> dict[str, Any]:
        model_meta = self._cache.model.get("metadata", {})
        return {
            "value": inputs["engineering_group_id"],
            "engineering_group_id": inputs["engineering_group_id"],
            "engineering_signature": membership.engineering_signature,
            "member_bar_ids": list(membership.member_bar_ids),
            "member_identity_ids": list(membership.member_identity_ids),
            "member_count": len(membership.member_bar_ids),
            "is_duplicate_group": len(membership.member_bar_ids) > 1,
            "unit": "GROUP",
            "rule_source": str(rule.rule_source),
            "determination_method": DETERMINATION_METHOD,
            "rule_name": str(rule.rule_name),
            "rule_reference": str(rule.rule_reference),
            "shape_code": str(inputs.get("shape_code", "")),
            "cut_length_mm": int(inputs.get("cut_length_mm", 0)),
            "hook_length_mm": int(inputs.get("hook_length_mm", 0)),
            "development_length_mm": int(inputs.get("development_length_mm", 0)),
            "lap_length_mm": int(inputs.get("lap_length_mm", 0)),
            "diameter_mm": int(inputs.get("diameter", 0)),
            "geometry_signature": str(inputs.get("geometry_signature", "")),
            "support_configuration": str(inputs.get("support_configuration", "")),
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
        membership: BarGroupMembership,
        group_sequence: int,
        trace: List[str],
        group_metadata: dict[str, Any],
        provenance: dict[str, Any],
    ) -> dict[str, Any]:
        updated = dict(result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = CalculationResultState.CALCULATED.value
        updated["result_status"] = RESULT_STATUS_SUCCESS
        updated["result_value"] = format_engineering_group_id(group_sequence)
        updated["result_unit"] = "GROUP"
        updated["classification_inputs"] = dict(inputs)
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = list(trace)
        updated["bar_group_metadata"] = dict(group_metadata)
        updated["group_metadata"] = dict(group_metadata)
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.9"
        metadata["framework_only"] = False
        metadata["dependency_graph_consulted"] = True
        metadata["engineering_group_id"] = format_engineering_group_id(group_sequence)
        metadata["engineering_signature"] = membership.engineering_signature
        metadata["member_count"] = len(membership.member_bar_ids)
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
        updated["result_unit"] = "GROUP"
        updated["classification_inputs"] = dict(inputs)
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = reasons
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.9"
        metadata["lookup_failed"] = True
        metadata["dependency_graph_consulted"] = True
        updated["result_metadata"] = metadata
        return updated

    @staticmethod
    def _build_preserved_record(
        result: dict[str, Any],
        context: dict[str, Any],
        bar: dict[str, Any],
        determination_state: str,
    ) -> dict[str, Any]:
        return BarGroupDeterminer._build_record(
            membership=None,
            group_sequence=0,
            rule=None,
            inputs={},
            determination_state=determination_state,
            result_status=RESULT_STATUS_PRESERVED,
            result=result,
            context=context,
            bar=bar,
        )

    @staticmethod
    def _build_record(
        membership: BarGroupMembership | None,
        group_sequence: int,
        rule: ResolvedBarGroupRule | None,
        inputs: dict[str, Any],
        determination_state: str,
        result_status: str,
        group_metadata: dict[str, Any] | None = None,
        dependency_consulted: bool = False,
        missing_dependencies: List[str] | None = None,
        calculation_provenance: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        bar: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "bar_group_id": None,
            "group_id": None,
            "engineering_group_id": (
                format_engineering_group_id(group_sequence) if group_sequence else None
            ),
            "engineering_signature": (
                membership.engineering_signature if membership else None
            ),
            "member_bar_ids": list(membership.member_bar_ids) if membership else [],
            "member_identity_ids": list(membership.member_identity_ids) if membership else [],
            "member_beams": list(membership.member_beams) if membership else [],
            "member_roles": list(membership.member_roles) if membership else [],
            "diameter": membership.diameter_mm if membership else None,
            "shape_code": membership.shape_code if membership else None,
            "cut_length": membership.cut_length_mm if membership else None,
            "hook_length": membership.hook_length_mm if membership else None,
            "development_length": membership.development_length_mm if membership else None,
            "lap_length": membership.lap_length_mm if membership else None,
            "geometry_signature": membership.geometry_signature if membership else None,
            "support_configuration": membership.support_configuration if membership else None,
            "member_count": len(membership.member_bar_ids) if membership else 0,
            "is_duplicate_group": (
                len(membership.member_bar_ids) > 1 if membership else False
            ),
            "determination_state": determination_state,
            "result_status": result_status,
            "rule_source": str(rule.rule_source) if rule else "",
            "dependency_graph_consulted": dependency_consulted,
            "classification_inputs": dict(inputs),
            "traceability": {
                "lineage": [
                    "Bar Group Aggregation",
                    "Rule Resolver",
                    "Classifier",
                    "Calculation Provenance",
                    "Engineering Calculation Dependency Graph",
                    "Engineering Calculation Result Framework",
                    "Bar Identity",
                    "Engineering Calculation Context",
                ],
            },
        }
        if result:
            record["result_id"] = result.get("result_id")
            record["bar_id"] = bar.get("bar_id") if bar else result.get("input_bar_id")
            record["beam_id"] = bar.get("beam_id") if bar else result.get("input_beam_id")
            record["context_id"] = context.get("context_id") if context else None
            record["specification_id"] = bar.get("specification_id") if bar else None
            record["traceability"]["result_id"] = result.get("result_id")
            record["traceability"]["bar_id"] = record.get("bar_id")
            record["traceability"]["context_id"] = record.get("context_id")
        if missing_dependencies:
            record["missing_dependencies"] = list(missing_dependencies)
        if group_metadata:
            record["group_metadata"] = dict(group_metadata)
            record["bar_group_metadata"] = dict(group_metadata)
            record["metadata"] = dict(group_metadata)
        if calculation_provenance:
            record["calculation_provenance"] = dict(calculation_provenance)
            record["provenance"] = dict(calculation_provenance)
        return record
