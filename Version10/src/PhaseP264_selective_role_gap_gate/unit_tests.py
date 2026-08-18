"""Unit tests for P2.6.4. No live Claude in the default suite."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP261_stratified_vision_candidate_recovery.set_artefacts import (
    load_ownership,
    load_r13_index,
)
from PhaseP261_stratified_vision_candidate_recovery.unit_tests import (
    run_unit_tests as run_p261_unit_tests,
)
from PhaseP262_selective_vision_candidate_gate.unit_tests import (
    run_unit_tests as run_p262_unit_tests,
    test_incomplete_stirrup_call as p262_incomplete_stirrup,
    test_ocr_stirrup_call as p262_ocr_stirrup,
    test_stirrup_text_no_object_call as p262_stirrup_no_object,
)
from PhaseP263_longitudinal_aware_gate.unit_tests import (
    run_unit_tests as run_p263_unit_tests,
)

from .config import (
    COVER_FULL,
    COVER_LAYER,
    COVER_MISSING,
    COVER_NONE,
    COVER_QTY,
    COVER_ROLE,
    DECISION_CALL,
    DECISION_SKIP,
    GATE_VERSION,
    MAX_LIVE_CALLS,
    MODEL_VERSION,
    PRODUCTION_WRITE,
    ROLE_GAP_EXPLAINED,
    ROLE_GAP_REQUIRED,
)
from .frozen_sample import load_frozen_manifest
from .gate_decision import build_gate_decision
from .gate_rules import decide_gate
from .longitudinal_coverage import evaluate_longitudinal_coverage
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .replay_runner import apply_gate_to_frozen
from .role_gap import evaluate_selective_role_gap


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _ann(text: str, **extra: Any) -> Dict[str, Any]:
    row = {"text": text}
    row.update(extra)
    return row


def _model(*, top=None, bottom=None, stirrups=None, extra_top=None, extra_bottom=None) -> Dict[str, Any]:
    return {
        "top_main_bars": list(top or []),
        "top_extra_bars": list(extra_top or []),
        "bottom_main_bars": list(bottom or []),
        "bottom_extra_bars": list(extra_bottom or []),
        "stirrups": list(stirrups or []),
        "side_face_reinforcement": [],
        "spacer_bars": [],
        "total_classified_bars": len(top or []) + len(bottom or []) + len(stirrups or []),
    }


def _bar(role: str, dia: int, label: str, quantity: Optional[int] = None) -> Dict[str, Any]:
    qty = quantity
    if qty is None:
        try:
            qty = int(str(label).split("-")[0].split("Y")[0])
        except Exception:
            qty = 1
        if not qty:
            qty = 1
    return {
        "semantic_role": role,
        "diameter_mm": dia,
        "bar_label": label,
        "bar_id": f"R13-X-{role}-{label}",
        "quantity": qty,
    }


def _decide(rec: Dict[str, Any], model: Dict[str, Any], **kw: Any) -> Dict[str, Any]:
    return build_gate_decision(
        beam_id=kw.get("beam_id", "BX"),
        region_id=kw.get("region_id", "P264::Fifth::BX"),
        rec=rec,
        model=model,
        association=kw.get("association", "TARGET_BEAM"),
        set_key=kw.get("set_key", "Fifth"),
        source_set="Fifth Set Drawings",
    )


def _real(set_key: str, beam_id: str) -> Dict[str, Any]:
    v10 = _v10()
    rec = (load_ownership(v10, set_key).get("by_beam") or {}).get(beam_id) or {}
    model = load_r13_index(v10, set_key).get(beam_id)
    return _decide(rec, model or {}, beam_id=beam_id, set_key=set_key, region_id=f"P261::{set_key}::{beam_id}")


def test_same_role_dia_sufficient_qty_skip() -> None:
    rec = {"accepted_annotations": [_ann("3-Y20", semantic_role="BOTTOM")], "rejected_annotations": []}
    d = _decide(rec, _model(bottom=[_bar("BOTTOM_MAIN", 20, "3-Y20", 3)]))
    assert d["decision"] == DECISION_SKIP
    assert d["longitudinal_coverage"] == COVER_FULL


def test_same_role_dia_insufficient_qty_call() -> None:
    rec = {"accepted_annotations": [_ann("3-Y20", semantic_role="BOTTOM")], "rejected_annotations": []}
    d = _decide(rec, _model(bottom=[_bar("BOTTOM_MAIN", 20, "1-Y20", 1)]))
    assert d["decision"] == DECISION_CALL
    assert d["longitudinal_coverage"] == COVER_QTY


def test_same_dia_different_role_call() -> None:
    rec = {"accepted_annotations": [_ann("3-Y20", semantic_role="BOTTOM")], "rejected_annotations": []}
    d = _decide(rec, _model(top=[_bar("TOP_MAIN", 20, "3-Y20", 3)]))
    assert d["decision"] == DECISION_CALL
    assert d["longitudinal_coverage"] == COVER_ROLE


def test_multiple_callouts_insufficient_qty_call() -> None:
    rec = {
        "accepted_annotations": [_ann("3-Y20", semantic_role="TOP"), _ann("2-Y20", semantic_role="TOP")],
        "rejected_annotations": [],
    }
    d = _decide(rec, _model(top=[_bar("TOP_MAIN", 20, "3-Y20", 3)]))
    assert d["decision"] == DECISION_CALL


def test_multiple_callouts_adequately_represented_skip() -> None:
    rec = {
        "accepted_annotations": [_ann("3-Y20", semantic_role="TOP"), _ann("2-Y16", semantic_role="BOTTOM")],
        "rejected_annotations": [],
    }
    d = _decide(
        rec,
        _model(top=[_bar("TOP_MAIN", 20, "3-Y20", 3)], bottom=[_bar("BOTTOM_MAIN", 16, "2-Y16", 2)]),
    )
    assert d["decision"] == DECISION_SKIP


def test_conflicting_longitudinal_object_call() -> None:
    rec = {"accepted_annotations": [_ann("4-Y16", semantic_role="TOP")], "rejected_annotations": []}
    d = _decide(rec, _model(top=[_bar("TOP_MAIN", 20, "6-Y20", 6)]))
    assert d["decision"] == DECISION_CALL


def test_unknown_role_conservative() -> None:
    xor = _decide(
        {"accepted_annotations": [_ann("3-Y20")], "rejected_annotations": []},
        _model(top=[_bar("TOP_MAIN", 20, "3-Y20", 3)]),
    )
    assert xor["decision"] == DECISION_CALL
    assert xor["longitudinal_coverage"] == COVER_LAYER
    assert xor["role_gap_status"] == ROLE_GAP_REQUIRED
    both = _decide(
        {"accepted_annotations": [_ann("3-Y20")], "rejected_annotations": []},
        _model(top=[_bar("TOP_MAIN", 20, "3-Y20", 3)], bottom=[_bar("BOTTOM_MAIN", 25, "4-Y25", 4)]),
    )
    assert both["decision"] == DECISION_SKIP


def test_role_gap_explained_by_extras() -> None:
    rec = {"accepted_annotations": [_ann("3-Y20")], "rejected_annotations": []}
    d = _decide(
        rec,
        _model(
            top=[_bar("TOP_MAIN", 20, "3-Y20", 3)],
            extra_top=[_bar("TOP_EXTRA", 16, "3Y16#L", 3), _bar("TOP_EXTRA", 16, "3Y16#R", 3)],
        ),
    )
    assert d["longitudinal_coverage"] == COVER_LAYER
    assert d["role_gap_status"] == ROLE_GAP_EXPLAINED
    assert d["decision"] == DECISION_SKIP
    assert "ROLE_GAP_DETERMINISTICALLY_EXPLAINED" in d["reason_codes"]


def test_role_gap_repeated_accepted_requires_vision() -> None:
    rec = {"accepted_annotations": [_ann("3-Y16"), _ann("3-Y16")], "rejected_annotations": []}
    d = _decide(rec, _model(top=[_bar("TOP_MAIN", 16, "3-Y16", 3)]))
    assert d["decision"] == DECISION_CALL
    assert d["role_gap_status"] == ROLE_GAP_REQUIRED


def test_role_gap_rejected_match_explains() -> None:
    rec = {"accepted_annotations": [_ann("4-Y25")], "rejected_annotations": [_ann("4-Y25")]}
    d = _decide(rec, _model(top=[_bar("TOP_MAIN", 25, "4-Y25", 4)]))
    assert d["decision"] == DECISION_SKIP
    assert d["role_gap_status"] == ROLE_GAP_EXPLAINED


def test_role_gap_two_specs_requires_vision() -> None:
    rec = {"accepted_annotations": [_ann("3-Y20"), _ann("3-Y16")], "rejected_annotations": []}
    d = _decide(
        rec,
        _model(
            top=[_bar("TOP_MAIN", 20, "3-Y20", 3)],
            extra_top=[_bar("TOP_EXTRA", 16, "3Y16#L", 3)],
        ),
    )
    assert d["decision"] == DECISION_CALL
    assert d["role_gap_status"] == ROLE_GAP_REQUIRED


def test_true_recovery_b128_pattern_call() -> None:
    d = _real("Fifth", "B128")
    assert d["longitudinal_coverage"] == COVER_LAYER
    assert d["decision"] == DECISION_CALL
    assert d["role_gap_status"] == ROLE_GAP_REQUIRED


def test_true_recovery_b173_pattern_call() -> None:
    d = _real("Fifth", "B173")
    assert d["longitudinal_coverage"] == COVER_LAYER
    assert d["decision"] == DECISION_CALL
    assert d["role_gap_status"] == ROLE_GAP_REQUIRED


def test_b136_fully_covered_skip_unchanged() -> None:
    d = _real("Fifth", "B136")
    assert d["longitudinal_coverage"] == COVER_FULL
    assert d["decision"] == DECISION_SKIP


def test_quantity_shortfall_b41_b59_b77_call() -> None:
    for set_key, beam_id in (("Sixth", "B41"), ("Sixth", "B59"), ("Fifth", "B77")):
        d = _real(set_key, beam_id)
        assert d["decision"] == DECISION_CALL, (set_key, beam_id, d["decision"], d["longitudinal_coverage"])
        assert d["longitudinal_coverage"] == COVER_QTY


def test_no_deterministic_longitudinal_object_call() -> None:
    d = _decide({"accepted_annotations": [_ann("4-Y25")], "rejected_annotations": []}, _model())
    assert d["decision"] == DECISION_CALL
    assert d["longitudinal_coverage"] == COVER_MISSING


def test_stirrup_behavior_unchanged() -> None:
    rec = {"accepted_annotations": [_ann("4L-Y10@100C/C")], "rejected_annotations": []}
    d = _decide(rec, _model())
    assert d["decision"] == DECISION_CALL
    assert "STIRRUP_TEXT_NO_OBJECT" in d["reason_codes"]
    p262_stirrup_no_object()
    p262_ocr_stirrup()
    p262_incomplete_stirrup()


def test_stratum_not_used() -> None:
    feat = {
        "stirrup_text_no_object": True,
        "stirrup_text_present": True,
        "stirrup_object_present": False,
        "unmatched_stirrup_count": 1,
        "OCR_corruption_count": 0,
        "ocr_corrupted_stirrup_unmatched": 0,
        "incomplete_parse_count": 0,
        "unmatched_longitudinal_count": 0,
        "unassociated_strong_count": 0,
        "unassociated_annotation_count": 0,
        "association": "TARGET_BEAM",
        "matching_object_count": 0,
        "parse_complete": True,
        "deterministic_object_count": 0,
        "reinforcement_annotation_count": 1,
        "side_text_present": False,
        "side_object_present": False,
        "longitudinal_coverage": COVER_NONE,
        "role_gap_status": "ROLE_GAP_NOT_APPLICABLE",
    }
    a = decide_gate(feat)
    raised = False
    try:
        decide_gate({**feat, "stratum": "EASY"})
    except ValueError:
        raised = True
    assert raised
    assert a["decision"] == DECISION_CALL
    for name in ("role_gap.py", "gate_features.py", "longitudinal_coverage.py"):
        assert "stratum" not in (_pkg() / name).read_text(encoding="utf-8")


def test_gate_runtime_no_gt_tokens() -> None:
    for name in ("gate_features.py", "gate_rules.py", "gate_decision.py", "role_gap.py", "replay_runner.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "TRUE_RECOVERY" not in text
        assert "gt_match_status" not in text
        assert "load_gt_universe" not in text


def test_gate_runtime_no_estimator_tokens() -> None:
    for name in ("gate_features.py", "gate_rules.py", "gate_decision.py", "role_gap.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "EstimatorOutput" not in text
        assert "estimator_steel" not in text


def test_frozen_manifest_not_resampled() -> None:
    regions, summary = load_frozen_manifest(_v10())
    assert int(summary.get("seed") or 0) == 2611101
    assert len(regions) == 75


def test_no_live_vision_api() -> None:
    assert MAX_LIVE_CALLS == 0
    orch = (_pkg() / "phase_p264_orchestrator.py").read_text(encoding="utf-8")
    assert "observe_region" not in orch
    assert "anthropic" not in orch.lower()


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.4"
    assert GATE_VERSION == "P264_SELECTIVE_ROLE_GAP_GATE_V1_0"


def test_no_production_mutation() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True


def test_firewall_and_leakage() -> None:
    fw = firewall_check(_v10())
    assert fw["ok"], fw.get("offenders")
    leak = runtime_leakage_scan(_pkg())
    assert leak["ok"], leak.get("hits")


def test_p261_regression() -> None:
    nested = run_p261_unit_tests()
    assert nested.get("success"), nested


def test_p262_stirrup_regression() -> None:
    nested = run_p262_unit_tests()
    assert nested.get("success"), nested


def test_p263_regression() -> None:
    nested = run_p263_unit_tests()
    assert nested.get("success"), nested


def test_replay_skip_drops_candidates() -> None:
    decisions = [
        {"set_key": "Fifth", "beam_id": "B1", "decision": DECISION_CALL},
        {"set_key": "Fifth", "beam_id": "B2", "decision": DECISION_SKIP},
    ]
    frozen = [
        {"set_key": "Fifth", "beam_id": "B1", "candidate_id": "C1", "gt_match_status": "TRUE_RECOVERY"},
        {"set_key": "Fifth", "beam_id": "B2", "candidate_id": "C2", "gt_match_status": "DUPLICATE"},
    ]
    gated, summary = apply_gate_to_frozen(decisions=decisions, frozen_candidates=frozen)
    assert len(gated) == 1
    assert summary["suppressed_candidates"] == 1


def test_role_gap_evaluator_not_applicable_when_fully_covered() -> None:
    rec = {"accepted_annotations": [_ann("3-Y20", semantic_role="BOTTOM")]}
    cov = evaluate_longitudinal_coverage(
        rec=rec, model=_model(bottom=[_bar("BOTTOM_MAIN", 20, "3-Y20", 3)])
    )
    rg = evaluate_selective_role_gap(rec=rec, model=_model(bottom=[_bar("BOTTOM_MAIN", 20, "3-Y20", 3)]), coverage=cov)
    assert rg["role_gap_status"] == "ROLE_GAP_NOT_APPLICABLE"


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("same_role_dia_sufficient_qty_skip", test_same_role_dia_sufficient_qty_skip),
        ("same_role_dia_insufficient_qty_call", test_same_role_dia_insufficient_qty_call),
        ("same_dia_different_role_call", test_same_dia_different_role_call),
        ("multiple_callouts_insufficient_qty_call", test_multiple_callouts_insufficient_qty_call),
        ("multiple_callouts_adequately_represented_skip", test_multiple_callouts_adequately_represented_skip),
        ("conflicting_longitudinal_object_call", test_conflicting_longitudinal_object_call),
        ("unknown_role_conservative", test_unknown_role_conservative),
        ("role_gap_explained_by_extras", test_role_gap_explained_by_extras),
        ("role_gap_repeated_accepted_requires_vision", test_role_gap_repeated_accepted_requires_vision),
        ("role_gap_rejected_match_explains", test_role_gap_rejected_match_explains),
        ("role_gap_two_specs_requires_vision", test_role_gap_two_specs_requires_vision),
        ("true_recovery_b128_pattern_call", test_true_recovery_b128_pattern_call),
        ("true_recovery_b173_pattern_call", test_true_recovery_b173_pattern_call),
        ("b136_fully_covered_skip_unchanged", test_b136_fully_covered_skip_unchanged),
        ("quantity_shortfall_b41_b59_b77_call", test_quantity_shortfall_b41_b59_b77_call),
        ("no_deterministic_longitudinal_object_call", test_no_deterministic_longitudinal_object_call),
        ("stirrup_behavior_unchanged", test_stirrup_behavior_unchanged),
        ("stratum_not_used", test_stratum_not_used),
        ("gate_runtime_no_gt_tokens", test_gate_runtime_no_gt_tokens),
        ("gate_runtime_no_estimator_tokens", test_gate_runtime_no_estimator_tokens),
        ("frozen_manifest_not_resampled", test_frozen_manifest_not_resampled),
        ("no_live_vision_api", test_no_live_vision_api),
        ("production_write_false", test_production_write_false),
        ("no_production_mutation", test_no_production_mutation),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("P2.6.1_regression", test_p261_regression),
        ("P2.6.2_stirrup_regression", test_p262_stirrup_regression),
        ("P2.6.3_regression", test_p263_regression),
        ("replay_skip_drops_candidates", test_replay_skip_drops_candidates),
        ("role_gap_evaluator_not_applicable_when_fully_covered", test_role_gap_evaluator_not_applicable_when_fully_covered),
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
