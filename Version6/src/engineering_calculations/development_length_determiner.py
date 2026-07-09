"""Development length determiner — Phase I.3."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.engineering_calculations.calculation_provenance.provenance_builder import (
    CalculationProvenanceBuilder,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState
from src.engineering_calculations.development_length_types import (
    ENGINE_NAME,
    RESULT_STATUS_LOOKUP_FAILED,
    RESULT_STATUS_PRESERVED,
    RESULT_STATUS_SUCCESS,
    SOURCE_ENGINE_VERSION,
    DevelopmentLengthState,
)
from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_value import EngineeringValue, engineering_value_numeric
from src.general_notes.ld_table_selector import steel_table_key


def development_length_applied(model: dict[str, Any]) -> bool:
    registry = model.get("development_length_registry", {})
    if registry.get("phase") == "Phase I.3" and registry.get("determination_count", 0) >= 0:
        return True
    if model.get("development_length_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("development_length_complete"))


class DevelopmentLengthDeterminer:
    """Determine development length for a single READY calculation result."""

    def __init__(self, cache: EngineeringRuleCache) -> None:
        self._cache = cache

    def determine(
        self,
        result: dict[str, Any],
        context: dict[str, Any],
        bar: dict[str, Any],
    ) -> Tuple[dict[str, Any], dict[str, Any]]:
        """Return updated calculation result and development length registry record."""
        state = str(result.get("calculation_state", ""))
        if state != CalculationResultState.READY.value:
            return result, self._build_preserved_record(result, context, bar, state)

        inputs, missing = self._resolve_inputs(context, bar)
        if missing:
            updated = self._build_failed_result(result, inputs, missing)
            record = self._build_record(
                result,
                context,
                bar,
                inputs,
                None,
                DevelopmentLengthState.FAILED.value,
                RESULT_STATUS_LOOKUP_FAILED,
            )
            return updated, record

        ld_value = self._lookup_development_length(inputs)
        if ld_value is None:
            reason = (
                "Development length not found in engineering rule cache for "
                f"{inputs['steel_grade']}/{inputs['concrete_grade']}/{inputs['bar_diameter_mm']} mm."
            )
            updated = self._build_failed_result(result, inputs, [reason])
            record = self._build_record(
                result,
                context,
                bar,
                inputs,
                None,
                DevelopmentLengthState.FAILED.value,
                RESULT_STATUS_LOOKUP_FAILED,
            )
            return updated, record

        ld_mm = int(engineering_value_numeric(ld_value) or ld_value.value)
        inputs = self._finalize_inputs(inputs, ld_value)
        trace = self._build_trace(inputs, ld_mm)
        metadata = self._build_development_length_metadata(inputs, ld_value, ld_mm)
        updated = self._build_calculated_result(result, inputs, ld_mm, trace, metadata)
        record = self._build_record(
            result,
            context,
            bar,
            inputs,
            ld_mm,
            DevelopmentLengthState.CALCULATED.value,
            RESULT_STATUS_SUCCESS,
            metadata=metadata,
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

        dev_table_ref = context.get("development_length_table") or {}
        table_label = self._table_label(dev_table_ref)

        inputs: dict[str, Any] = {
            "bar_diameter_mm": int(diameter),
            "steel_grade": str(steel_grade or ""),
            "concrete_grade": str(concrete_grade or ""),
            "development_length_table": table_label,
        }
        return inputs, missing

    def _lookup_development_length(self, inputs: dict[str, Any]) -> Optional[EngineeringValue]:
        return self._cache.get_ld(
            inputs["steel_grade"],
            inputs["concrete_grade"],
            int(inputs["bar_diameter_mm"]),
        )

    @staticmethod
    def _finalize_inputs(inputs: dict[str, Any], ld_value: EngineeringValue) -> dict[str, Any]:
        finalized = dict(inputs)
        selection = ld_value.extra.get("selection_method") or ld_value.table
        if selection:
            finalized["development_length_table"] = DevelopmentLengthDeterminer._format_table_label(
                str(selection)
            )
        code = ld_value.extra.get("code") or ld_value.extra.get("design_code")
        if code:
            finalized["code"] = str(code)
        bond = ld_value.extra.get("bond_condition")
        if bond:
            finalized["bond_condition"] = str(bond)
        return finalized

    @staticmethod
    def _table_label(dev_table_ref: dict[str, Any]) -> str:
        active_key = str(dev_table_ref.get("active_table_key") or "")
        if active_key.upper().startswith("TABLE"):
            return DevelopmentLengthDeterminer._format_table_label(active_key)
        return active_key or "UNKNOWN"

    @staticmethod
    def _format_table_label(table_key: str) -> str:
        normalized = str(table_key or "").strip().upper().replace("-", "_")
        if normalized.startswith("TABLE_"):
            suffix = normalized.split("_", 1)[-1]
            return f"Table-{suffix}"
        return str(table_key)

    @staticmethod
    def _build_trace(inputs: dict[str, Any], ld_mm: int) -> List[str]:
        return [
            f"Read steel grade {inputs['steel_grade']}",
            f"Read concrete grade {inputs['concrete_grade']}",
            f"Selected Development Length {inputs['development_length_table']}",
            f"Read diameter {inputs['bar_diameter_mm']} mm",
            f"Resolved Ld = {ld_mm} mm",
        ]

    def _build_development_length_metadata(
        self,
        inputs: dict[str, Any],
        ld_value: EngineeringValue,
        ld_mm: int,
    ) -> dict[str, Any]:
        normalized_steel = steel_table_key(str(inputs.get("steel_grade", "")))
        concrete = str(inputs.get("concrete_grade", ""))
        diameter = str(int(inputs.get("bar_diameter_mm", 0)))
        model_meta = self._cache.model.get("metadata", {})
        return {
            "value": ld_mm,
            "unit": "mm",
            "source_table": str(inputs.get("development_length_table", "")),
            "steel_grade": str(inputs.get("steel_grade", "")),
            "normalized_steel_grade": normalized_steel,
            "concrete_grade": concrete,
            "bar_diameter_mm": int(inputs.get("bar_diameter_mm", 0)),
            "lookup_path": [
                "development_tables",
                normalized_steel,
                concrete,
                diameter,
            ],
            "lookup_status": "FOUND",
            "rule_cache_version": str(
                model_meta.get("knowledge_version")
                or self._cache.model.get("knowledge_version")
                or SOURCE_ENGINE_VERSION
            ),
            "determination_method": "RULE_TABLE_LOOKUP",
        }

    @staticmethod
    def _build_calculated_result(
        result: dict[str, Any],
        inputs: dict[str, Any],
        ld_mm: int,
        trace: List[str],
        development_length_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        updated = dict(result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = CalculationResultState.CALCULATED.value
        updated["result_status"] = RESULT_STATUS_SUCCESS
        updated["result_value"] = ld_mm
        updated["result_unit"] = "mm"
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = list(trace)
        updated["development_length_metadata"] = dict(development_length_metadata)
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.3"
        metadata["framework_only"] = False
        updated["result_metadata"] = metadata
        provenance = CalculationProvenanceBuilder.build_empty()
        return CalculationProvenanceBuilder.attach(updated, provenance)

    @staticmethod
    def _build_failed_result(
        result: dict[str, Any],
        inputs: dict[str, Any],
        reasons: List[str],
    ) -> dict[str, Any]:
        updated = dict(result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = CalculationResultState.FAILED.value
        updated["result_status"] = RESULT_STATUS_LOOKUP_FAILED
        updated["result_value"] = None
        updated["result_unit"] = "mm"
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = reasons
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.3"
        metadata["lookup_failed"] = True
        updated["result_metadata"] = metadata
        return updated

    @staticmethod
    def _build_preserved_record(
        result: dict[str, Any],
        context: dict[str, Any],
        bar: dict[str, Any],
        state: str,
    ) -> dict[str, Any]:
        determination_state = state
        if state == CalculationResultState.BLOCKED.value:
            determination_state = DevelopmentLengthState.BLOCKED.value
        elif state == CalculationResultState.DEFERRED.value:
            determination_state = DevelopmentLengthState.DEFERRED.value
        else:
            determination_state = DevelopmentLengthState.DEFERRED.value

        return DevelopmentLengthDeterminer._build_record(
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
        ld_mm: Optional[int],
        determination_state: str,
        result_status: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "result_id": result.get("result_id"),
            "bar_id": bar.get("bar_id"),
            "beam_id": bar.get("beam_id"),
            "context_id": context.get("context_id"),
            "specification_id": bar.get("specification_id"),
            "bar_diameter_mm": inputs.get("bar_diameter_mm") or bar.get("diameter_mm"),
            "steel_grade": inputs.get("steel_grade") or bar.get("steel_grade"),
            "concrete_grade": inputs.get("concrete_grade") or context.get("concrete_grade"),
            "development_length_table": inputs.get("development_length_table", ""),
            "development_length_mm": ld_mm,
            "determination_state": determination_state,
            "result_status": result_status,
            "calculation_inputs": dict(inputs),
            "traceability": {
                "lineage": [
                    "Development Length Determination",
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
        if metadata:
            record["development_length_metadata"] = dict(metadata)
        return record
