"""BBS determiner — Phase I.10."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.engineering_calculations.bar_group.bar_group_types import BarGroupState
from src.engineering_calculations.bbs.bbs_types import (
    DETERMINATION_METHOD,
    ENGINE_NAME,
    FabricationState,
    RESULT_STATUS_DEPENDENCY_BLOCKED,
    RESULT_STATUS_LOOKUP_FAILED,
    RESULT_STATUS_PRESERVED,
    RESULT_STATUS_SUCCESS,
    SOURCE_ENGINE_VERSION,
    BbsState,
    format_fabrication_mark,
    format_schedule_description,
)
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_provenance.provenance_builder import (
    CalculationProvenanceBuilder,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState
from src.engineering_calculations.formula_engine.bbs_classifier import BbsScheduleMembership
from src.engineering_calculations.rule_resolution.bbs_rule_resolver import BbsRuleResolver
from src.engineering_calculations.rule_resolution.rule_types import ResolvedBbsRule
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


DEPENDENCY_CATEGORY = "BBS"
IDENTITY_TYPE = "BAR_IDENTITY"
SHAPE_CODE_TYPE = "SHAPE_CODE"
CUT_LENGTH_TYPE = "CUT_LENGTH"
BAR_GROUP_TYPE = "BAR_GROUP"


def bbs_applied(model: dict[str, Any]) -> bool:
    registry = model.get("bbs_registry", {})
    if registry.get("phase") == "Phase I.10" and registry.get("determination_count", 0) >= 0:
        return True
    if model.get("bbs_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("bbs_complete"))


class BbsDeterminer:
    """Determine BBS schedule record for an engineering bar group."""

    def __init__(
        self,
        cache: EngineeringRuleCache,
        dependency_graph: CalculationDependencyGraph,
        results_by_id: dict[str, dict[str, Any]],
        group_records_by_id: dict[str, dict[str, Any]],
    ) -> None:
        self._cache = cache
        self._dependency_graph = dependency_graph
        self._results_by_id = results_by_id
        self._group_records_by_id = group_records_by_id
        self._rule_resolver = BbsRuleResolver(cache)

    def resolve_rule(self, context: dict[str, Any]) -> ResolvedBbsRule:
        return self._rule_resolver.resolve(context)

    def classify_memberships(
        self,
        group_records: List[dict[str, Any]],
        context: dict[str, Any],
    ) -> tuple[BbsScheduleMembership, ...]:
        from src.engineering_calculations.formula_engine.bbs_classifier import (
            BbsClassificationInput,
            BbsClassifier,
        )

        resolved_rule = self._rule_resolver.resolve(context)
        return BbsClassifier.classify(
            BbsClassificationInput(
                resolved_rule=resolved_rule,
                group_records=tuple(group_records),
            )
        )

    def determine_schedule(
        self,
        membership: BbsScheduleMembership,
        schedule_position: int,
        member_results: List[dict[str, Any]],
        group_record: dict[str, Any],
        context: dict[str, Any],
        resolved_rule: ResolvedBbsRule,
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        if not self._can_execute_bbs(group_record):
            missing = self._missing_bbs_dependencies(group_record)
            updated = [
                self._build_failed_result(
                    result,
                    {},
                    [f"BBS bar group prerequisites not satisfied: {', '.join(missing)}."],
                )
                for result in member_results
            ]
            record = self._build_record(
                membership,
                schedule_position,
                resolved_rule,
                {},
                group_record,
                BbsState.FAILED.value,
                FabricationState.FABRICATION_DEFERRED.value,
                RESULT_STATUS_DEPENDENCY_BLOCKED,
                dependency_consulted=True,
                missing_dependencies=missing,
            )
            return updated, record

        inputs = self._build_schedule_inputs(
            membership,
            schedule_position,
            resolved_rule,
            group_record,
        )
        source_results = self._resolve_provenance_sources(membership, group_record, context)
        if len(source_results) < 6:
            updated = [
                self._build_failed_result(
                    result,
                    inputs,
                    ["Insufficient provenance sources for BBS determination."],
                )
                for result in member_results
            ]
            record = self._build_record(
                membership,
                schedule_position,
                resolved_rule,
                inputs,
                group_record,
                BbsState.FAILED.value,
                FabricationState.FABRICATION_DEFERRED.value,
                RESULT_STATUS_LOOKUP_FAILED,
                dependency_consulted=True,
            )
            return updated, record

        provenance = CalculationProvenanceBuilder.build_from_source_results(source_results)
        schedule_metadata = self._build_schedule_metadata(inputs, membership, resolved_rule)
        trace = self._build_trace(inputs, membership, resolved_rule)
        updated_results = [
            self._build_calculated_result(
                result,
                inputs,
                schedule_metadata,
                trace,
                provenance,
            )
            for result in member_results
        ]
        record = self._build_record(
            membership,
            schedule_position,
            resolved_rule,
            inputs,
            group_record,
            BbsState.CALCULATED.value,
            FabricationState.FABRICATION_READY.value,
            RESULT_STATUS_SUCCESS,
            schedule_metadata=schedule_metadata,
            dependency_consulted=True,
            calculation_provenance=provenance,
        )
        return updated_results, record

    def determine_preserved(
        self,
        group_record: dict[str, Any],
        member_results: List[dict[str, Any]],
        context: dict[str, Any],
        bar: dict[str, Any],
        state: str,
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        if state == CalculationResultState.BLOCKED.value:
            bbs_state = BbsState.BLOCKED.value
            fab_state = FabricationState.FABRICATION_BLOCKED.value
        else:
            bbs_state = BbsState.DEFERRED.value
            fab_state = FabricationState.FABRICATION_DEFERRED.value

        updated = []
        for result in member_results:
            item = dict(result)
            item["engine_name"] = ENGINE_NAME
            item["calculation_state"] = state
            item["result_status"] = RESULT_STATUS_PRESERVED
            item["result_unit"] = "SCHEDULE"
            metadata = dict(item.get("result_metadata") or {})
            metadata["determination_phase"] = "I.10"
            metadata["preserved"] = True
            item["result_metadata"] = metadata
            updated.append(item)

        record = self._build_preserved_record(group_record, bar, bbs_state, fab_state)
        return updated, record

    def _can_execute_bbs(self, group_record: dict[str, Any]) -> bool:
        return group_record.get("determination_state") == BarGroupState.CALCULATED.value

    def _missing_bbs_dependencies(self, group_record: dict[str, Any]) -> List[str]:
        missing: List[str] = []
        if group_record.get("determination_state") != BarGroupState.CALCULATED.value:
            missing.append("BAR_GROUP")
        bar_group_id = str(group_record.get("bar_group_id", ""))
        if not bar_group_id or bar_group_id not in self._group_records_by_id:
            missing.append("BAR_GROUP_RECORD")
        return missing

    def _build_schedule_inputs(
        self,
        membership: BbsScheduleMembership,
        schedule_position: int,
        rule: ResolvedBbsRule,
        group_record: dict[str, Any],
    ) -> dict[str, Any]:
        primary_role = membership.member_roles[0] if membership.member_roles else ""
        fabrication_mark = format_fabrication_mark(schedule_position)
        description = format_schedule_description(
            membership.member_count,
            membership.diameter_mm,
            primary_role,
            membership.shape_code,
        )
        inputs = {
            "fabrication_mark": fabrication_mark,
            "schedule_position": schedule_position,
            "schedule_description": description,
            "engineering_group_id": membership.engineering_group_id,
            "engineering_signature": membership.engineering_signature,
            "bar_group_id": membership.bar_group_id,
            "member_bar_ids": list(membership.member_bar_ids),
            "member_identity_ids": list(membership.member_identity_ids),
            "member_beams": list(membership.member_beams),
            "member_roles": list(membership.member_roles),
            "shape_code": membership.shape_code,
            "cut_length_mm": membership.cut_length_mm,
            "diameter": membership.diameter_mm,
            "role": primary_role,
            "geometry_signature": membership.geometry_signature,
            "support_configuration": membership.support_configuration,
            "member_count": membership.member_count,
            "fabrication_state": FabricationState.FABRICATION_READY.value,
        }
        inputs.update(rule.to_schedule_spec())
        inputs["rule_source"] = str(rule.rule_source)
        inputs["group_record_id"] = group_record.get("bar_group_id")
        return inputs

    def _resolve_provenance_sources(
        self,
        membership: BbsScheduleMembership,
        group_record: dict[str, Any],
        context: dict[str, Any],
    ) -> List[dict[str, Any]]:
        representative_bar = membership.member_bar_ids[0] if membership.member_bar_ids else ""
        identity_result = self._resolve_identity_result(representative_bar)
        shape_result = self._resolve_shape_code_result(representative_bar)
        cut_result = self._resolve_cut_length_result(representative_bar)
        group_source = self._group_source_from_record(group_record)
        signature_source = self._signature_source_from_group(group_record)
        bbs_source = self._bbs_source_from_inputs(membership, group_record)
        return [
            identity_result,
            shape_result,
            cut_result,
            group_source,
            signature_source,
            bbs_source,
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
    def _group_source_from_record(group_record: dict[str, Any]) -> dict[str, Any]:
        return {
            "result_id": str(group_record.get("bar_group_id", "")),
            "calculation_type": BAR_GROUP_TYPE,
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": "BAR_GROUP_ENGINE",
            "source_engine_version": "I.9",
            "result_value": group_record.get("engineering_group_id"),
            "result_unit": "GROUP",
            "created_timestamp": "",
            "result_metadata": {"determination_phase": "I.9"},
        }

    @staticmethod
    def _signature_source_from_group(group_record: dict[str, Any]) -> dict[str, Any]:
        signature = str(group_record.get("engineering_signature", ""))
        return {
            "result_id": f"ENGINEERING_SIGNATURE::{signature}",
            "calculation_type": "ENGINEERING_SIGNATURE",
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": "ENGINEERING_SIGNATURE_ENGINE",
            "source_engine_version": "I.9",
            "result_value": signature,
            "result_unit": "SIGNATURE",
            "created_timestamp": "",
            "result_metadata": {"determination_phase": "I.9", "immutable": True},
        }

    @staticmethod
    def _bbs_source_from_inputs(
        membership: BbsScheduleMembership,
        group_record: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "result_id": f"BBS_GENERATION::{membership.engineering_group_id}",
            "calculation_type": "BBS_GENERATION",
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": ENGINE_NAME,
            "source_engine_version": SOURCE_ENGINE_VERSION,
            "result_value": membership.engineering_group_id,
            "result_unit": "SCHEDULE",
            "created_timestamp": "",
            "result_metadata": {"determination_phase": "I.10", "foundation_only": True},
        }

    @staticmethod
    def _build_trace(
        inputs: dict[str, Any],
        membership: BbsScheduleMembership,
        rule: ResolvedBbsRule,
    ) -> List[str]:
        return [
            "Engineering Calculation Dependency Graph",
            "Bar Identity",
            "Engineering Bar Group",
            "Shape Code",
            "Cut Length",
            "Engineering Signature",
            "BBS Generation",
            "Rule Resolver",
            "Classifier",
            rule.rule_description,
            f"Fabrication Mark {inputs['fabrication_mark']}",
            f"Schedule {inputs['schedule_description']}",
        ]

    def _build_schedule_metadata(
        self,
        inputs: dict[str, Any],
        membership: BbsScheduleMembership,
        rule: ResolvedBbsRule,
    ) -> dict[str, Any]:
        model_meta = self._cache.model.get("metadata", {})
        return {
            "value": inputs["fabrication_mark"],
            "fabrication_mark": inputs["fabrication_mark"],
            "engineering_group_id": membership.engineering_group_id,
            "engineering_signature": membership.engineering_signature,
            "bar_group_id": membership.bar_group_id,
            "member_bar_ids": list(membership.member_bar_ids),
            "member_identity_ids": list(membership.member_identity_ids),
            "member_count": membership.member_count,
            "schedule_position": int(inputs["schedule_position"]),
            "schedule_description": str(inputs["schedule_description"]),
            "fabrication_state": FabricationState.FABRICATION_READY.value,
            "shape_code": membership.shape_code,
            "cut_length_mm": membership.cut_length_mm,
            "diameter_mm": membership.diameter_mm,
            "role": inputs.get("role", ""),
            "unit": "SCHEDULE",
            "rule_source": str(rule.rule_source),
            "determination_method": DETERMINATION_METHOD,
            "rule_name": str(rule.rule_name),
            "rule_reference": str(rule.rule_reference),
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
        schedule_metadata: dict[str, Any],
        trace: List[str],
        provenance: dict[str, Any],
    ) -> dict[str, Any]:
        updated = dict(result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = CalculationResultState.CALCULATED.value
        updated["result_status"] = RESULT_STATUS_SUCCESS
        updated["result_value"] = inputs["fabrication_mark"]
        updated["result_unit"] = "SCHEDULE"
        updated["classification_inputs"] = dict(inputs)
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = list(trace)
        updated["bbs_metadata"] = dict(schedule_metadata)
        updated["schedule_metadata"] = dict(schedule_metadata)
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.10"
        metadata["framework_only"] = False
        metadata["dependency_graph_consulted"] = True
        metadata["fabrication_mark"] = inputs["fabrication_mark"]
        metadata["engineering_group_id"] = inputs["engineering_group_id"]
        metadata["engineering_signature"] = inputs["engineering_signature"]
        metadata["fabrication_state"] = FabricationState.FABRICATION_READY.value
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
        updated["result_unit"] = "SCHEDULE"
        updated["classification_inputs"] = dict(inputs)
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = reasons
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.10"
        metadata["lookup_failed"] = True
        updated["result_metadata"] = metadata
        return updated

    @staticmethod
    def _build_preserved_record(
        group_record: dict[str, Any],
        bar: dict[str, Any],
        determination_state: str,
        fabrication_state: str,
    ) -> dict[str, Any]:
        return BbsDeterminer._build_record(
            membership=None,
            schedule_position=0,
            rule=None,
            inputs={},
            group_record=group_record,
            determination_state=determination_state,
            fabrication_state=fabrication_state,
            result_status=RESULT_STATUS_PRESERVED,
            bar=bar,
        )

    @staticmethod
    def _build_record(
        membership: BbsScheduleMembership | None,
        schedule_position: int,
        rule: ResolvedBbsRule | None,
        inputs: dict[str, Any],
        group_record: dict[str, Any],
        determination_state: str,
        fabrication_state: str,
        result_status: str,
        schedule_metadata: dict[str, Any] | None = None,
        dependency_consulted: bool = False,
        missing_dependencies: List[str] | None = None,
        calculation_provenance: dict[str, Any] | None = None,
        bar: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "bbs_id": None,
            "fabrication_mark": inputs.get("fabrication_mark") if inputs else None,
            "engineering_group_id": (
                membership.engineering_group_id if membership else group_record.get("engineering_group_id")
            ),
            "engineering_signature": (
                membership.engineering_signature if membership else group_record.get("engineering_signature")
            ),
            "bar_group_id": (
                membership.bar_group_id if membership else group_record.get("bar_group_id")
            ),
            "member_bar_ids": list(membership.member_bar_ids) if membership else [],
            "member_identity_ids": list(membership.member_identity_ids) if membership else [],
            "member_beams": list(membership.member_beams) if membership else [],
            "member_roles": list(membership.member_roles) if membership else [],
            "shape_code": membership.shape_code if membership else group_record.get("shape_code"),
            "cut_length": membership.cut_length_mm if membership else group_record.get("cut_length"),
            "diameter": membership.diameter_mm if membership else group_record.get("diameter"),
            "role": inputs.get("role") if inputs else None,
            "geometry_signature": (
                membership.geometry_signature if membership else group_record.get("geometry_signature")
            ),
            "support_configuration": (
                membership.support_configuration if membership else group_record.get("support_configuration")
            ),
            "schedule_position": schedule_position or None,
            "schedule_description": inputs.get("schedule_description") if inputs else None,
            "fabrication_state": fabrication_state,
            "determination_state": determination_state,
            "result_status": result_status,
            "rule_source": str(rule.rule_source) if rule else "",
            "dependency_graph_consulted": dependency_consulted,
            "classification_inputs": dict(inputs),
            "traceability": {
                "lineage": [
                    "Bar Bending Schedule Foundation",
                    "Rule Resolver",
                    "Classifier",
                    "Calculation Provenance",
                    "Engineering Calculation Dependency Graph",
                    "Engineering Bar Group",
                    "Bar Identity",
                ],
            },
        }
        if bar:
            record["bar_id"] = bar.get("bar_id")
            record["beam_id"] = bar.get("beam_id")
            record["traceability"]["bar_id"] = bar.get("bar_id")
        if missing_dependencies:
            record["missing_dependencies"] = list(missing_dependencies)
        if schedule_metadata:
            record["bbs_metadata"] = dict(schedule_metadata)
            record["schedule_metadata"] = dict(schedule_metadata)
            record["metadata"] = dict(schedule_metadata)
        if calculation_provenance:
            record["calculation_provenance"] = dict(calculation_provenance)
            record["provenance"] = dict(calculation_provenance)
        return record
