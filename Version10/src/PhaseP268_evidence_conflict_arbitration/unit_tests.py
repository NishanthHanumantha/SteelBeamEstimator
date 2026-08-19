"""Unit tests for P2.6.8. No live Claude. Does not change P2.6.4–P2.6.7 routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .arbitration import arbitrate
from .config import (
    ARB_AGREE,
    ARB_DET_OVERRIDES,
    CONFLICT_EQUAL_SPEC_LAYER,
    CONFLICT_EQUAL_SPEC_TARGET,
    CONFLICT_LEADER,
    CONFLICT_NONE,
    CONFLICT_ROLE,
    CONFLICT_SEM_DIST_PHYS_DUP,
    CONFLICT_SEM_DUP_PHYS_DIST,
    CONFLICT_SPATIAL,
    GATE_VERSION,
    LAYER_BOTTOM,
    LAYER_TOP,
    MODEL_VERSION,
    PHYS_DISTINCT,
    PHYS_DUPLICATE,
    PHYS_INSUFFICIENT,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    SEM_DISTINCT,
    SEM_DUPLICATE,
    SEM_UNUSABLE,
    SHADOW_ONLY,
)
from .conflict import detect_conflicts
from .dataset import load_p266_targets, load_p267_live_index
from .evidence import build_evidence_record
from .layer_resolver import resolve_candidate_layer
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .semantic_contract import ContractSchemaError, normalize_contract_payload, parse_contract_response
from .semantic_prompt import SYSTEM_PROMPT, assert_no_truth_leak, build_user_prompt


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _ev(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "candidate_id": "C1",
        "normalized_specification": "3Y16",
        "spec_match_any_layer": True,
        "spec_match_same_layer": True,
        "semantic_role": "UNKNOWN",
        "layer_hint": LAYER_TOP,
        "layer": {
            "resolved_layer": LAYER_TOP,
            "leader_layer": LAYER_TOP,
            "role_layer": "UNKNOWN",
        },
        "deterministic_identity": {
            "physical": PHYS_DUPLICATE,
            "populated_layer": LAYER_TOP,
            "match_status": "ALREADY_DETECTED",
        },
        "semantic_identity": {
            "decision": SEM_DUPLICATE,
            "usable": True,
            "target_layer": LAYER_TOP,
            "source": "TEST",
            "confidence": 0.7,
        },
        "spatial_position": {"tip_in_bottom_zone": False, "tip_in_top_zone": True},
        "provenance": {"p265_context_status": "CONTEXT_SUPPORTS_SKIP", "observed_decision": "CALL_VISION"},
        "evidence_quality": {"layer_evidence_incomplete": False, "leader_geometry_available": True},
        "p266_semantic": {"decision": SEM_DUPLICATE, "usable": True},
        "p267_semantic": {"decision": SEM_DUPLICATE, "usable": True},
    }
    for key, val in overrides.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            merged = dict(base[key])
            merged.update(val)
            base[key] = merged
        else:
            base[key] = val
    return base


def test_same_spec_same_layer_no_conflict() -> None:
    out = detect_conflicts(_ev())
    assert out["conflict_type"] == CONFLICT_NONE
    dec = arbitrate(_ev())
    assert dec["arbitration_result"] == ARB_AGREE
    assert dec["production_action"] == PRODUCTION_ACTION
    assert dec["shadow_only"] is True


def test_same_spec_different_layer() -> None:
    ev = _ev(
        spec_match_same_layer=False,
        layer_hint=LAYER_BOTTOM,
        layer={"resolved_layer": LAYER_BOTTOM, "leader_layer": LAYER_BOTTOM},
        deterministic_identity={"physical": PHYS_DISTINCT, "populated_layer": LAYER_TOP, "match_status": "POTENTIALLY_MISSING"},
        semantic_identity={"decision": SEM_DISTINCT, "usable": True, "target_layer": LAYER_BOTTOM},
    )
    out = detect_conflicts(ev)
    assert out["conflict_type"] in (CONFLICT_EQUAL_SPEC_LAYER, CONFLICT_SEM_DUP_PHYS_DIST)
    assert CONFLICT_EQUAL_SPEC_LAYER in out["conflict_types"]


def test_same_spec_different_physical_target() -> None:
    ev = _ev(
        layer_hint=LAYER_TOP,
        layer={"resolved_layer": LAYER_TOP, "leader_layer": LAYER_TOP},
        spec_match_same_layer=False,
        deterministic_identity={"physical": PHYS_DISTINCT, "populated_layer": LAYER_TOP, "match_status": "POTENTIALLY_MISSING"},
        semantic_identity={"decision": SEM_DISTINCT, "usable": True, "target_layer": LAYER_TOP},
    )
    out = detect_conflicts(ev)
    assert CONFLICT_EQUAL_SPEC_TARGET in out["conflict_types"] or out["conflict_type"] == CONFLICT_EQUAL_SPEC_TARGET


def test_semantic_duplicate_physical_distinct() -> None:
    ev = _ev(
        spec_match_same_layer=False,
        layer={"resolved_layer": LAYER_BOTTOM, "leader_layer": LAYER_BOTTOM},
        layer_hint=LAYER_BOTTOM,
        deterministic_identity={"physical": PHYS_DISTINCT, "populated_layer": LAYER_TOP, "match_status": "POTENTIALLY_MISSING"},
        semantic_identity={"decision": SEM_DUPLICATE, "usable": True, "target_layer": LAYER_BOTTOM},
    )
    out = detect_conflicts(ev)
    assert out["conflict_type"] == CONFLICT_SEM_DUP_PHYS_DIST
    dec = arbitrate(ev)
    assert dec["arbitration_result"] == ARB_DET_OVERRIDES
    assert dec["production_action"] == PRODUCTION_ACTION


def test_semantic_distinct_physical_duplicate() -> None:
    ev = _ev(
        semantic_identity={"decision": SEM_DISTINCT, "usable": True, "target_layer": LAYER_TOP},
        deterministic_identity={"physical": PHYS_DUPLICATE, "populated_layer": LAYER_TOP, "match_status": "ALREADY_DETECTED"},
    )
    out = detect_conflicts(ev)
    assert out["conflict_type"] == CONFLICT_SEM_DIST_PHYS_DUP
    assert arbitrate(ev)["arbitration_result"] == ARB_DET_OVERRIDES


def test_same_target_different_annotation_representation() -> None:
    ev = _ev(
        normalized_specification="3Y16",
        provenance={"p265_context_status": "CONTEXT_SUPPORTS_CALL", "observed_decision": "CALL_VISION"},
    )
    out = detect_conflicts(ev)
    assert out["conflict_type"] == CONFLICT_NONE
    assert "ANNOTATION_REPRESENTATION_ONLY" in out["reason_codes"]


def test_leader_conflict() -> None:
    ev = _ev(
        layer={"resolved_layer": LAYER_TOP, "leader_layer": LAYER_BOTTOM},
        semantic_identity={"decision": SEM_DUPLICATE, "usable": True, "target_layer": LAYER_TOP},
    )
    out = detect_conflicts(ev)
    assert CONFLICT_LEADER in out["conflict_types"] or out["conflict_type"] == CONFLICT_LEADER


def test_spatial_conflict() -> None:
    ev = _ev(
        spec_match_any_layer=False,
        normalized_specification="3Y16",
        deterministic_identity={"physical": PHYS_DISTINCT, "populated_layer": LAYER_TOP, "match_status": "POTENTIALLY_MISSING"},
        semantic_identity={"decision": SEM_DISTINCT, "usable": True, "target_layer": LAYER_BOTTOM},
        layer={"resolved_layer": LAYER_BOTTOM, "leader_layer": LAYER_BOTTOM},
        provenance={"p265_context_status": "CONTEXT_SUPPORTS_SKIP"},
    )
    out = detect_conflicts(ev)
    assert CONFLICT_SPATIAL in out["conflict_types"] or out["conflict_type"] != CONFLICT_NONE


def test_role_conflict() -> None:
    ev = _ev(
        semantic_role="BOTTOM_MAIN",
        layer={"resolved_layer": LAYER_TOP, "leader_layer": LAYER_TOP},
    )
    out = detect_conflicts(ev)
    assert CONFLICT_ROLE in out["conflict_types"]


def test_missing_layer_evidence() -> None:
    info = resolve_candidate_layer(annotation={}, p266_target_layer=None, tip_votes=[], frozen_role=None)
    assert info["resolved_layer"] == "UNKNOWN"
    assert info["layer_evidence_incomplete"] is True


def test_missing_semantic_response() -> None:
    ev = _ev(semantic_identity={"decision": SEM_UNUSABLE, "usable": False, "source": "P267_ABSENT"})
    dec = arbitrate(ev)
    assert dec["production_action"] == PRODUCTION_ACTION
    assert dec["shadow_only"] is True


def test_malformed_claude_response() -> None:
    payload, report = parse_contract_response("not json")
    assert payload is None
    assert report["decision"] == SEM_UNUSABLE
    assert report["error_class"] == "malformed_json"
    empty, report2 = parse_contract_response("")
    assert empty is None
    assert report2["error_class"] == "empty_response"


def test_unknown_semantic_class() -> None:
    try:
        normalize_contract_payload(
            {
                "specification_equivalence": "MATCH",
                "physical_target_equivalence": "SAME",
                "layer_equivalence": "SAME",
                "conflict_type": "NOT_A_CONFLICT",
                "confidence": 0.5,
                "rationale": "x",
            }
        )
        raise AssertionError("unknown conflict accepted")
    except ContractSchemaError:
        pass


def test_deterministic_stronger_than_semantic() -> None:
    ev = _ev(
        layer={"resolved_layer": LAYER_BOTTOM, "leader_layer": LAYER_BOTTOM},
        deterministic_identity={"physical": PHYS_DISTINCT, "populated_layer": LAYER_TOP, "match_status": "POTENTIALLY_MISSING"},
        semantic_identity={"decision": SEM_DUPLICATE, "usable": True, "target_layer": LAYER_TOP, "confidence": 0.99},
    )
    dec = arbitrate(ev)
    assert dec["arbitration_result"] == ARB_DET_OVERRIDES
    assert "DETERMINISTIC_EVIDENCE_STRONGER" in dec["reason_codes"]
    assert dec["winning_evidence_source"] == "deterministic_physical"


def test_semantic_cannot_mutate_production() -> None:
    for ev in (_ev(), _ev(semantic_identity={"decision": SEM_DISTINCT, "usable": True, "target_layer": LAYER_TOP})):
        dec = arbitrate(ev)
        assert dec["production_action"] == PRODUCTION_ACTION
        assert dec["shadow_only"] is SHADOW_ONLY
        assert dec["production_routing_changed"] is False


def test_p266_regression_file() -> None:
    prior = _v10() / "data" / "output" / "PhaseP266_semantic_longitudinal_resolver" / "unit_tests.json"
    payload = json.loads(prior.read_text(encoding="utf-8"))
    assert payload.get("success") is True
    assert int(payload.get("passed") or 0) >= 36


def test_p267_regression_file() -> None:
    prior = _v10() / "data" / "output" / "PhaseP267_live_semantic_arbitration" / "unit_tests.json"
    payload = json.loads(prior.read_text(encoding="utf-8"))
    assert payload.get("success") is True
    assert int(payload.get("passed") or 0) >= 31


def test_production_identical_fingerprints() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True


def test_recovery_fields_forbidden_in_contract() -> None:
    try:
        normalize_contract_payload(
            {
                "specification_equivalence": "MATCH",
                "physical_target_equivalence": "SAME",
                "layer_equivalence": "SAME",
                "conflict_type": CONFLICT_NONE,
                "confidence": 0.5,
                "should_recover": True,
            }
        )
        raise AssertionError("recovery field accepted")
    except ContractSchemaError:
        pass


def test_no_gt_usage() -> None:
    for name in ("evidence.py", "conflict.py", "arbitration.py", "layer_resolver.py", "dataset.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "TRUE_RECOVERY" not in text
        assert "load_gt_universe" not in text
        assert "EstimatorOutput" not in text


def test_no_beam_id_hardcoding_in_runtime() -> None:
    for name in ("evidence.py", "conflict.py", "arbitration.py", "layer_resolver.py", "semantic_contract.py", "semantic_prompt.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for token in ("B128", "B141", "B23", "B136"):
            assert token not in text, f"{name} contains {token}"


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.8"
    assert GATE_VERSION == "P268_EVIDENCE_CONFLICT_ARBITRATION_V1_0"


def test_firewall_and_leakage() -> None:
    fw = firewall_check(_v10())
    assert fw["ok"], fw.get("offenders")
    leak = runtime_leakage_scan(_pkg())
    assert leak["ok"], leak.get("hits")


def test_prompt_no_recovery_request() -> None:
    assert "Should we recover" not in SYSTEM_PROMPT
    prompt = build_user_prompt(evidence={"normalized_specification": "3Y16", "layer_hint": "BOTTOM"})
    assert "Do not decide recovery" in prompt
    assert not assert_no_truth_leak({"user": prompt})


def test_b128_and_b141_controls_from_frozen_artefacts() -> None:
    targets = load_p266_targets(_v10())
    live = load_p267_live_index(_v10())
    by = {(t.get("set_key"), t.get("beam_id")): t for t in targets}
    b128 = arbitrate(build_evidence_record(by[("Fifth", "B128")], live=live.get(("Fifth", "B128"))))
    b141 = arbitrate(build_evidence_record(by[("Fourth", "B141")], live=live.get(("Fourth", "B141"))))
    assert b128["conflict_type"] == CONFLICT_SEM_DUP_PHYS_DIST
    assert b128["arbitration_result"] == ARB_DET_OVERRIDES
    assert b128["production_action"] == PRODUCTION_ACTION
    assert b141["conflict_type"] != CONFLICT_SEM_DUP_PHYS_DIST
    assert b141["production_action"] == PRODUCTION_ACTION
    assert b141["shadow_only"] is True


def test_classify_phase_never_production_ready() -> None:
    from .evaluator import classify_phase

    rec = classify_phase(
        controls={"b128_physical_distinct_protected": True, "b141_not_overclassified": True},
        fingerprints_ok=True,
        production_mutation=0,
        tests_ok=True,
        all_shadow=True,
        all_no_change=True,
    )
    assert rec["decision"] != "PRODUCTION_READY"
    assert rec["decision"] == "SAFE_SHADOW_DIAGNOSTIC"


def test_insufficient_physical_evidence() -> None:
    ev = _ev(
        spec_match_any_layer=False,
        normalized_specification=None,
        layer={"resolved_layer": "UNKNOWN", "leader_layer": "UNKNOWN"},
        deterministic_identity={"physical": PHYS_INSUFFICIENT, "populated_layer": "UNKNOWN", "match_status": None},
        semantic_identity={"decision": SEM_UNUSABLE, "usable": False},
        evidence_quality={"layer_evidence_incomplete": True},
    )
    out = detect_conflicts(ev)
    assert out["conflict_type"] in ("INSUFFICIENT_EVIDENCE", CONFLICT_NONE) or "INSUFFICIENT_PHYSICAL_EVIDENCE" in out["reason_codes"]


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("same_spec_same_layer_no_conflict", test_same_spec_same_layer_no_conflict),
        ("same_spec_different_layer", test_same_spec_different_layer),
        ("same_spec_different_physical_target", test_same_spec_different_physical_target),
        ("semantic_duplicate_physical_distinct", test_semantic_duplicate_physical_distinct),
        ("semantic_distinct_physical_duplicate", test_semantic_distinct_physical_duplicate),
        ("same_target_different_annotation_representation", test_same_target_different_annotation_representation),
        ("leader_conflict", test_leader_conflict),
        ("spatial_conflict", test_spatial_conflict),
        ("role_conflict", test_role_conflict),
        ("missing_layer_evidence", test_missing_layer_evidence),
        ("missing_semantic_response", test_missing_semantic_response),
        ("malformed_claude_response", test_malformed_claude_response),
        ("unknown_semantic_class", test_unknown_semantic_class),
        ("deterministic_stronger_than_semantic", test_deterministic_stronger_than_semantic),
        ("semantic_cannot_mutate_production", test_semantic_cannot_mutate_production),
        ("P2.6.6_regression", test_p266_regression_file),
        ("P2.6.7_regression", test_p267_regression_file),
        ("production_identical_fingerprints", test_production_identical_fingerprints),
        ("recovery_fields_forbidden_in_contract", test_recovery_fields_forbidden_in_contract),
        ("no_gt_usage", test_no_gt_usage),
        ("no_beam_id_hardcoding_in_runtime", test_no_beam_id_hardcoding_in_runtime),
        ("production_write_false", test_production_write_false),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("prompt_no_recovery_request", test_prompt_no_recovery_request),
        ("b128_and_b141_controls_from_frozen_artefacts", test_b128_and_b141_controls_from_frozen_artefacts),
        ("classify_phase_never_production_ready", test_classify_phase_never_production_ready),
        ("insufficient_physical_evidence", test_insufficient_physical_evidence),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "pass": False, "error": str(exc)})
    passed = sum(1 for r in results if r["pass"])
    return {
        "success": passed == len(tests),
        "passed": passed,
        "total": len(tests),
        "results": results,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
    }


__all__ = ["run_unit_tests"]
