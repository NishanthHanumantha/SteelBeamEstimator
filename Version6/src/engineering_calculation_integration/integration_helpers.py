"""Shared helpers for recovered bar integration status."""

from __future__ import annotations

from typing import Any, Dict, List, Set


def index_calc_results(results: List[dict[str, Any]], calc_type: str) -> Dict[str, dict[str, Any]]:
    indexed: Dict[str, dict[str, Any]] = {}
    for result in results:
        if str(result.get("calculation_type") or "") != calc_type:
            continue
        bar_id = str(result.get("input_bar_id") or "")
        if bar_id:
            indexed[bar_id] = result
    return indexed


def is_production_calc_success(result: dict[str, Any] | None) -> bool:
    if not result:
        return False
    return (
        str(result.get("calculation_state") or "") == "CALCULATED"
        and str(result.get("result_status") or "") == "SUCCESS"
    )


def collect_bbs_bar_ids(bbs_results: List[dict[str, Any]]) -> Set[str]:
    bar_ids: Set[str] = set()
    for item in bbs_results:
        bar_id = str(item.get("bar_id") or "")
        if bar_id:
            bar_ids.add(bar_id)
        for member_id in item.get("member_bar_ids") or []:
            bar_ids.add(str(member_id))
    return bar_ids


def is_steel_generated(
    steel_result: dict[str, Any] | None,
    calc_result: dict[str, Any] | None,
) -> bool:
    if is_production_calc_success(calc_result):
        value = calc_result.get("result_value")
        return value is not None and float(value) > 0
    if not steel_result:
        return False
    weight = steel_result.get("weight_kg")
    return (
        str(steel_result.get("result_status") or "") == "SUCCESS"
        and weight is not None
        and float(weight) > 0
    )


def is_identity_generated(
    identity_result: dict[str, Any] | None,
    calc_result: dict[str, Any] | None,
) -> bool:
    if is_production_calc_success(calc_result):
        return bool(calc_result.get("result_value"))
    if not identity_result:
        return False
    return str(identity_result.get("result_status") or "") == "SUCCESS"


def is_cut_length_generated(
    cut_result: dict[str, Any] | None,
    calc_result: dict[str, Any] | None,
) -> bool:
    if is_production_calc_success(calc_result):
        return calc_result.get("result_value") is not None
    if not cut_result:
        return False
    return str(cut_result.get("result_status") or "") == "SUCCESS"


def recovered_integration_complete(model: dict[str, Any], recovered_bar_ids: Set[str]) -> bool:
    if not recovered_bar_ids:
        return True

    results = model.get("engineering_calculation_results") or []
    identity_calc = index_calc_results(results, "BAR_IDENTITY")
    cut_calc = index_calc_results(results, "CUT_LENGTH")
    steel_calc = index_calc_results(results, "STEEL_WEIGHT")
    bbs_bar_ids = collect_bbs_bar_ids(model.get("bbs_results") or [])
    bars_by_id = {
        str(bar.get("bar_id") or ""): bar for bar in model.get("reinforcement_bars") or [] if bar.get("bar_id")
    }

    for bar_id in recovered_bar_ids:
        bar = bars_by_id.get(bar_id, {})
        if not (bar.get("calculation_index") or {}).get("references"):
            return False
        if not is_production_calc_success(identity_calc.get(bar_id)):
            return False
        if not is_production_calc_success(cut_calc.get(bar_id)):
            return False
        if not is_steel_generated(None, steel_calc.get(bar_id)):
            return False
        if bar_id not in bbs_bar_ids:
            return False
    return True
