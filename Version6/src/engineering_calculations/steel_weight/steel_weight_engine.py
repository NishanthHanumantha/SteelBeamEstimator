"""Steel weight calculation engine — Phase I.11."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.calculation_context.context_loader import DEFAULT_RULES_PATH
from src.engineering_calculations.bar_group.bar_group_types import BarGroupState
from src.engineering_calculations.bar_identity.bar_identity_types import BarIdentityState
from src.engineering_calculations.bbs.bbs_types import BbsState
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_provenance.provenance_builder import (
    CalculationProvenanceBuilder,
)
from src.engineering_calculations.calculation_result_builder import CalculationResultBuilder
from src.engineering_calculations.calculation_result_registry import CalculationResultRegistry
from src.engineering_calculations.calculation_result_types import (
    CalculationResultState,
    CalculationType,
)
from src.engineering_calculations.steel_weight.steel_weight_calculator import SteelWeightCalculator
from src.engineering_calculations.steel_weight.steel_weight_registry import SteelWeightRegistry
from src.engineering_calculations.steel_weight.steel_weight_types import (
    CALCULATION_TYPE,
    DETERMINATION_METHOD,
    ENGINE_NAME,
    RESULT_STATUS_DEPENDENCY_BLOCKED,
    RESULT_STATUS_LOOKUP_FAILED,
    RESULT_STATUS_PRESERVED,
    RESULT_STATUS_SUCCESS,
    SOURCE_ENGINE_VERSION,
    SteelWeightState,
)
from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_value import engineering_value_numeric


class SteelWeightEngine:
    """Transform engineering bar records into deterministic steel weight outputs."""

    def __init__(
        self,
        rules_path: Path | None = None,
        dependency_graph: CalculationDependencyGraph | None = None,
    ) -> None:
        path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        self._cache = EngineeringRuleCache.get_instance(path)
        self._dependency_graph = dependency_graph or CalculationDependencyGraph.from_spec()
        self._result_builder = CalculationResultBuilder()
        self._calculator = SteelWeightCalculator()

    def determine(
        self,
        results: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        identity_records: List[dict[str, Any]],
        group_records: List[dict[str, Any]],
        bbs_records: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]] | None = None,
        project_id: str = "",
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        context_by_spec = {
            str(item.get("specification_id", "")): item for item in contexts
        }
        identity_by_bar = {
            str(item.get("bar_id", "")): item
            for item in identity_records
            if item.get("bar_id")
        }
        group_by_bar = self._group_records_by_bar(group_records)
        bbs_by_bar = self._bbs_records_by_bar(bbs_records)

        result_registry = CalculationResultRegistry()
        self._initialize_registry_sequence(result_registry, results)
        for result in results:
            result_id = str(result.get("result_id", ""))
            if result_id:
                result_registry.register(result)

        updated_results = self._ensure_steel_weight_results(
            results,
            bars,
            contexts,
            result_registry,
        )
        results_by_bar_type = self._index_results_by_bar_and_type(updated_results)
        result_index = self._build_result_index(updated_results)

        registry = SteelWeightRegistry()
        weight_records: List[dict[str, Any]] = []
        primary_context = contexts[0] if contexts else {}

        sorted_bars = sorted(bars, key=lambda item: str(item.get("bar_id", "")))
        for bar in sorted_bars:
            bar_id = str(bar.get("bar_id", ""))
            spec_id = str(bar.get("specification_id", ""))
            context = context_by_spec.get(spec_id, primary_context)
            weight_result = self._find_weight_result(updated_results, bar_id)
            if not weight_result:
                continue

            initial_state = str(weight_result.get("calculation_state", ""))
            if initial_state in {
                CalculationResultState.DEFERRED.value,
                CalculationResultState.BLOCKED.value,
            }:
                updated, record = self._preserve_weight(
                    weight_result,
                    bar,
                    context,
                    identity_by_bar.get(bar_id),
                    group_by_bar.get(bar_id),
                    bbs_by_bar.get(bar_id),
                    initial_state,
                )
                record["weight_id"] = registry.next_id()
                registry.register(record)
                weight_records.append(record)
                self._apply_result_update(updated_results, result_index, updated)
                continue

            prerequisites = self._resolve_prerequisites(
                bar_id,
                bar,
                context,
                results_by_bar_type.get(bar_id, {}),
                identity_by_bar.get(bar_id),
                group_by_bar.get(bar_id),
                bbs_by_bar.get(bar_id),
            )
            if not prerequisites.get("ready"):
                updated, record = self._blocked_or_deferred_weight(
                    weight_result,
                    bar,
                    context,
                    prerequisites,
                )
                record["weight_id"] = registry.next_id()
                registry.register(record)
                weight_records.append(record)
                self._apply_result_update(updated_results, result_index, updated)
                continue

            calculation = self._calculator.calculate(
                prerequisites["diameter_mm"],
                prerequisites["cut_length_mm"],
            )
            source_results = prerequisites["provenance_sources"]
            provenance = CalculationProvenanceBuilder.build_from_source_results(source_results)
            trace = self._build_trace(prerequisites, calculation)
            metadata = self._build_weight_metadata(prerequisites, calculation)
            updated = self._build_calculated_result(
                weight_result,
                prerequisites,
                calculation,
                metadata,
                trace,
                provenance,
            )
            record = self._build_weight_record(
                bar,
                prerequisites,
                calculation,
                metadata,
                trace,
                provenance,
                SteelWeightState.CALCULATED.value,
                RESULT_STATUS_SUCCESS,
            )
            record["weight_id"] = registry.next_id()
            registry.register(record)
            weight_records.append(record)
            self._apply_result_update(updated_results, result_index, updated)

        primary = drawing_models[0] if drawing_models else {}
        project_registry = SteelWeightRegistry.build_project_registry(
            weight_records,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )

        exports = {
            "engineering_calculation_results": updated_results,
            "steel_weight_results": weight_records,
            "steel_weight_registry": project_registry,
        }
        return updated_results, exports

    def _resolve_prerequisites(
        self,
        bar_id: str,
        bar: dict[str, Any],
        context: dict[str, Any],
        results_by_type: dict[str, dict[str, Any]],
        identity_record: Optional[dict[str, Any]],
        group_record: Optional[dict[str, Any]],
        bbs_record: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        missing: List[str] = []
        cut_result = results_by_type.get(CalculationType.CUT_LENGTH.value)
        shape_result = results_by_type.get(CalculationType.SHAPE_CODE.value)
        bbs_result = results_by_type.get(CalculationType.BBS.value)

        if not cut_result or cut_result.get("calculation_state") != CalculationResultState.CALCULATED.value:
            missing.append("CUT_LENGTH")
        if not shape_result or shape_result.get("calculation_state") != CalculationResultState.CALCULATED.value:
            missing.append("SHAPE_CODE")
        if not identity_record or identity_record.get("determination_state") != BarIdentityState.CALCULATED.value:
            missing.append("BAR_IDENTITY")
        if not group_record or group_record.get("determination_state") != BarGroupState.CALCULATED.value:
            missing.append("BAR_GROUP")
        if not bbs_result or bbs_result.get("calculation_state") != CalculationResultState.CALCULATED.value:
            missing.append("BBS")
        if not bbs_record or bbs_record.get("determination_state") != BbsState.CALCULATED.value:
            missing.append("BBS_RECORD")

        if missing:
            return {"ready": False, "missing": missing}

        cut_length_mm = engineering_value_numeric(cut_result.get("result_value"))
        diameter_mm = self._resolve_diameter_mm(bar, group_record, bbs_record, cut_result)
        if cut_length_mm is None or diameter_mm is None:
            return {"ready": False, "missing": ["NUMERIC_INPUTS"]}

        context_source = self._context_source(context)
        identity_source = self._identity_source(identity_record)
        group_source = self._group_source(group_record)
        provenance_sources = [
            context_source,
            cut_result,
            shape_result,
            identity_source,
            group_source,
            self._bbs_source(bbs_record),
        ]

        return {
            "ready": True,
            "missing": [],
            "bar_id": bar_id,
            "bar_identity_id": str(identity_record.get("bar_identity_id", "")),
            "engineering_group_id": str(group_record.get("engineering_group_id", "")),
            "bar_group_id": str(group_record.get("bar_group_id", "")),
            "bbs_id": str(bbs_record.get("bbs_id", "")),
            "fabrication_mark": str(bbs_record.get("fabrication_mark", "")),
            "shape_code": str(group_record.get("shape_code") or bbs_record.get("shape_code") or ""),
            "role": str(group_record.get("role") or bbs_record.get("role") or bar.get("role", "")),
            "beam_id": str(bar.get("beam_id", "")),
            "fabrication_state": str(bbs_record.get("fabrication_state", "")),
            "diameter_mm": float(diameter_mm),
            "cut_length_mm": float(cut_length_mm),
            "cut_result": cut_result,
            "shape_result": shape_result,
            "bbs_result": bbs_result,
            "identity_record": identity_record,
            "group_record": group_record,
            "bbs_record": bbs_record,
            "context": context,
            "provenance_sources": provenance_sources,
        }

    @staticmethod
    def _resolve_diameter_mm(
        bar: dict[str, Any],
        group_record: dict[str, Any],
        bbs_record: dict[str, Any],
        cut_result: dict[str, Any],
    ) -> Optional[float]:
        for source in (bbs_record, group_record, cut_result.get("cut_length_metadata") or {}, bar):
            value = engineering_value_numeric(source.get("diameter_mm") or source.get("diameter"))
            if value is not None:
                return float(value)
        properties = bar.get("engineering_properties") or bar.get("properties") or {}
        value = engineering_value_numeric(properties.get("diameter_mm") or properties.get("diameter"))
        return float(value) if value is not None else None

    @staticmethod
    def _context_source(context: dict[str, Any]) -> dict[str, Any]:
        return {
            "result_id": str(context.get("context_id", "")),
            "calculation_type": "CALCULATION_CONTEXT",
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": "CALCULATION_CONTEXT_BUILDER",
            "source_engine_version": "I.1",
            "result_value": context.get("context_id"),
            "result_unit": "CONTEXT",
            "created_timestamp": "",
            "result_metadata": {"determination_phase": "I.1"},
        }

    @staticmethod
    def _identity_source(identity_record: dict[str, Any]) -> dict[str, Any]:
        return {
            "result_id": str(identity_record.get("bar_identity_id", "")),
            "calculation_type": CalculationType.BAR_IDENTITY.value,
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": "BAR_IDENTITY_ENGINE",
            "source_engine_version": "I.8",
            "result_value": identity_record.get("identity_value"),
            "result_unit": "IDENTITY",
            "created_timestamp": "",
            "result_metadata": {"determination_phase": "I.8"},
        }

    @staticmethod
    def _group_source(group_record: dict[str, Any]) -> dict[str, Any]:
        return {
            "result_id": str(group_record.get("bar_group_id", "")),
            "calculation_type": CalculationType.BAR_GROUP.value,
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": "BAR_GROUP_ENGINE",
            "source_engine_version": "I.9",
            "result_value": group_record.get("engineering_group_id"),
            "result_unit": "GROUP",
            "created_timestamp": "",
            "result_metadata": {"determination_phase": "I.9"},
        }

    @staticmethod
    def _bbs_source(bbs_record: dict[str, Any]) -> dict[str, Any]:
        return {
            "result_id": str(bbs_record.get("bbs_id", "")),
            "calculation_type": CalculationType.BBS.value,
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": "BBS_ENGINE",
            "source_engine_version": "I.10",
            "result_value": bbs_record.get("fabrication_mark"),
            "result_unit": "SCHEDULE",
            "created_timestamp": "",
            "result_metadata": {"determination_phase": "I.10"},
        }

    def _preserve_weight(
        self,
        weight_result: dict[str, Any],
        bar: dict[str, Any],
        context: dict[str, Any],
        identity_record: Optional[dict[str, Any]],
        group_record: Optional[dict[str, Any]],
        bbs_record: Optional[dict[str, Any]],
        state: str,
    ) -> Tuple[dict[str, Any], dict[str, Any]]:
        updated = dict(weight_result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = state
        updated["result_status"] = RESULT_STATUS_PRESERVED
        updated["result_unit"] = "kg"
        metadata = dict(updated.get("result_metadata") or {})
        metadata["determination_phase"] = "I.11"
        metadata["preserved"] = True
        updated["result_metadata"] = metadata

        if state == CalculationResultState.BLOCKED.value:
            weight_state = SteelWeightState.BLOCKED.value
        else:
            weight_state = SteelWeightState.DEFERRED.value

        record = self._build_weight_record(
            bar,
            {
                "bar_identity_id": str((identity_record or {}).get("bar_identity_id", "")),
                "engineering_group_id": str((group_record or {}).get("engineering_group_id", "")),
                "bbs_id": str((bbs_record or {}).get("bbs_id", "")),
                "fabrication_mark": str((bbs_record or {}).get("fabrication_mark", "")),
                "shape_code": str((group_record or {}).get("shape_code", "")),
                "role": str(bar.get("role", "")),
                "beam_id": str(bar.get("beam_id", "")),
                "fabrication_state": str((bbs_record or {}).get("fabrication_state", "")),
                "diameter_mm": None,
                "cut_length_mm": None,
            },
            {},
            {},
            ["Preserved deferred steel weight"],
            {},
            weight_state,
            RESULT_STATUS_PRESERVED,
        )
        return updated, record

    def _blocked_or_deferred_weight(
        self,
        weight_result: dict[str, Any],
        bar: dict[str, Any],
        context: dict[str, Any],
        prerequisites: dict[str, Any],
    ) -> Tuple[dict[str, Any], dict[str, Any]]:
        missing = prerequisites.get("missing") or []
        updated = dict(weight_result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = CalculationResultState.DEFERRED.value
        updated["result_status"] = RESULT_STATUS_DEPENDENCY_BLOCKED
        updated["result_unit"] = "kg"
        updated["calculation_trace"] = [
            f"Steel weight prerequisites not satisfied: {', '.join(missing)}.",
        ]
        metadata = dict(updated.get("result_metadata") or {})
        metadata["determination_phase"] = "I.11"
        metadata["missing_dependencies"] = list(missing)
        updated["result_metadata"] = metadata

        record = self._build_weight_record(
            bar,
            {
                "bar_identity_id": "",
                "engineering_group_id": "",
                "bbs_id": "",
                "fabrication_mark": "",
                "shape_code": "",
                "role": str(bar.get("role", "")),
                "beam_id": str(bar.get("beam_id", "")),
                "fabrication_state": "",
                "diameter_mm": None,
                "cut_length_mm": None,
            },
            {},
            {},
            updated["calculation_trace"],
            {},
            SteelWeightState.DEFERRED.value,
            RESULT_STATUS_DEPENDENCY_BLOCKED,
            missing_dependencies=missing,
        )
        return updated, record

    @staticmethod
    def _build_trace(prerequisites: dict[str, Any], calculation: dict[str, Any]) -> List[str]:
        return [
            "Engineering Calculation Dependency Graph",
            "Calculation Context",
            "Cut Length",
            "Shape Code",
            "Bar Identity",
            "Engineering Bar Group",
            "Bar Bending Schedule",
            "Steel Weight Calculator",
            prerequisites.get("formula", calculation.get("formula", "")),
            f"Diameter {prerequisites.get('diameter_mm')} mm",
            f"Cut Length {prerequisites.get('cut_length_mm')} mm",
            f"Weight {calculation.get('weight_kg')} kg",
        ]

    @staticmethod
    def _build_weight_metadata(
        prerequisites: dict[str, Any],
        calculation: dict[str, Any],
    ) -> dict[str, Any]:
        metadata = dict(calculation)
        metadata.update({
            "bar_identity_id": prerequisites.get("bar_identity_id"),
            "engineering_group_id": prerequisites.get("engineering_group_id"),
            "bbs_id": prerequisites.get("bbs_id"),
            "fabrication_mark": prerequisites.get("fabrication_mark"),
            "shape_code": prerequisites.get("shape_code"),
            "role": prerequisites.get("role"),
            "fabrication_state": prerequisites.get("fabrication_state"),
            "determination_method": DETERMINATION_METHOD,
            "dependency_graph_consulted": True,
        })
        return metadata

    @staticmethod
    def _build_calculated_result(
        weight_result: dict[str, Any],
        prerequisites: dict[str, Any],
        calculation: dict[str, Any],
        metadata: dict[str, Any],
        trace: List[str],
        provenance: dict[str, Any],
    ) -> dict[str, Any]:
        updated = dict(weight_result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = CalculationResultState.CALCULATED.value
        updated["result_status"] = RESULT_STATUS_SUCCESS
        updated["result_value"] = calculation.get("weight_kg")
        updated["result_unit"] = "kg"
        updated["calculation_inputs"] = {
            "diameter_mm": prerequisites.get("diameter_mm"),
            "cut_length_mm": prerequisites.get("cut_length_mm"),
            "engineering_group_id": prerequisites.get("engineering_group_id"),
            "bbs_id": prerequisites.get("bbs_id"),
            "fabrication_mark": prerequisites.get("fabrication_mark"),
        }
        updated["classification_inputs"] = dict(updated["calculation_inputs"])
        updated["calculation_trace"] = list(trace)
        updated["weight_metadata"] = dict(metadata)
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        result_metadata = dict(weight_result.get("result_metadata") or {})
        result_metadata["determination_phase"] = "I.11"
        result_metadata["framework_only"] = False
        result_metadata["dependency_graph_consulted"] = True
        result_metadata["weight_kg_raw"] = calculation.get("weight_kg_raw")
        updated["result_metadata"] = result_metadata
        return CalculationProvenanceBuilder.attach(updated, provenance)

    @staticmethod
    def _build_weight_record(
        bar: dict[str, Any],
        prerequisites: dict[str, Any],
        calculation: dict[str, Any],
        metadata: dict[str, Any],
        trace: List[str],
        provenance: dict[str, Any],
        status: str,
        result_status: str,
        missing_dependencies: List[str] | None = None,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "weight_id": None,
            "bar_id": bar.get("bar_id"),
            "bar_identity_id": prerequisites.get("bar_identity_id"),
            "engineering_group_id": prerequisites.get("engineering_group_id"),
            "bbs_id": prerequisites.get("bbs_id"),
            "fabrication_mark": prerequisites.get("fabrication_mark"),
            "diameter": prerequisites.get("diameter_mm"),
            "cut_length": prerequisites.get("cut_length_mm"),
            "cut_length_mm": prerequisites.get("cut_length_mm"),
            "weight_kg": calculation.get("weight_kg"),
            "weight_kg_raw": calculation.get("weight_kg_raw"),
            "unit": calculation.get("unit", "kg"),
            "formula": calculation.get("formula"),
            "density": calculation.get("density_kg_m3"),
            "status": status,
            "result_status": result_status,
            "shape_code": prerequisites.get("shape_code"),
            "role": prerequisites.get("role"),
            "beam_id": prerequisites.get("beam_id") or bar.get("beam_id"),
            "fabrication_state": prerequisites.get("fabrication_state"),
            "trace": list(trace),
            "metadata": dict(metadata),
            "weight_metadata": dict(metadata),
            "traceability": {
                "lineage": [
                    "Steel Weight Calculation Engine",
                    "Steel Weight Calculator",
                    "Calculation Provenance",
                    "Engineering Calculation Dependency Graph",
                ],
                "bar_id": bar.get("bar_id"),
            },
        }
        if missing_dependencies:
            record["missing_dependencies"] = list(missing_dependencies)
        if provenance:
            record["calculation_provenance"] = dict(provenance)
            record["provenance"] = dict(provenance)
        return record

    def _ensure_steel_weight_results(
        self,
        results: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        registry: CalculationResultRegistry,
    ) -> List[dict[str, Any]]:
        context_by_spec = {
            str(item.get("specification_id", "")): item for item in contexts
        }
        bars_with_weight = {
            str(item.get("input_bar_id", ""))
            for item in results
            if item.get("calculation_type") == CALCULATION_TYPE
        }
        updated_results = list(results)
        sorted_bars = sorted(bars, key=lambda item: str(item.get("bar_id", "")))
        for bar in sorted_bars:
            bar_id = str(bar.get("bar_id", ""))
            if bar_id in bars_with_weight:
                continue
            spec_id = str(bar.get("specification_id", ""))
            context = context_by_spec.get(spec_id, {})
            readiness = bar.get("calculation_readiness") or {}
            result = self._result_builder.build(
                context,
                bar,
                readiness,
                CalculationType.STEEL_WEIGHT,
                registry=registry,
            )
            registry.register(result)
            updated_results.append(result)
        return updated_results

    @staticmethod
    def _group_records_by_bar(group_records: List[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        mapping: dict[str, dict[str, Any]] = {}
        for record in group_records:
            bar_id = str(record.get("bar_id", ""))
            if bar_id:
                mapping[bar_id] = record
            for member_id in record.get("member_bar_ids") or []:
                mapping[str(member_id)] = record
        return mapping

    @staticmethod
    def _bbs_records_by_bar(bbs_records: List[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        mapping: dict[str, dict[str, Any]] = {}
        for record in bbs_records:
            bar_id = str(record.get("bar_id", ""))
            if bar_id:
                mapping[bar_id] = record
            for member_id in record.get("member_bar_ids") or []:
                mapping[str(member_id)] = record
        return mapping

    @staticmethod
    def _index_results_by_bar_and_type(
        results: List[dict[str, Any]],
    ) -> dict[str, dict[str, dict[str, Any]]]:
        mapping: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for result in results:
            bar_id = str(result.get("input_bar_id", ""))
            calc_type = str(result.get("calculation_type", ""))
            if bar_id and calc_type:
                mapping[bar_id][calc_type] = result
        return mapping

    @staticmethod
    def _build_result_index(results: List[dict[str, Any]]) -> dict[str, int]:
        index: dict[str, int] = {}
        for position, result in enumerate(results):
            result_id = str(result.get("result_id", ""))
            if result_id:
                index[result_id] = position
        return index

    @staticmethod
    def _find_weight_result(results: List[dict[str, Any]], bar_id: str) -> Optional[dict[str, Any]]:
        for result in results:
            if (
                str(result.get("input_bar_id", "")) == bar_id
                and result.get("calculation_type") == CALCULATION_TYPE
            ):
                return result
        return None

    @staticmethod
    def _apply_result_update(
        results: List[dict[str, Any]],
        result_index: dict[str, int],
        updated: dict[str, Any],
    ) -> None:
        result_id = str(updated.get("result_id", ""))
        if result_id in result_index:
            results[result_index[result_id]] = updated

    @staticmethod
    def _initialize_registry_sequence(
        registry: CalculationResultRegistry,
        results: List[dict[str, Any]],
    ) -> None:
        max_sequence = 0
        for result in results:
            result_id = str(result.get("result_id", ""))
            if "::" not in result_id:
                continue
            try:
                max_sequence = max(max_sequence, int(result_id.rsplit("::", 1)[-1]))
            except ValueError:
                continue
        registry._sequence = max_sequence

    @staticmethod
    def sync_calculation_result_registry(
        results: List[dict[str, Any]],
        registry: dict[str, Any],
    ) -> dict[str, Any]:
        updated = dict(registry)
        by_state: dict[str, int] = defaultdict(int)
        for result in results:
            by_state[str(result.get("calculation_state", ""))] += 1

        state_counts = {
            "ready": by_state.get(CalculationResultState.READY.value, 0),
            "deferred": by_state.get(CalculationResultState.DEFERRED.value, 0),
            "blocked": by_state.get(CalculationResultState.BLOCKED.value, 0),
            "failed": by_state.get(CalculationResultState.FAILED.value, 0),
            "calculated": by_state.get(CalculationResultState.CALCULATED.value, 0),
        }
        updated["results_by_state"] = dict(by_state)
        updated["state_counts"] = state_counts
        return updated

    @staticmethod
    def build_project_exports(
        results: List[dict[str, Any]],
        weight_records: List[dict[str, Any]],
        weight_registry: dict[str, Any],
        calc_registry: dict[str, Any],
    ) -> dict[str, Any]:
        synced_registry = SteelWeightEngine.sync_calculation_result_registry(
            results,
            calc_registry,
        )
        return {
            "engineering_calculation_results": results,
            "calculation_result_registry": synced_registry,
            "steel_weight_results": weight_records,
            "steel_weight_registry": weight_registry,
        }
