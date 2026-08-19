"""Evaluation-only control checks and phase decision. Not imported by the extractor."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    ALLOWED_FINAL,
    ERR_MERGED,
    ERR_STIRRUP_MIX,
    FAMILY_LONGITUDINAL,
    FAMILY_STIRRUP,
    LAYER_BOTTOM,
    LAYER_TOP,
    PRODUCTION_ACTION,
    SHADOW_ONLY,
)
from .group_model import identity_key


def _row(records: List[Dict[str, Any]], set_key: str, beam_id: str) -> Dict[str, Any]:
    for rec in records:
        if rec.get("set_key") == set_key and rec.get("beam_id") == beam_id:
            return rec
    return {}


def _has_group(groups: List[Dict[str, Any]], *, layer: str, spec: str, family: str = FAMILY_LONGITUDINAL) -> bool:
    return any(
        str(g.get("family")) == family
        and str(g.get("physical_layer")) == layer
        and str(g.get("specification")) == spec
        for g in groups
    )


def _collapsed_same_spec_across_layers(groups: List[Dict[str, Any]], spec: str) -> bool:
    layers = {
        str(g.get("physical_layer"))
        for g in groups
        if str(g.get("specification")) == spec and str(g.get("family")) == FAMILY_LONGITUDINAL
    }
    return len(layers) < 2 and any(str(g.get("specification")) == spec for g in groups)


def evaluate_controls(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    b128 = _row(records, "Fifth", "B128")
    b55 = _row(records, "Fifth", "B55")
    b141 = _row(records, "Fourth", "B141")
    e128 = list(b128.get("expected_groups") or [])
    d128 = list(b128.get("detected_groups") or [])
    e55 = list(b55.get("expected_groups") or [])
    d55 = list(b55.get("detected_groups") or [])
    d141 = list(b141.get("detected_groups") or [])
    e141 = list(b141.get("expected_groups") or [])

    long_e128 = [g for g in e128 if g.get("family") == FAMILY_LONGITUDINAL]
    long_d128 = [g for g in d128 if g.get("family") == FAMILY_LONGITUDINAL]
    b128_ok = (
        _has_group(e128, layer=LAYER_TOP, spec="3Y16")
        and _has_group(e128, layer=LAYER_BOTTOM, spec="3Y16")
        and len(long_e128) >= 2
        and not _collapsed_same_spec_across_layers(d128, "3Y16")
        and b128.get("production_action") == PRODUCTION_ACTION
        and b128.get("shadow_only") is True
    )
    b128_collapsed = _has_group(d128, layer=LAYER_TOP, spec="3Y16") and not _has_group(d128, layer=LAYER_BOTTOM, spec="3Y16")
    # collapse into one group if a single detected group is the only 3Y16
    spec_groups = [g for g in long_d128 if str(g.get("specification")) == "3Y16"]
    b128_merged = len(spec_groups) == 1 and len(long_e128) >= 2

    two_y16 = [g for g in e55 if str(g.get("specification")) == "2Y16"]
    three_y25 = [identity_key(g) for g in e55 if str(g.get("specification")) == "3Y25" and g.get("family") == FAMILY_LONGITUDINAL]
    det_3y25 = [identity_key(g) for g in d55 if str(g.get("specification")) == "3Y25" and g.get("family") == FAMILY_LONGITUDINAL]
    stirrup_ok = any(g.get("family") == FAMILY_STIRRUP for g in e55) and not any(
        g.get("family") == FAMILY_LONGITUDINAL and "L-Y" in str(g.get("specification")) for g in d55
    )
    b55_distinct_same_layer = len(set(three_y25)) >= 1
    b55_not_merged_3y25 = len(set(det_3y25)) >= min(2, len(set(three_y25))) if three_y25 else True
    b55_ok = (
        _has_group(e55, layer=LAYER_TOP, spec="2Y16")
        and stirrup_ok
        and b55.get("production_action") == PRODUCTION_ACTION
        and b55.get("shadow_only") is True
        and ERR_STIRRUP_MIX not in ((b55.get("comparison") or {}).get("errors") or [])
    )

    b141_top = _has_group(d141, layer=LAYER_TOP, spec="5Y16") or _has_group(e141, layer=LAYER_TOP, spec="5Y16")
    b141_not_b128_mode = not (
        _has_group(e141, layer=LAYER_TOP, spec="5Y16")
        and _has_group(e141, layer=LAYER_BOTTOM, spec="5Y16")
    )
    b141_ok = (
        b141_top
        and b141.get("production_action") == PRODUCTION_ACTION
        and b141.get("shadow_only") is True
        and ERR_MERGED not in ((b141.get("comparison") or {}).get("errors") or [])
    )

    return {
        "b128": {
            "expected_top_3y16": _has_group(e128, layer=LAYER_TOP, spec="3Y16"),
            "expected_bottom_3y16": _has_group(e128, layer=LAYER_BOTTOM, spec="3Y16"),
            "detected_top_3y16": _has_group(d128, layer=LAYER_TOP, spec="3Y16"),
            "detected_bottom_3y16": _has_group(d128, layer=LAYER_BOTTOM, spec="3Y16"),
            "longitudinal_expected": len(long_e128),
            "longitudinal_detected": len(long_d128),
            "collapsed_identical_spec": bool(b128_merged or b128_collapsed),
            "ok": b128_ok and not b128_merged,
        },
        "b55": {
            "expected_keys": [identity_key(g) for g in e55],
            "detected_keys": [identity_key(g) for g in d55],
            "two_y16_expected": len(two_y16),
            "same_layer_3y25_expected": three_y25,
            "same_layer_3y25_detected": det_3y25,
            "stirrup_not_mixed": stirrup_ok,
            "ok": b55_ok and b55_distinct_same_layer and b55_not_merged_3y25,
        },
        "b141": {
            "expected_keys": [identity_key(g) for g in e141],
            "detected_keys": [identity_key(g) for g in d141],
            "top_5y16_present": b141_top,
            "not_b128_same_spec_conflict": b141_not_b128_mode,
            "ok": b141_ok,
        },
    }


def classify_capability(aggregate: Dict[str, Any], controls: Dict[str, Any]) -> str:
    merged = int(aggregate.get("merged_distinct_groups") or 0)
    missed = int(aggregate.get("missed_groups") or 0)
    wrong_layer = int(aggregate.get("wrong_layer_count") or 0)
    acc = aggregate.get("overall_group_interpretation_accuracy")
    b128_ok = bool((controls.get("b128") or {}).get("ok"))
    collapsed = bool((controls.get("b128") or {}).get("collapsed_identical_spec"))
    if collapsed or not b128_ok or merged > 0 and missed > 2:
        return "GROUP_INTERPRETATION_NOT_READY"
    if acc == "NOT_EVALUABLE":
        return "GROUP_INTERPRETATION_NOT_READY"
    if isinstance(acc, (int, float)) and acc >= 0.99 and merged == 0 and missed == 0 and wrong_layer == 0:
        return "GROUP_INTERPRETATION_READY"
    if merged > 0 or wrong_layer > 0 or missed > 0 or (isinstance(acc, (int, float)) and acc < 0.85):
        return "GROUP_INTERPRETATION_PARTIAL" if isinstance(acc, (int, float)) and acc >= 0.4 else "GROUP_INTERPRETATION_NOT_READY"
    return "GROUP_INTERPRETATION_PARTIAL"


def classify_phase(
    *,
    tests_ok: bool,
    fingerprints_ok: bool,
    production_mutation: int,
    all_shadow: bool,
    all_no_change: bool,
    six_beams: bool,
    inventories_complete: bool,
) -> Dict[str, str]:
    if not tests_ok:
        return {"decision": "IMPLEMENTATION_FAILED", "strength": "FAILED", "note": "P2.6.9 unit tests failed."}
    if production_mutation or not fingerprints_ok:
        return {"decision": "BENCHMARK_FAILED", "strength": "PRODUCTION_MUTATION", "note": "Fingerprint or production mutation detected."}
    if not all_shadow or not all_no_change:
        return {"decision": "BENCHMARK_FAILED", "strength": "PRODUCTION_LEAK", "note": "A shadow result was not NO_CHANGE / shadow_only."}
    if not six_beams or not inventories_complete:
        return {"decision": "BENCHMARK_FAILED", "strength": "INCOMPLETE_INVENTORY", "note": "Not all six beams produced a complete group inventory."}
    return {
        "decision": "SAFE_SHADOW_BENCHMARK",
        "strength": "DIAGNOSTIC",
        "note": "Group-interpretation benchmark completed without production mutation.",
    }


def production_invariants(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "all_shadow_only": all(r.get("shadow_only") is True for r in records) if records else False,
        "all_no_change": all(r.get("production_action") == PRODUCTION_ACTION for r in records) if records else False,
        "any_production_routing_changed": any(r.get("production_routing_changed") for r in records),
        "count": len(records),
    }


__all__ = [
    "ALLOWED_FINAL",
    "classify_capability",
    "classify_phase",
    "evaluate_controls",
    "production_invariants",
]
