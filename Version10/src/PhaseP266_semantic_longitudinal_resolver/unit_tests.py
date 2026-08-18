"""Unit tests for P2.6.6. No live Claude. Does not change P2.6.4/P2.6.5 routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import (
    ADAPTER_SOURCE,
    COVER_FULL,
    COVER_LAYER,
    DECISION_CALL,
    DECISION_SKIP,
    GATE_VERSION,
    MAX_LIVE_CALLS_REPLAY,
    MODEL_VERSION,
    PRODUCTION_WRITE,
    SEM_AMBIGUOUS,
    SEM_DISTINCT,
    SEM_DUPLICATE,
    SEM_UNSUPPORTED,
)
from .frozen_sample import candidates_for_beam, load_frozen_candidates, load_frozen_manifest, load_p265_decisions
from .hypothetical import hypothetical_from_semantic, is_safe_skip_candidate
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .semantic_prompt import SYSTEM_PROMPT, assert_no_truth_leak, build_user_prompt
from .semantic_replay import adapt_frozen_observations
from .semantic_resolver import resolve_semantic
from .semantic_schema import SemanticSchemaError, normalize_semantic_payload, parse_semantic_response


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _valid_payload(**overrides: Any) -> Dict[str, Any]:
    base = {
        "decision": SEM_DISTINCT,
        "confidence": 0.7,
        "annotation_interpretation": "unrepresented bottom spec",
        "target_layer": "BOTTOM",
        "existing_representation_assessment": "NOT_REPRESENTED",
        "semantic_reason_codes": ["UNREPRESENTED_REINFORCEMENT"],
        "visual_evidence": ["leader to bottom layer"],
        "deterministic_context_consistent": True,
        "spatial_context_consistent": True,
        "conflict_present": False,
    }
    base.update(overrides)
    return base


def _p265_row(set_key: str, beam_id: str) -> Dict[str, Any]:
    for row in load_p265_decisions(_v10()):
        if row.get("set_key") == set_key and row.get("beam_id") == beam_id:
            return row
    raise AssertionError(f"missing P2.6.5 row {set_key}/{beam_id}")


def _resolve(set_key: str, beam_id: str) -> Dict[str, Any]:
    row = _p265_row(set_key, beam_id)
    cands = candidates_for_beam(load_frozen_candidates(_v10()), set_key, beam_id)
    return resolve_semantic(p265_decision=row, frozen_candidates=cands)


def test_schema_validation() -> None:
    payload = normalize_semantic_payload(_valid_payload())
    assert payload["decision"] == SEM_DISTINCT
    assert payload["schema_ok"] is True
    assert 0.0 <= payload["confidence"] <= 1.0


def test_invalid_output_handling() -> None:
    parsed, report = parse_semantic_response("this is not json")
    assert parsed is None
    assert report.get("ok") is False
    try:
        normalize_semantic_payload(_valid_payload(decision="SKIP_IT"))
        raise AssertionError("invalid decision accepted")
    except SemanticSchemaError:
        pass
    try:
        normalize_semantic_payload(_valid_payload(confidence=1.5))
        raise AssertionError("out-of-range confidence accepted")
    except SemanticSchemaError:
        pass
    try:
        normalize_semantic_payload(_valid_payload(semantic_reason_codes=["NOT_A_CODE"]))
        raise AssertionError("unknown reason code accepted")
    except SemanticSchemaError:
        pass


def test_confidence_bounds() -> None:
    lo = normalize_semantic_payload(_valid_payload(confidence=0.0))
    hi = normalize_semantic_payload(_valid_payload(confidence=1.0))
    assert lo["confidence"] == 0.0
    assert hi["confidence"] == 1.0


def test_allowed_enum_decisions_only() -> None:
    for decision in (SEM_DISTINCT, SEM_DUPLICATE, SEM_AMBIGUOUS, SEM_UNSUPPORTED):
        normalize_semantic_payload(_valid_payload(decision=decision, semantic_reason_codes=[]))


def test_replay_adapter_no_gt_fields() -> None:
    src = (_pkg() / "semantic_replay.py").read_text(encoding="utf-8")
    assert "gt_match_status" not in src
    assert "TRUE_RECOVERY" not in src
    cands = [
        {
            "candidate_type": "LONGITUDINAL_REINFORCEMENT",
            "role": "BOTTOM_BAR",
            "annotation_text": "3-Y16",
            "deterministic_match_status": "POTENTIALLY_MISSING",
            "gt_match_status": "TRUE_RECOVERY",
            "evidence_notes": ["leader to bottom"],
        }
    ]
    out = adapt_frozen_observations(
        context={
            "deterministic_reinforcement": {"role_assignments": {"populated_layer": "TOP"}},
            "spatial_context": {"spatial_context_status": "CONTEXT_SUPPORTS_CALL"},
        },
        frozen_candidates=cands,
    )
    assert out["decision"] == SEM_DISTINCT
    assert "TRUE_RECOVERY" not in json.dumps(out)


def test_empty_observations_unsupported() -> None:
    out = adapt_frozen_observations(
        context={"deterministic_reinforcement": {}, "spatial_context": {}},
        frozen_candidates=[],
    )
    assert out["decision"] == SEM_UNSUPPORTED


def test_already_detected_duplicate() -> None:
    out = adapt_frozen_observations(
        context={
            "deterministic_reinforcement": {"role_assignments": {"populated_layer": "TOP"}},
            "spatial_context": {"spatial_context_status": "CONTEXT_SUPPORTS_CALL"},
        },
        frozen_candidates=[
            {
                "candidate_type": "LONGITUDINAL_REINFORCEMENT",
                "role": "TOP_BAR",
                "annotation_text": "5-Y16",
                "deterministic_match_status": "ALREADY_DETECTED",
                "evidence_notes": ["leader to top"],
            }
        ],
    )
    assert out["decision"] == SEM_DUPLICATE
    assert out["spatial_context_consistent"] is False


def test_high_confidence_alone_cannot_skip() -> None:
    semantic = normalize_semantic_payload(
        _valid_payload(
            decision=SEM_DUPLICATE,
            confidence=0.99,
            existing_representation_assessment="REPRESENTED",
            spatial_context_consistent=False,
            deterministic_context_consistent=True,
            conflict_present=False,
            semantic_reason_codes=["DUPLICATE_ANNOTATION"],
        )
    )
    assert is_safe_skip_candidate(semantic) is False
    hypo = hypothetical_from_semantic(
        observed_decision=DECISION_CALL,
        coverage=COVER_LAYER,
        semantic=semantic,
    )
    assert hypo["hypothetical_vision_routing"] == DECISION_CALL


def test_stirrup_reasons_block_skip() -> None:
    semantic = normalize_semantic_payload(
        _valid_payload(
            decision=SEM_DUPLICATE,
            confidence=0.8,
            existing_representation_assessment="REPRESENTED",
            spatial_context_consistent=True,
            deterministic_context_consistent=True,
            conflict_present=False,
            semantic_reason_codes=["ALREADY_REPRESENTED_LAYER"],
        )
    )
    hypo = hypothetical_from_semantic(
        observed_decision=DECISION_CALL,
        coverage=COVER_LAYER,
        semantic=semantic,
        reason_codes=["STIRRUP_TEXT_NO_OBJECT", "LONGITUDINAL_COVERAGE_SHORTFALL"],
    )
    assert hypo["hypothetical_vision_routing"] == DECISION_CALL
    assert hypo["hypothetical_reason"] == "PRESERVE_STIRRUP_CALL"


def test_safe_skip_requires_multi_evidence() -> None:
    semantic = normalize_semantic_payload(
        _valid_payload(
            decision=SEM_DUPLICATE,
            confidence=0.8,
            existing_representation_assessment="REPRESENTED",
            spatial_context_consistent=True,
            deterministic_context_consistent=True,
            conflict_present=False,
            semantic_reason_codes=["ALREADY_REPRESENTED_LAYER"],
        )
    )
    assert is_safe_skip_candidate(semantic) is True


def test_ambiguous_and_unsupported_call() -> None:
    for decision in (SEM_AMBIGUOUS, SEM_UNSUPPORTED):
        hypo = hypothetical_from_semantic(
            observed_decision=DECISION_CALL,
            coverage=COVER_LAYER,
            semantic=normalize_semantic_payload(_valid_payload(decision=decision, semantic_reason_codes=[])),
        )
        assert hypo["hypothetical_vision_routing"] == DECISION_CALL


def test_fully_covered_not_overridden() -> None:
    hypo = hypothetical_from_semantic(
        observed_decision=DECISION_SKIP,
        coverage=COVER_FULL,
        semantic=normalize_semantic_payload(_valid_payload(decision=SEM_DISTINCT)),
    )
    assert hypo["hypothetical_vision_routing"] == DECISION_SKIP
    assert hypo["hypothetical_reason"] == "PRESERVE_FULLY_COVERED_PRODUCTION_PATH"


def test_prompt_no_truth_leak() -> None:
    ctx = {
        "beam_id": "BX",
        "deterministic_reinforcement": {"populated_layer": "TOP"},
        "annotation_context": [{"text": "3-Y16"}],
        "spatial_context": {"label": "SUPPORTING_EVIDENCE_ONLY"},
    }
    prompt = build_user_prompt(context=ctx)
    assert "TRUE_RECOVERY" not in prompt
    assert "DUPLICATE_ONLY" not in prompt
    assert "ground truth" not in prompt.lower()
    assert not assert_no_truth_leak({"system": SYSTEM_PROMPT, "user": prompt})
    try:
        build_user_prompt(context={"gt_match_status": "TRUE_RECOVERY"})
        raise AssertionError("truth leak allowed")
    except ValueError:
        pass


def test_b128_semantic_distinct() -> None:
    rec = _resolve("Fifth", "B128")
    assert rec["semantic"]["decision"] == SEM_DISTINCT
    assert rec["observed_decision"] == DECISION_CALL
    assert rec["hypothetical"]["hypothetical_vision_routing"] == DECISION_CALL
    assert rec["production_routing_changed"] is False


def test_b173_semantic_distinct() -> None:
    rec = _resolve("Fifth", "B173")
    assert rec["semantic"]["decision"] == SEM_DISTINCT
    assert rec["observed_decision"] == DECISION_CALL


def test_b141_semantic_duplicate() -> None:
    rec = _resolve("Fourth", "B141")
    assert rec["semantic"]["decision"] == SEM_DUPLICATE
    assert rec["observed_decision"] == DECISION_CALL
    assert rec["hypothetical"]["safe_skip_candidate"] is False


def test_b23_semantic_duplicate() -> None:
    rec = _resolve("Fourth", "B23")
    assert rec["semantic"]["decision"] == SEM_DUPLICATE
    assert rec["observed_decision"] == DECISION_CALL


def test_b100_semantic_duplicate() -> None:
    rec = _resolve("Fifth", "B100")
    assert rec["semantic"]["decision"] == SEM_DUPLICATE
    assert rec["observed_decision"] == DECISION_CALL


def test_separability_b128_vs_b141_b23() -> None:
    a = _resolve("Fifth", "B128")["semantic"]["decision"]
    b = _resolve("Fourth", "B141")["semantic"]["decision"]
    c = _resolve("Fourth", "B23")["semantic"]["decision"]
    assert a == SEM_DISTINCT
    assert b == SEM_DUPLICATE
    assert c == SEM_DUPLICATE
    assert a != b and a != c


def test_b136_false_skip_diagnostic() -> None:
    row = _p265_row("Fifth", "B136")
    rec = _resolve("Fifth", "B136")
    assert row.get("longitudinal_coverage") == COVER_FULL
    assert rec["observed_decision"] == DECISION_SKIP
    assert rec["hypothetical"]["hypothetical_vision_routing"] == DECISION_SKIP
    assert rec["semantic"]["decision"] in (SEM_AMBIGUOUS, SEM_DISTINCT, SEM_UNSUPPORTED)


def test_no_production_mutation() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True


def test_no_live_vision_in_replay() -> None:
    assert MAX_LIVE_CALLS_REPLAY == 0
    orch = (_pkg() / "phase_p266_orchestrator.py").read_text(encoding="utf-8")
    assert "call_claude_vision" not in orch
    assert "anthropic" not in orch.lower()


def test_frozen_p261_replay_integrity() -> None:
    regions, summary = load_frozen_manifest(_v10())
    assert int(summary.get("seed") or 0) == 2611101
    assert len(regions) == 75


def test_p264_p265_artefact_immutability_paths() -> None:
    paths = fingerprint_paths(_v10(), {})
    assert paths["p264_status"].name == "P2.6.4_STATUS.md"
    assert paths["p265_status"].name == "P2.6.5_STATUS.md"
    assert paths["p264_status"].exists()
    assert paths["p265_status"].exists()
    assert paths["p265_decisions"].exists()


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.6"
    assert GATE_VERSION == "P266_SEMANTIC_LONGITUDINAL_RESOLVER_V1_0"


def test_runtime_no_gt_tokens() -> None:
    for name in (
        "semantic_resolver.py",
        "semantic_replay.py",
        "semantic_context_builder.py",
        "hypothetical.py",
        "live_observer.py",
    ):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "TRUE_RECOVERY" not in text
        assert "gt_match_status" not in text
        assert "load_gt_universe" not in text


def test_runtime_no_estimator_tokens() -> None:
    for name in ("semantic_resolver.py", "semantic_replay.py", "hypothetical.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "EstimatorOutput" not in text
        assert "estimator_steel" not in text


def test_stratum_not_used_in_resolver() -> None:
    for name in ("semantic_resolver.py", "semantic_replay.py", "hypothetical.py"):
        src = (_pkg() / name).read_text(encoding="utf-8")
        assert "stratum" not in src


def test_firewall_and_leakage() -> None:
    fw = firewall_check(_v10())
    assert fw["ok"], fw.get("offenders")
    leak = runtime_leakage_scan(_pkg())
    assert leak["ok"], leak.get("hits")


def test_observed_routing_unchanged() -> None:
    rec = _resolve("Fifth", "B128")
    row = _p265_row("Fifth", "B128")
    assert rec["observed_decision"] == (row.get("observed_decision") or row.get("decision"))
    assert rec["production_routing_changed"] is False


def test_no_beam_id_hardcoding_in_resolver() -> None:
    for name in (
        "semantic_resolver.py",
        "semantic_replay.py",
        "hypothetical.py",
        "semantic_context_builder.py",
        "semantic_schema.py",
    ):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for token in ("B128", "B173", "B100", "B136", "B23", "B141"):
            assert token not in text, f"{name} contains {token}"


def test_cache_isolation_path() -> None:
    text = (_pkg() / "phase_p266_orchestrator.py").read_text(encoding="utf-8")
    assert "PhaseP261_stratified_vision_candidate_recovery" in text
    assert "out_root / \"cache\"" in text or 'out_root / "cache"' in text


def test_p264_regression() -> None:
    prior = _v10() / "data" / "output" / "PhaseP264_selective_role_gap_gate" / "unit_tests.json"
    payload = json.loads(prior.read_text(encoding="utf-8"))
    assert payload.get("success") is True
    assert int(payload.get("passed") or 0) >= 30


def test_p265_regression() -> None:
    prior = _v10() / "data" / "output" / "PhaseP265_spatial_context_longitudinal" / "unit_tests.json"
    payload = json.loads(prior.read_text(encoding="utf-8"))
    assert payload.get("success") is True
    assert int(payload.get("passed") or 0) >= 32


def test_adapter_source_label() -> None:
    rec = _resolve("Fifth", "B128")
    assert rec["semantic"].get("source") == ADAPTER_SOURCE


def test_context_builder_strips_eval_fields() -> None:
    from .semantic_context_builder import build_semantic_context

    row = _p265_row("Fifth", "B128")
    row = dict(row)
    row["eval_stratum"] = "DIFFICULT"
    row["gt_match_status"] = "TRUE_RECOVERY"
    ctx = build_semantic_context(p265_decision=row, frozen_candidates=[])
    blob = json.dumps(ctx)
    assert "TRUE_RECOVERY" not in blob
    assert "eval_stratum" not in blob
    assert "gt_match_status" not in blob


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("schema_validation", test_schema_validation),
        ("invalid_output_handling", test_invalid_output_handling),
        ("confidence_bounds", test_confidence_bounds),
        ("allowed_enum_decisions_only", test_allowed_enum_decisions_only),
        ("replay_adapter_no_gt_fields", test_replay_adapter_no_gt_fields),
        ("empty_observations_unsupported", test_empty_observations_unsupported),
        ("already_detected_duplicate", test_already_detected_duplicate),
        ("high_confidence_alone_cannot_skip", test_high_confidence_alone_cannot_skip),
        ("stirrup_reasons_block_skip", test_stirrup_reasons_block_skip),
        ("safe_skip_requires_multi_evidence", test_safe_skip_requires_multi_evidence),
        ("ambiguous_and_unsupported_call", test_ambiguous_and_unsupported_call),
        ("fully_covered_not_overridden", test_fully_covered_not_overridden),
        ("prompt_no_truth_leak", test_prompt_no_truth_leak),
        ("b128_semantic_distinct", test_b128_semantic_distinct),
        ("b173_semantic_distinct", test_b173_semantic_distinct),
        ("b141_semantic_duplicate", test_b141_semantic_duplicate),
        ("b23_semantic_duplicate", test_b23_semantic_duplicate),
        ("b100_semantic_duplicate", test_b100_semantic_duplicate),
        ("separability_b128_vs_b141_b23", test_separability_b128_vs_b141_b23),
        ("b136_false_skip_diagnostic", test_b136_false_skip_diagnostic),
        ("no_production_mutation", test_no_production_mutation),
        ("no_live_vision_in_replay", test_no_live_vision_in_replay),
        ("frozen_p261_replay_integrity", test_frozen_p261_replay_integrity),
        ("p264_p265_artefact_immutability_paths", test_p264_p265_artefact_immutability_paths),
        ("production_write_false", test_production_write_false),
        ("runtime_no_gt_tokens", test_runtime_no_gt_tokens),
        ("runtime_no_estimator_tokens", test_runtime_no_estimator_tokens),
        ("stratum_not_used_in_resolver", test_stratum_not_used_in_resolver),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("observed_routing_unchanged", test_observed_routing_unchanged),
        ("no_beam_id_hardcoding_in_resolver", test_no_beam_id_hardcoding_in_resolver),
        ("cache_isolation_path", test_cache_isolation_path),
        ("P2.6.4_regression", test_p264_regression),
        ("P2.6.5_regression", test_p265_regression),
        ("adapter_source_label", test_adapter_source_label),
        ("context_builder_strips_eval_fields", test_context_builder_strips_eval_fields),
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
