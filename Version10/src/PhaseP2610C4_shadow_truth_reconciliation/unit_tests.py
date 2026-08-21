"""Unit tests for P2.6.10-C.4. No Claude. No DXF. No production mutation."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .anti_hardcoding import fixture_rename_invariance, run_anti_hardcoding, source_guard
from .config import (
    GATE_VERSION,
    LIVE_CLAUDE_CALL,
    MODEL_VERSION,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    SHADOW_ONLY,
    STATUS_AMBIGUOUS,
    STATUS_DET_CONFIRMED,
    STATUS_EQUIVALENT,
    STATUS_INSUFFICIENT,
    STATUS_VIS_CONFIRMED,
)
from .discovery import control_beam_ids, load_six_beam_control
from .engine import reconcile_groups
from .metrics import aggregate_metrics
from .normalize import keys_of, match_against, normalize_spec, physical_identity
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    prior_artefacts_intact,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def test_six_beam_control_discovery() -> None:
    control = load_six_beam_control(_v10())
    assert control.get("ok") is True, control
    ids = control_beam_ids(control)
    assert len(ids) == 6
    assert len(set(ids)) == 6


def test_missing_evidence_fail_closed() -> None:
    rec = reconcile_groups(vision_groups=[], deterministic_groups=[], p269_groups=[])
    assert rec["reconciliation_status"] == STATUS_INSUFFICIENT
    assert rec["truth_established"] is False
    assert rec["vision_result"] == "UNRESOLVED"
    assert rec["deterministic_result"] == "UNRESOLVED"


def test_contradictory_independent_ambiguous() -> None:
    rec = reconcile_groups(
        vision_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y20"}],
        deterministic_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y16"}],
        independent_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y20"}],
        independent_conflict=True,
    )
    assert rec["reconciliation_status"] == STATUS_AMBIGUOUS
    assert rec["truth_established"] is False


def test_explicit_verification_vision_confirmed() -> None:
    rec = reconcile_groups(
        vision_groups=[
            {"layer": "TOP", "role": "MAIN", "specification": "5-Y20"},
            {"layer": "BOTTOM", "role": "MAIN", "specification": "5-Y16"},
            {"layer": "STIRRUP", "role": "STIRRUP", "specification": "4L-Y8@100C/C"},
        ],
        deterministic_groups=[
            {"layer": "TOP", "role": "MAIN", "specification": "5Y16"},
            {"layer": "STIRRUP", "role": "STIRRUP", "specification": "4L-Y8@\\X100C/C"},
        ],
        independent_groups=[
            {"layer": "TOP", "role": "MAIN", "specification": "5-Y20"},
            {"layer": "BOTTOM", "role": "MAIN", "specification": "5-Y16"},
            {"layer": "STIRRUP", "role": "STIRRUP", "specification": "4L-Y8@100C/C"},
        ],
        independent_basis="MANUAL_VISUAL_VERIFICATION",
    )
    assert rec["reconciliation_status"] == STATUS_VIS_CONFIRMED
    assert rec["vision_result"] == "MATCHES_RECONCILED_TRUTH"
    assert rec["deterministic_result"] != "MATCHES_RECONCILED_TRUTH"


def test_fixture_rename_invariance() -> None:
    out = fixture_rename_invariance()
    assert out.get("ok") is True, out


def test_same_spec_top_bottom_distinct() -> None:
    groups = [
        {"layer": "TOP", "role": "MAIN", "specification": "3Y16"},
        {"layer": "BOTTOM", "role": "MAIN", "specification": "3Y16"},
    ]
    keys = keys_of(groups)
    assert len(set(keys)) == 2
    rec = reconcile_groups(vision_groups=groups, deterministic_groups=groups)
    assert rec["reconciliation_status"] == STATUS_EQUIVALENT
    assert len(rec["reconciled_groups"]) == 2


def test_main_extra_remain_distinct() -> None:
    groups = [
        {"layer": "BOTTOM", "role": "MAIN", "specification": "3Y20"},
        {"layer": "BOTTOM", "role": "EXTRA", "specification": "3Y20"},
    ]
    assert len(set(keys_of(groups))) == 2


def test_stirrup_separate_from_longitudinal() -> None:
    groups = [
        {"layer": "TOP", "role": "MAIN", "specification": "5Y20"},
        {"layer": "STIRRUP", "role": "STIRRUP", "specification": "4L-Y8@100C/C"},
    ]
    keys = set(keys_of(groups))
    assert ("STIRRUP", "STIRRUP", normalize_spec("4L-Y8@100C/C")) in keys
    assert ("TOP", "MAIN", normalize_spec("5Y20")) in keys
    assert len(keys) == 2


def test_safe_notation_normalization() -> None:
    assert normalize_spec("5-Y20") == normalize_spec("5Y20")
    assert normalize_spec("4L-Y8@100C/C") == normalize_spec("4L-Y8@\\X100C/C")
    a = physical_identity({"layer": "TOP", "role": "MAIN", "specification": "5-Y20"})
    b = physical_identity({"layer": "TOP", "role": "MAIN", "spec": "5Y20"})
    assert a == b


def test_no_unsafe_semantic_normalization() -> None:
    a = physical_identity({"layer": "TOP", "role": "MAIN", "specification": "5Y20"})
    b = physical_identity({"layer": "BOTTOM", "role": "MAIN", "specification": "5Y20"})
    c = physical_identity({"layer": "TOP", "role": "EXTRA", "specification": "5Y20"})
    assert a != b
    assert a != c


def test_both_equivalent_only_when_same_physical() -> None:
    same = reconcile_groups(
        vision_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5-Y20"}],
        deterministic_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y20"}],
    )
    diff = reconcile_groups(
        vision_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y20"}],
        deterministic_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y16"}],
    )
    assert same["reconciliation_status"] == STATUS_EQUIVALENT
    assert diff["reconciliation_status"] == STATUS_AMBIGUOUS


def test_metrics_use_reconciled_truth() -> None:
    vis_win = reconcile_groups(
        vision_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y20"}],
        deterministic_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y16"}],
        independent_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y20"}],
        independent_basis="MANUAL_VISUAL_VERIFICATION",
    )
    vis_win["reconciliation_status"] = vis_win["reconciliation_status"]
    metrics = aggregate_metrics([vis_win])
    assert metrics["vision_correct_group_count"] == 1
    assert metrics["deterministic_correct_group_count"] == 0
    assert metrics["deterministic_spurious_group_count"] == 1


def test_unresolved_excluded_from_forced_correctness() -> None:
    rec = reconcile_groups(
        vision_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y20"}],
        deterministic_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y16"}],
    )
    assert rec["vision_result"] == "UNRESOLVED"
    assert rec["deterministic_result"] == "UNRESOLVED"
    metrics = aggregate_metrics([rec])
    assert metrics["reconciled_expected_group_count"] == 0
    assert metrics["vision_correct_group_count"] == 0
    assert metrics["unresolved_excluded_from_forced_correctness"] is True


def test_no_predecessor_mutation_fingerprint() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True


def test_no_claude_api_or_dxf_in_runtime() -> None:
    leak = runtime_leakage_scan(_pkg())
    assert leak.get("ok") is True, leak
    for name in ("engine.py", "evidence.py", "phase_p2610c4_orchestrator.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "ezdxf" not in text
        assert "RenderSession" not in text
        assert "anthropic" not in text.lower()


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert LIVE_CLAUDE_CALL is False
    assert SHADOW_ONLY is True
    assert PRODUCTION_ACTION == "NO_CHANGE"
    assert MODEL_VERSION == "10.11.17"


def test_no_beam_id_literals_in_engine() -> None:
    guard = source_guard(_pkg())
    assert guard.get("ok") is True, guard.get("hits")


def test_control_population_integrity() -> None:
    intact = prior_artefacts_intact(_v10())
    assert intact.get("ok") is True, intact.get("missing")
    control = load_six_beam_control(_v10())
    for row in control.get("rows") or []:
        assert row.get("beam_id")
        assert "claude" in row


def test_source_fingerprint_immutability_and_firewall() -> None:
    fw = firewall_check(_v10())
    assert fw.get("ok") is True, fw.get("offenders")
    assert prior_phase_unit_ok(_v10(), "PhaseP266_semantic_longitudinal_resolver", 36).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP269_reinforcement_group_interpretation", 20).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610A_beam_region_crop_audit", 14).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B_adaptive_beam_detail_crop", 18).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B1_population_generalization", 16).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B2_render_quality_directional_recovery", 29).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B3_target_anchor_geometry_context_recovery", 18).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610C1C2_evidence_inventory_candidate_selection", 21).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610C3_visual_completeness_claude_shadow", 19).get("ok") is True


def test_deterministic_confirmed_path() -> None:
    rec = reconcile_groups(
        vision_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y20"}],
        deterministic_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y16"}],
        independent_groups=[{"layer": "TOP", "role": "MAIN", "specification": "5Y16"}],
        independent_basis="MANUAL_VISUAL_VERIFICATION",
    )
    assert rec["reconciliation_status"] == STATUS_DET_CONFIRMED


def test_anti_hardcoding_bundle() -> None:
    out = run_anti_hardcoding(package_dir=_pkg())
    assert out.get("ok") is True, out


def test_match_against_identity_rule() -> None:
    m = match_against(
        [{"layer": "TOP", "role": "MAIN", "specification": "5Y20"}],
        [{"layer": "TOP", "role": "MAIN", "specification": "5-Y20"}],
    )
    assert m["correct"] == 1
    assert m["identity_rule"] == "layer+role+specification"


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("six_beam_control_discovery", test_six_beam_control_discovery),
        ("missing_evidence_fail_closed", test_missing_evidence_fail_closed),
        ("contradictory_independent_ambiguous", test_contradictory_independent_ambiguous),
        ("explicit_verification_vision_confirmed", test_explicit_verification_vision_confirmed),
        ("fixture_rename_invariance", test_fixture_rename_invariance),
        ("same_spec_top_bottom_distinct", test_same_spec_top_bottom_distinct),
        ("main_extra_remain_distinct", test_main_extra_remain_distinct),
        ("stirrup_separate_from_longitudinal", test_stirrup_separate_from_longitudinal),
        ("safe_notation_normalization", test_safe_notation_normalization),
        ("no_unsafe_semantic_normalization", test_no_unsafe_semantic_normalization),
        ("both_equivalent_only_when_same_physical", test_both_equivalent_only_when_same_physical),
        ("metrics_use_reconciled_truth", test_metrics_use_reconciled_truth),
        ("unresolved_excluded_from_forced_correctness", test_unresolved_excluded_from_forced_correctness),
        ("no_predecessor_mutation_fingerprint", test_no_predecessor_mutation_fingerprint),
        ("no_claude_api_or_dxf_in_runtime", test_no_claude_api_or_dxf_in_runtime),
        ("production_write_false", test_production_write_false),
        ("no_beam_id_literals_in_engine", test_no_beam_id_literals_in_engine),
        ("control_population_integrity", test_control_population_integrity),
        ("source_fingerprint_immutability_and_firewall", test_source_fingerprint_immutability_and_firewall),
        ("deterministic_confirmed_path", test_deterministic_confirmed_path),
        ("anti_hardcoding_bundle", test_anti_hardcoding_bundle),
        ("match_against_identity_rule", test_match_against_identity_rule),
    ]
    results = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:
            results.append({"name": name, "pass": False, "error": str(exc)})
    passed = sum(1 for r in results if r.get("pass"))
    return {
        "success": passed == len(results),
        "passed": passed,
        "total": len(results),
        "results": results,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
    }


__all__ = ["run_unit_tests"]
