"""Hook length determiner — Phase I.4."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.engineering_calculations.calculation_provenance.provenance_builder import (
    CalculationProvenanceBuilder,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState
from src.engineering_calculations.hook_length_types import (
    DETERMINATION_METHOD,
    ENGINE_NAME,
    RESULT_STATUS_LOOKUP_FAILED,
    RESULT_STATUS_PRESERVED,
    RESULT_STATUS_SUCCESS,
    RULE_SOURCE_GENERAL_NOTES,
    SOURCE_ENGINE_VERSION,
    HookLengthState,
)
from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_value import engineering_value_numeric


def hook_length_applied(model: dict[str, Any]) -> bool:
    registry = model.get("hook_length_registry", {})
    if registry.get("phase") == "Phase I.4" and registry.get("determination_count", 0) >= 0:
        return True
    if model.get("hook_length_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("hook_length_complete"))


@dataclass(frozen=True)
class HookRuleEntry:
    hook_type: str
    hook_angle: int
    hook_multiplier: int
    rule_source: str
    rule_type: str


class HookRuleCatalog:
    """Build hook rule catalog exclusively from structural detailing rules."""

    def __init__(self, cache: EngineeringRuleCache) -> None:
        self._entries = self._build_catalog(cache)
        self._by_angle: dict[int, List[HookRuleEntry]] = {}
        for entry in self._entries:
            self._by_angle.setdefault(entry.hook_angle, []).append(entry)

    @property
    def entries(self) -> List[HookRuleEntry]:
        return list(self._entries)

    def lookup(self, hook_angle: int, hook_type: str = "STANDARD") -> Optional[HookRuleEntry]:
        candidates = self._by_angle.get(int(hook_angle), [])
        if not candidates:
            return None
        typed = [item for item in candidates if item.hook_type == hook_type]
        pool = typed or candidates
        return sorted(pool, key=lambda item: item.hook_multiplier)[0]

    @staticmethod
    def _build_catalog(cache: EngineeringRuleCache) -> List[HookRuleEntry]:
        structural = cache.model.get("structural_detailing_rules", {})
        bend_rules = list(structural.get("bend_rules", []))
        entries: List[HookRuleEntry] = []
        current_angle: Optional[int] = None

        for rule in bend_rules:
            angle = HookRuleCatalog._extract_angle(rule)
            if angle is not None:
                current_angle = angle

            multiplier = HookRuleCatalog._extract_multiplier(rule)
            if multiplier is None:
                continue

            rule_angle = current_angle if current_angle is not None else 90
            provenance = rule.get("provenance") or {}
            source = str(provenance.get("source") or RULE_SOURCE_GENERAL_NOTES)
            entries.append(
                HookRuleEntry(
                    hook_type="STANDARD",
                    hook_angle=int(rule_angle),
                    hook_multiplier=int(multiplier),
                    rule_source=source,
                    rule_type=str(rule.get("rule_type", "BEND_MULTIPLIER")),
                )
            )

        return entries

    @staticmethod
    def _extract_angle(rule: dict[str, Any]) -> Optional[int]:
        angle = rule.get("angle")
        if isinstance(angle, dict):
            value = angle.get("angle_deg")
            if value is not None:
                return int(value)
        return None

    @staticmethod
    def _extract_multiplier(rule: dict[str, Any]) -> Optional[int]:
        raw = rule.get("hook_multiplier")
        if raw is None:
            raw = rule.get("multiplier_db")
        value = engineering_value_numeric(raw)
        if value is None and rule.get("rule_type") == "BEND_MULTIPLIER":
            provenance = rule.get("provenance") or {}
            value = engineering_value_numeric(provenance.get("value"))
        return int(value) if value is not None else None


class HookLengthDeterminer:
    """Determine hook length for a single READY calculation result."""

    def __init__(self, cache: EngineeringRuleCache) -> None:
        self._cache = cache
        self._catalog = HookRuleCatalog(cache)

    def determine(
        self,
        result: dict[str, Any],
        context: dict[str, Any],
        bar: dict[str, Any],
        specification: Optional[dict[str, Any]] = None,
    ) -> Tuple[dict[str, Any], dict[str, Any]]:
        state = str(result.get("calculation_state", ""))
        if state != CalculationResultState.READY.value:
            return result, self._build_preserved_record(result, context, bar, state)

        inputs, missing = self._resolve_inputs(context, bar, specification)
        if missing:
            updated = self._build_failed_result(result, inputs, missing)
            record = self._build_record(
                result,
                context,
                bar,
                inputs,
                None,
                HookLengthState.FAILED.value,
                RESULT_STATUS_LOOKUP_FAILED,
            )
            return updated, record

        rule_entry = self._catalog.lookup(
            int(inputs["hook_angle"]),
            str(inputs.get("hook_type", "STANDARD")),
        )
        if rule_entry is None:
            reason = (
                "Hook rule not found in structural detailing rules for "
                f"{inputs['hook_angle']}° / {inputs.get('hook_type', 'STANDARD')}."
            )
            updated = self._build_failed_result(result, inputs, [reason])
            record = self._build_record(
                result,
                context,
                bar,
                inputs,
                None,
                HookLengthState.FAILED.value,
                RESULT_STATUS_LOOKUP_FAILED,
            )
            return updated, record

        inputs = self._finalize_inputs(inputs, rule_entry)
        hook_mm = int(inputs["hook_multiplier"] * inputs["bar_diameter_mm"])
        trace = self._build_trace(inputs, hook_mm)
        hook_metadata = self._build_hook_metadata(inputs, hook_mm)
        updated = self._build_calculated_result(result, inputs, hook_mm, trace, hook_metadata)
        record = self._build_record(
            result,
            context,
            bar,
            inputs,
            hook_mm,
            HookLengthState.CALCULATED.value,
            RESULT_STATUS_SUCCESS,
            hook_metadata=hook_metadata,
        )
        return updated, record

    def _resolve_inputs(
        self,
        context: dict[str, Any],
        bar: dict[str, Any],
        specification: Optional[dict[str, Any]],
    ) -> Tuple[dict[str, Any], List[str]]:
        missing: List[str] = []
        diameter_raw = bar.get("diameter_mm")
        diameter = engineering_value_numeric(diameter_raw)
        if diameter is None:
            missing.append("Bar diameter unavailable.")
            diameter = 0

        hook_angle = self._resolve_hook_angle(bar, specification)
        if hook_angle is None:
            missing.append("Hook angle unavailable from structural detailing rules.")
            hook_angle = 0

        hook_type = self._resolve_hook_type(bar, specification)
        hook_rule_ref = context.get("hook_rule") or {}
        hook_rule_source = str(hook_rule_ref.get("source") or RULE_SOURCE_GENERAL_NOTES)

        inputs: dict[str, Any] = {
            "bar_diameter_mm": int(diameter),
            "hook_type": hook_type,
            "hook_angle": int(hook_angle),
            "hook_rule_source": hook_rule_source,
        }
        return inputs, missing

    def _resolve_hook_angle(
        self,
        bar: dict[str, Any],
        specification: Optional[dict[str, Any]],
    ) -> Optional[int]:
        for source in (specification or {}, bar):
            for field in ("hook", "hook_angle"):
                parsed = self._parse_angle(source.get(field))
                if parsed is not None:
                    return parsed

        angles = sorted({entry.hook_angle for entry in self._catalog.entries})
        return angles[0] if angles else None

    @staticmethod
    def _resolve_hook_type(
        bar: dict[str, Any],
        specification: Optional[dict[str, Any]],
    ) -> str:
        for source in (specification or {}, bar):
            hook_type = source.get("hook_type")
            if hook_type:
                return str(hook_type).upper()
        return "STANDARD"

    @staticmethod
    def _parse_angle(value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, dict):
            nested = value.get("angle_deg")
            if nested is not None:
                return int(nested)
        text = str(value)
        match = re.search(r"(90|135|180)", text)
        if match:
            return int(match.group(1))
        numeric = engineering_value_numeric(value)
        return int(numeric) if numeric is not None else None

    @staticmethod
    def _finalize_inputs(inputs: dict[str, Any], rule_entry: HookRuleEntry) -> dict[str, Any]:
        finalized = dict(inputs)
        finalized["hook_multiplier"] = int(rule_entry.hook_multiplier)
        finalized["hook_type"] = str(rule_entry.hook_type)
        finalized["hook_angle"] = int(rule_entry.hook_angle)
        finalized["hook_rule_source"] = str(rule_entry.rule_source)
        return finalized

    @staticmethod
    def _build_trace(inputs: dict[str, Any], hook_mm: int) -> List[str]:
        return [
            "Engineering Rules",
            "Hook Rules",
            f"{inputs['hook_angle']}°",
            f"Multiplier {inputs['hook_multiplier']}",
            f"{inputs['bar_diameter_mm']} mm",
            f"{hook_mm} mm",
        ]

    def _build_hook_metadata(self, inputs: dict[str, Any], hook_mm: int) -> dict[str, Any]:
        model_meta = self._cache.model.get("metadata", {})
        return {
            "value": hook_mm,
            "unit": "mm",
            "hook_type": str(inputs.get("hook_type", "STANDARD")),
            "hook_angle": int(inputs.get("hook_angle", 0)),
            "multiplier": int(inputs.get("hook_multiplier", 0)),
            "diameter_mm": int(inputs.get("bar_diameter_mm", 0)),
            "rule_source": str(inputs.get("hook_rule_source", RULE_SOURCE_GENERAL_NOTES)),
            "determination_method": DETERMINATION_METHOD,
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
        hook_mm: int,
        trace: List[str],
        hook_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        updated = dict(result)
        updated["engine_name"] = ENGINE_NAME
        updated["calculation_state"] = CalculationResultState.CALCULATED.value
        updated["result_status"] = RESULT_STATUS_SUCCESS
        updated["result_value"] = hook_mm
        updated["result_unit"] = "mm"
        updated["calculation_inputs"] = dict(inputs)
        updated["calculation_trace"] = list(trace)
        updated["hook_metadata"] = dict(hook_metadata)
        updated["source_engine_version"] = SOURCE_ENGINE_VERSION
        metadata = dict(result.get("result_metadata") or {})
        metadata["determination_phase"] = "I.4"
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
        metadata["determination_phase"] = "I.4"
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
        if state == CalculationResultState.BLOCKED.value:
            determination_state = HookLengthState.BLOCKED.value
        elif state == CalculationResultState.DEFERRED.value:
            determination_state = HookLengthState.DEFERRED.value
        else:
            determination_state = HookLengthState.DEFERRED.value

        return HookLengthDeterminer._build_record(
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
        hook_mm: Optional[int],
        determination_state: str,
        result_status: str,
        hook_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "result_id": result.get("result_id"),
            "bar_id": bar.get("bar_id"),
            "beam_id": bar.get("beam_id"),
            "context_id": context.get("context_id"),
            "specification_id": bar.get("specification_id"),
            "bar_diameter_mm": inputs.get("bar_diameter_mm") or bar.get("diameter_mm"),
            "hook_type": inputs.get("hook_type", ""),
            "hook_angle": inputs.get("hook_angle"),
            "hook_multiplier": inputs.get("hook_multiplier"),
            "hook_rule_source": inputs.get("hook_rule_source", ""),
            "hook_length_mm": hook_mm,
            "determination_state": determination_state,
            "result_status": result_status,
            "calculation_inputs": dict(inputs),
            "traceability": {
                "lineage": [
                    "Hook Length Determination",
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
        if hook_metadata:
            record["hook_metadata"] = dict(hook_metadata)
        return record
