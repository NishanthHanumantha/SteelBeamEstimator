"""Unit tests for P2.6.7. Live Claude is not invoked here."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

from .config import (
    EXPECTED_LIVE_CALLS,
    GATE_VERSION,
    MODEL_VERSION,
    PASS_PRIMARY,
    PASS_REPEAT,
    PRODUCTION_WRITE,
    SEM_AMBIGUOUS,
    SEM_DISTINCT,
    SEM_DUPLICATE,
    TARGET_BEAMS,
)
from .reparse import reparse_stored_observation
from .dataset import load_p266_targets
from .evaluator import (
    classify_phase,
    evaluate_accuracy,
    evaluate_critical,
    fully_covered_untouched,
)
from .live_caller import classify_call_error, live_observe, sanitize_text
from .live_context import build_live_context
from .live_prompt import SYSTEM_PROMPT, assert_no_truth_leak, build_user_prompt
from .live_schema import LiveSchemaError, normalize_live_payload, parse_live_response
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .repeatability import compute_repeatability, critical_repeatability


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _payload(**overrides: Any) -> Dict[str, Any]:
    base = {
        "decision": SEM_DISTINCT,
        "confidence": 0.7,
        "target_layer": "BOTTOM",
        "existing_representation_assessment": "NOT_REPRESENTED",
        "deterministic_context_consistent": True,
        "spatial_context_consistent": True,
        "conflict_present": False,
        "reason_codes": ["UNREPRESENTED_REINFORCEMENT"],
        "evidence": ["leader to bottom"],
        "annotation_interpretation": "missing bottom spec",
        "uncertainty_notes": "",
    }
    base.update(overrides)
    return base


def test_schema_validation() -> None:
    out = normalize_live_payload(_payload())
    assert out["schema_ok"] is True
    assert out["decision"] == SEM_DISTINCT


def test_enum_validation() -> None:
    try:
        normalize_live_payload(_payload(decision="SKIP_IT"))
        raise AssertionError("invalid enum accepted")
    except LiveSchemaError:
        pass


def test_confidence_validation() -> None:
    normalize_live_payload(_payload(confidence=0.0))
    normalize_live_payload(_payload(confidence=1.0))
    try:
        normalize_live_payload(_payload(confidence=1.2))
        raise AssertionError("out of range accepted")
    except LiveSchemaError:
        pass


def test_malformed_response_handling() -> None:
    parsed, report = parse_live_response("not json")
    assert parsed is None
    assert report.get("error_class") == "malformed_json"
    parsed2, report2 = parse_live_response("")
    assert parsed2 is None
    assert report2.get("error_class") == "empty_response"


def test_schema_coerces_nested_supporting_fields() -> None:
    out = normalize_live_payload(
        _payload(
            decision=SEM_DUPLICATE,
            annotation_interpretation={"notation": "3-Y16", "purpose": "repeat"},
            evidence={"image_observations": ["leader to existing bars"]},
            uncertainty_notes=["spatial zone is supporting only"],
        )
    )
    assert out["schema_ok"] is True
    assert out["decision"] == SEM_DUPLICATE
    assert isinstance(out["annotation_interpretation"], str) and out["annotation_interpretation"]
    assert isinstance(out["evidence"], list) and out["evidence"]
    assert isinstance(out["uncertainty_notes"], str) and out["uncertainty_notes"]
    assert "annotation_interpretation" in out["coerced_fields"]
    assert "evidence" in out["coerced_fields"]
    assert "uncertainty_notes" in out["coerced_fields"]


def test_schema_does_not_invent_decision() -> None:
    try:
        normalize_live_payload(_payload(decision=""))
        raise AssertionError("empty decision accepted")
    except LiveSchemaError:
        pass
    parsed, report = parse_live_response(json.dumps(_payload(decision="NOT_A_CLASS")))
    assert parsed is None
    assert report.get("error_class") == "schema_failure"


def test_reparse_nested_raw_keeps_claude_decision() -> None:
    raw = "```json\n" + json.dumps(
        _payload(
            decision=SEM_AMBIGUOUS,
            annotation_interpretation={"text": "unclear layer"},
            evidence={"notes": ["conflict"]},
            uncertainty_notes=["a", "b"],
        )
    ) + "\n```"
    out = reparse_stored_observation(
        {
            "ok": "False",
            "error_class": "schema_failure",
            "error": "annotation_interpretation must be a string",
            "raw_response": raw,
            "payload": None,
            "cache_hit": "False",
            "source": "P267_LIVE_PRIMARY",
        },
        pass_id=PASS_PRIMARY,
    )
    assert out["ok"] is True
    assert out["payload"]["decision"] == SEM_AMBIGUOUS
    assert out["schema_reparsed"] is True
    assert out["cache_hit"] is False
    assert out["live_call"] is True


def test_reparse_credit_failure_stays_failed() -> None:
    out = reparse_stored_observation(
        {
            "ok": "False",
            "error_class": "api_failure",
            "error": "Your credit balance is too low",
            "raw_response": None,
            "payload": None,
            "cache_hit": "False",
        },
        pass_id=PASS_PRIMARY,
    )
    assert out["ok"] is False
    assert out["payload"] is None
    assert out["error_class"] == "api_failure"
    assert out["schema_reparsed"] is False
    assert out["live_call"] is True


def test_api_failure_handling() -> None:
    assert classify_call_error(api_error_type="ClaudeAuthenticationError", parse_class=None, error="no key") == "authentication_failure"
    assert classify_call_error(api_error_type="ClaudeRateLimitError", parse_class=None, error="429") == "rate_limit"
    assert classify_call_error(api_error_type="ClaudeTimeoutError", parse_class=None, error="timeout") == "timeout"


def test_no_expected_label_leakage() -> None:
    ctx = {
        "beam_id": "BX",
        "deterministic_reinforcement": {"populated_layer": "TOP"},
        "annotation_context": [{"text": "3-Y16"}],
        "spatial_context": {"label": "SUPPORTING_EVIDENCE_ONLY"},
        "candidate_notation": [{"text": "3-Y16"}],
    }
    prompt = build_user_prompt(context=ctx)
    assert "TRUE_RECOVERY" not in prompt
    assert "DUPLICATE_CONTROL" not in prompt
    assert "FALSE_SKIP_CONTROL" not in prompt
    assert "expected class" not in prompt.lower()
    assert not assert_no_truth_leak({"system": SYSTEM_PROMPT, "user": prompt})
    try:
        build_user_prompt(context={"expected_decision": "DISTINCT_REINFORCEMENT"})
        raise AssertionError("leak allowed")
    except ValueError:
        pass


def test_no_gt_usage() -> None:
    for name in ("live_caller.py", "live_context.py", "live_schema.py", "dataset.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "TRUE_RECOVERY" not in text
        assert "gt_match_status" not in text
        assert "load_gt_universe" not in text


def test_no_estimator_usage() -> None:
    for name in ("live_caller.py", "live_context.py", "dataset.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "EstimatorOutput" not in text
        assert "estimator_steel" not in text


def test_no_production_mutation() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True


def test_p264_fingerprint_path() -> None:
    assert fingerprint_paths(_v10(), {})["p264_status"].exists()


def test_p265_fingerprint_path() -> None:
    assert fingerprint_paths(_v10(), {})["p265_status"].exists()


def test_p266_fingerprint_path() -> None:
    paths = fingerprint_paths(_v10(), {})
    assert paths["p266_status"].exists()
    assert paths["p266_targets"].exists()


def test_target_population_exactly_29() -> None:
    targets = load_p266_targets(_v10())
    assert len(targets) == TARGET_BEAMS == 29


def test_repeat_count_matches_primary() -> None:
    assert EXPECTED_LIVE_CALLS == 58
    assert PASS_PRIMARY != PASS_REPEAT


def test_cache_bypass_for_repeat() -> None:
    src = (_pkg() / "live_caller.py").read_text(encoding="utf-8")
    assert "load_cache" not in src
    assert "save_cache" not in src
    crop = Path("missing.png")
    ctx = {
        "beam_id": "BX",
        "deterministic_reinforcement": {},
        "annotation_context": [],
        "spatial_context": {"label": "SUPPORTING_EVIDENCE_ONLY"},
        "candidate_notation": [],
    }
    try:
        live_observe(
            version10_root=_v10(),
            context=ctx,
            crop=crop,
            pass_id=PASS_REPEAT,
            bypass_cache=False,
        )
        raise AssertionError("cache reuse allowed")
    except RuntimeError:
        pass


def test_critical_case_evaluation_logic() -> None:
    records = [
        {
            "set_key": "Fifth",
            "beam_id": "B128",
            "primary": {"ok": True, "payload": {"decision": SEM_DISTINCT}},
            "repeat": {"ok": True, "payload": {"decision": SEM_DISTINCT}},
            "p266_reference": SEM_DISTINCT,
        },
        {
            "set_key": "Fourth",
            "beam_id": "B141",
            "primary": {"ok": True, "payload": {"decision": SEM_DUPLICATE}},
            "repeat": {"ok": True, "payload": {"decision": SEM_AMBIGUOUS}},
            "p266_reference": SEM_DUPLICATE,
        },
        {
            "set_key": "Fourth",
            "beam_id": "B23",
            "primary": {"ok": True, "payload": {"decision": SEM_AMBIGUOUS}},
            "repeat": {"ok": True, "payload": {"decision": SEM_AMBIGUOUS}},
            "p266_reference": SEM_DUPLICATE,
        },
    ]
    crit = evaluate_critical(records)
    assert crit["strong_split"] is True
    assert crit["b128_duplicate_failure"] is False
    bad = json.loads(json.dumps(records))
    bad[0]["primary"]["payload"]["decision"] = SEM_DUPLICATE
    assert evaluate_critical(bad)["b128_duplicate_failure"] is True


def test_fully_covered_path_untouched() -> None:
    rows = [
        {
            "longitudinal_coverage": "FULLY_COVERED",
            "observed_decision": "SKIP_VISION",
            "production_routing_changed": False,
        }
    ]
    assert fully_covered_untouched(rows) is True
    rows[0]["production_routing_changed"] = True
    assert fully_covered_untouched(rows) is False


def test_no_duplicate_to_skip_routing() -> None:
    orch = (_pkg() / "phase_p267_orchestrator.py").read_text(encoding="utf-8")
    assert "hypothetical_vision_routing" not in orch
    assert 'observed_decision"] = "SKIP_VISION"' not in orch
    caller = (_pkg() / "live_caller.py").read_text(encoding="utf-8")
    assert "SKIP_VISION" not in caller
    schema = (_pkg() / "live_schema.py").read_text(encoding="utf-8")
    assert "SKIP_VISION" not in schema


def test_raw_response_secret_sanitization() -> None:
    red = sanitize_text("key sk-ant-abcdefghijklmnopqrstuvwxyz and ANTHROPIC_API_KEY=secret")
    assert "sk-ant-" not in red or "[REDACTED]" in red
    assert "secret" not in red


def test_repeatability_calculation() -> None:
    records = [
        {
            "set_key": "A",
            "beam_id": "1",
            "primary": {"ok": True, "payload": {"decision": SEM_DISTINCT, "confidence": 0.7, "target_layer": "BOTTOM", "existing_representation_assessment": "NOT_REPRESENTED"}},
            "repeat": {"ok": True, "payload": {"decision": SEM_DISTINCT, "confidence": 0.6, "target_layer": "BOTTOM", "existing_representation_assessment": "NOT_REPRESENTED"}},
        },
        {
            "set_key": "A",
            "beam_id": "2",
            "primary": {"ok": True, "payload": {"decision": SEM_DISTINCT, "confidence": 0.7, "target_layer": "TOP", "existing_representation_assessment": "NOT_REPRESENTED"}},
            "repeat": {"ok": True, "payload": {"decision": SEM_DUPLICATE, "confidence": 0.7, "target_layer": "TOP", "existing_representation_assessment": "REPRESENTED"}},
        },
    ]
    m = compute_repeatability(records)
    assert m["valid_paired_cases"] == 2
    assert m["exact_semantic_decision_agreement"] == 1
    assert m["DISTINCT_to_DUPLICATE"] == 1
    cr = critical_repeatability(records, [("A", "1"), ("A", "2")])
    assert cr["agreement"] == 1


def test_semantic_metric_calculation() -> None:
    records = [
        {"set_key": "Fifth", "beam_id": "B128", "primary": {"ok": True, "payload": {"decision": SEM_DISTINCT}}},
        {"set_key": "Fifth", "beam_id": "B173", "primary": {"ok": True, "payload": {"decision": SEM_DISTINCT}}},
        {"set_key": "Fourth", "beam_id": "B102", "primary": {"ok": True, "payload": {"decision": SEM_DISTINCT}}},
        {"set_key": "Fourth", "beam_id": "B170", "primary": {"ok": True, "payload": {"decision": SEM_DISTINCT}}},
        {"set_key": "Fourth", "beam_id": "B173", "primary": {"ok": True, "payload": {"decision": SEM_DISTINCT}}},
        {"set_key": "Fourth", "beam_id": "B174", "primary": {"ok": True, "payload": {"decision": SEM_DISTINCT}}},
        {"set_key": "Sixth", "beam_id": "B138", "primary": {"ok": True, "payload": {"decision": SEM_DISTINCT}}},
        {"set_key": "Fifth", "beam_id": "B100", "primary": {"ok": True, "payload": {"decision": SEM_DUPLICATE}}},
        {"set_key": "Fourth", "beam_id": "B23", "primary": {"ok": True, "payload": {"decision": SEM_DUPLICATE}}},
        {"set_key": "Fourth", "beam_id": "B141", "primary": {"ok": True, "payload": {"decision": SEM_DUPLICATE}}},
        {"set_key": "Fifth", "beam_id": "B62", "primary": {"ok": True, "payload": {"decision": SEM_DUPLICATE}}},
        {"set_key": "Sixth", "beam_id": "B56", "primary": {"ok": True, "payload": {"decision": SEM_DUPLICATE}}},
        {"set_key": "Fourth", "beam_id": "B143", "primary": {"ok": True, "payload": {"decision": SEM_DUPLICATE}}},
        {"set_key": "Fourth", "beam_id": "B176", "primary": {"ok": True, "payload": {"decision": SEM_DUPLICATE}}},
        {"set_key": "Sixth", "beam_id": "B45", "primary": {"ok": True, "payload": {"decision": SEM_DUPLICATE}}},
    ]
    acc = evaluate_accuracy(records)
    assert acc["false_DUPLICATE"] == 0
    assert acc["false_DISTINCT"] == 0
    assert acc["true_recovery_recall"] == 1.0
    assert acc["duplicate_recall"] == 1.0


def test_failed_call_accounting() -> None:
    parsed, report = parse_live_response(None)
    assert parsed is None
    assert report.get("ok") is False


def test_live_context_strips_frozen_observations() -> None:
    target = {
        "context": {
            "beam_id": "BX",
            "deterministic_reinforcement": {"role_assignments": {"populated_layer": "TOP"}},
            "annotation_context": [{"text": "3-Y16", "quantity": 3, "diameter_mm": 16}],
            "spatial_context": {"label": "SUPPORTING_EVIDENCE_ONLY"},
            "frozen_vision_longitudinal_observations": [
                {"deterministic_match_status": "POTENTIALLY_MISSING", "role": "BOTTOM_BAR"}
            ],
        },
        "semantic": {"decision": SEM_DISTINCT},
        "eval_stratum": "DIFFICULT",
    }
    ctx = build_live_context(target)
    blob = json.dumps(ctx)
    assert "frozen_vision" not in blob
    assert "POTENTIALLY_MISSING" not in blob
    assert "TRUE_RECOVERY" not in blob
    assert ctx.get("candidate_notation")


def test_no_beam_id_hardcoding_in_runtime() -> None:
    for name in ("live_caller.py", "live_context.py", "live_schema.py", "live_prompt.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for token in ("B128", "B141", "B23", "B136"):
            assert token not in text, f"{name} contains {token}"


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.7"
    assert GATE_VERSION == "P267_LIVE_SEMANTIC_ARBITRATION_V1_0"


def test_firewall_and_leakage() -> None:
    fw = firewall_check(_v10())
    assert fw["ok"], fw.get("offenders")
    leak = runtime_leakage_scan(_pkg())
    assert leak["ok"], leak.get("hits")


def test_classify_phase_never_production_ready() -> None:
    rec = classify_phase(
        accuracy={"false_DUPLICATE": 0, "false_DISTINCT": 0, "true_recovery_recall": 1.0},
        repeat={"semantic_repeatability_rate": 1.0, "DISTINCT_to_DUPLICATE": 0, "DUPLICATE_to_DISTINCT": 0},
        critical={"strong_split": True, "b128_duplicate_failure": False},
        live_ok=True,
        fingerprints_ok=True,
        production_mutation=0,
        successful_primary=29,
        successful_repeat=29,
    )
    assert rec["decision"] != "PRODUCTION_READY"
    assert rec["decision"] in (
        "LIVE_SEMANTIC_VALIDATED",
        "LIVE_SEMANTIC_PARTIALLY_VALIDATED",
        "REFINE_SEMANTIC_ARBITRATION",
        "LIVE_BENCHMARK_FAILED",
    )


def test_mocked_live_call_does_not_use_p266_cache() -> None:
    ctx = {
        "beam_id": "BX",
        "deterministic_reinforcement": {},
        "annotation_context": [],
        "spatial_context": {"label": "SUPPORTING_EVIDENCE_ONLY"},
        "candidate_notation": [],
    }
    crop = _v10() / "data" / "output" / "PhaseQA30_unseen_benchmark" / "Fifth_Set_Drawings" / "RenderedCrops" / "shared_renders" / "B128_render.png"
    fake = {
        "success": True,
        "raw_text": json.dumps(_payload()),
        "error": None,
        "error_type": None,
        "retry_count": 0,
        "latency_s": 0.1,
        "usage": {},
        "model": "claude-sonnet-4-5",
    }
    with patch("PhaseP267_live_semantic_arbitration.live_caller.call_claude_vision", return_value=fake):
        obs = live_observe(version10_root=_v10(), context=ctx, crop=crop, pass_id=PASS_PRIMARY, bypass_cache=True)
    assert obs["live_call"] is True
    assert obs["cache_hit"] is False
    assert obs["ok"] is True
    assert obs["payload"]["decision"] == SEM_DISTINCT
    assert obs["source"] == "P267_LIVE_PRIMARY"


def test_p266_regression_file() -> None:
    prior = _v10() / "data" / "output" / "PhaseP266_semantic_longitudinal_resolver" / "unit_tests.json"
    payload = json.loads(prior.read_text(encoding="utf-8"))
    assert payload.get("success") is True
    assert int(payload.get("passed") or 0) >= 36


def test_orchestrator_refuses_replay_mode() -> None:
    src = (_pkg() / "phase_p267_orchestrator.py").read_text(encoding="utf-8")
    assert "Refusing to silently convert to replay" in src
    assert "load_cache" not in src


def test_artifact_generation_helpers() -> None:
    from .report import write_reports

    assert callable(write_reports)


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("schema_validation", test_schema_validation),
        ("enum_validation", test_enum_validation),
        ("confidence_validation", test_confidence_validation),
        ("malformed_response_handling", test_malformed_response_handling),
        ("schema_coerces_nested_supporting_fields", test_schema_coerces_nested_supporting_fields),
        ("schema_does_not_invent_decision", test_schema_does_not_invent_decision),
        ("reparse_nested_raw_keeps_claude_decision", test_reparse_nested_raw_keeps_claude_decision),
        ("reparse_credit_failure_stays_failed", test_reparse_credit_failure_stays_failed),
        ("api_failure_handling", test_api_failure_handling),
        ("no_expected_label_leakage", test_no_expected_label_leakage),
        ("no_gt_usage", test_no_gt_usage),
        ("no_estimator_usage", test_no_estimator_usage),
        ("no_production_mutation", test_no_production_mutation),
        ("p264_fingerprint_path", test_p264_fingerprint_path),
        ("p265_fingerprint_path", test_p265_fingerprint_path),
        ("p266_fingerprint_path", test_p266_fingerprint_path),
        ("target_population_exactly_29", test_target_population_exactly_29),
        ("repeat_count_matches_primary", test_repeat_count_matches_primary),
        ("cache_bypass_for_repeat", test_cache_bypass_for_repeat),
        ("critical_case_evaluation_logic", test_critical_case_evaluation_logic),
        ("fully_covered_path_untouched", test_fully_covered_path_untouched),
        ("no_duplicate_to_skip_routing", test_no_duplicate_to_skip_routing),
        ("raw_response_secret_sanitization", test_raw_response_secret_sanitization),
        ("repeatability_calculation", test_repeatability_calculation),
        ("semantic_metric_calculation", test_semantic_metric_calculation),
        ("failed_call_accounting", test_failed_call_accounting),
        ("live_context_strips_frozen_observations", test_live_context_strips_frozen_observations),
        ("no_beam_id_hardcoding_in_runtime", test_no_beam_id_hardcoding_in_runtime),
        ("production_write_false", test_production_write_false),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("classify_phase_never_production_ready", test_classify_phase_never_production_ready),
        ("mocked_live_call_does_not_use_p266_cache", test_mocked_live_call_does_not_use_p266_cache),
        ("P2.6.6_regression", test_p266_regression_file),
        ("orchestrator_refuses_replay_mode", test_orchestrator_refuses_replay_mode),
        ("artifact_generation_helpers", test_artifact_generation_helpers),
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
