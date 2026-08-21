"""Unit tests for P2.6.10-C.5. Offline. No production mutation."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .anti_hardcoding import rename_invariance, repeatability, run_anti_hardcoding, source_guard
from .comparison import compare_beam, match_physical
from .config import (
    GATE_VERSION,
    MAX_SAMPLE_SIZE,
    MODEL_VERSION,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    SHADOW_ONLY,
    TARGET_SAMPLE_SIZE,
)
from .discovery import discover_fourth_set, load_prior_control_ids, load_selection_manifest
from .length_evidence import attach_length_evidence, summarize_length_vs_role
from .normalize import normalize_spec, parse_bar_count, physical_key
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
from .sampler import select_sample
from .vision_contract import parse_and_validate, validate_claude_payload


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _cand(i: int, **kwargs: Any) -> Dict[str, Any]:
    rec = {
        "beam_id": f"T{i:02d}",
        "set_key": "Fourth",
        "evidence_valid": True,
        "c3_visual_gate_status": "VISION_READY_WITH_LIMITATIONS",
        "neighbour_association_risk": False,
        "association_ambiguous": False,
        "mixed_source": False,
        "deterministic_group_count": 2,
        "group_stats": {
            "longitudinal_count": 2,
            "stirrup_count": 1,
            "top_count": 1,
            "bottom_count": 1,
            "has_main": True,
            "has_extra": False,
            "same_spec_distinct": False,
            "stirrup_present": True,
            "stirrup_complex": True,
        },
    }
    rec.update(kwargs)
    return rec


def test_sample_size_cap() -> None:
    recs = [_cand(i) for i in range(1, 20)]
    out = select_sample(recs, exclude_ids=[], target_size=10)
    assert out.get("ok") is True
    assert len(out.get("selected_ids") or []) <= 10
    bad = select_sample(recs, exclude_ids=[], target_size=11)
    assert bad.get("ok") is False


def test_fourth_set_membership() -> None:
    fourth = discover_fourth_set(_v10())
    assert fourth.get("ok") is True
    assert fourth.get("set_key") == "Fourth"
    assert len(fourth.get("beam_ids") or []) >= 10
    sel = {r.get("beam_id") for r in load_selection_manifest(_v10())}
    overlap = [b for b in fourth.get("beam_ids") if b in sel]
    assert len(overlap) == len(fourth.get("beam_ids"))


def test_no_duplicate_ids() -> None:
    recs = [_cand(i) for i in range(1, 16)]
    recs.append(_cand(3))
    out = select_sample(recs, exclude_ids=[], target_size=10)
    ids = out.get("selected_ids") or []
    assert len(ids) == len(set(ids))


def test_repeatability() -> None:
    assert repeatability().get("ok") is True


def test_no_hardcoded_selection() -> None:
    assert source_guard(_pkg()).get("ok") is True, source_guard(_pkg()).get("hits")


def test_invalid_excluded() -> None:
    recs = [_cand(1), _cand(2, evidence_valid=False, excluded_reason="MISSING_SELECTED_PNG")]
    recs += [_cand(i) for i in range(3, 14)]
    out = select_sample(recs, exclude_ids=[], target_size=10)
    assert "T02" not in (out.get("selected_ids") or [])


def test_mixed_source_preserved() -> None:
    recs = [_cand(i, mixed_source=(i == 1), c3_visual_gate_status="VISION_READY" if i == 1 else "VISION_READY_WITH_LIMITATIONS") for i in range(1, 14)]
    recs[0]["group_stats"] = recs[0]["group_stats"]
    out = select_sample(recs, exclude_ids=[], target_size=10)
    by_id = {r["beam_id"]: r for r in out.get("selected") or []}
    if "T01" in by_id:
        assert by_id["T01"].get("mixed_source") is True


def test_role_only_not_total_failure() -> None:
    vis = [{"layer": "TOP", "spec": "3-Y20", "role_hypothesis": "EXTRA", "bar_count": 3}]
    det = [{"layer": "TOP", "spec": "3Y20", "role": "MAIN", "bar_count": 3}]
    m = match_physical(vis, det)
    assert len(m["pairs"]) == 1
    p = m["pairs"][0]
    assert p["physical_group_match"] is True
    assert p["layer_match"] is True
    assert p["spec_match"] is True
    assert p["role_match"] is False
    parsed = {
        "usable": True,
        "target_identified": True,
        "target_beam_id": "T01",
        "groups": vis,
        "stirrups": [],
    }
    det_full = [{"physical_layer": "TOP", "reinforcement_role": "MAIN", "specification": "3Y20", "count": 3, "family": "LONGITUDINAL"}]
    cmp = compare_beam(parsed=parsed, detected=det_full, expected=[], requested_id="T01")
    assert "ROLE_ONLY_DISAGREEMENT" in cmp["taxonomy"]
    assert "GROUP_STRUCTURE_DISAGREEMENT" not in cmp["taxonomy"]


def test_same_spec_distinct() -> None:
    vis = [
        {"layer": "TOP", "spec": "3Y16", "role_hypothesis": "MAIN"},
        {"layer": "BOTTOM", "spec": "3Y16", "role_hypothesis": "MAIN"},
    ]
    assert physical_key(vis[0]) != physical_key(vis[1])
    m = match_physical(vis, vis)
    assert len(m["pairs"]) == 2


def test_count_classification() -> None:
    vis = [{"layer": "TOP", "spec": "5Y20", "role_hypothesis": "MAIN", "bar_count": 5}]
    det = [{"layer": "TOP", "spec": "5Y20", "role": "MAIN", "bar_count": 4}]
    p = match_physical(vis, det)["pairs"][0]
    assert p["count_comparison"] == "OVER_ESTIMATE"
    det2 = [{"layer": "TOP", "spec": "5Y20", "role": "MAIN", "bar_count": 6}]
    assert match_physical(vis, det2)["pairs"][0]["count_comparison"] == "UNDER_ESTIMATE"
    det3 = [{"layer": "TOP", "spec": "5Y20", "role": "MAIN", "bar_count": 5}]
    assert match_physical(vis, det3)["pairs"][0]["count_comparison"] == "EXACT"


def test_length_does_not_override_role() -> None:
    groups = attach_length_evidence(
        [{"layer": "TOP", "spec": "5Y20", "role_hypothesis": "EXTRA", "relative_length_evidence": "LONGER", "support_scope": "FULL_SPAN"}]
    )
    assert groups[0]["role_hypothesis"] == "EXTRA"
    s = summarize_length_vs_role(groups)
    assert s["role_hypothesis_conflicts"] >= 1
    assert "does not override" in s["note"].lower()


def test_schema_fail_closed() -> None:
    rec = parse_and_validate("{not json", requested_beam_id="T01")
    assert rec.get("usable") is False
    bad = {"target_beam_id": "T01", "groups": [{"layer": "MOON", "spec": "5Y20"}], "stirrups": []}
    ok, errors = validate_claude_payload(bad, requested_beam_id="T01")
    assert ok is False
    assert any("unknown_layer" in e for e in errors)


def test_valid_schema() -> None:
    raw = """{
      "target_beam_id": "T01",
      "target_identified": true,
      "association_confidence": 0.9,
      "groups": [{"physical_group_id": "G1", "layer": "TOP", "spec": "5-Y20", "bar_count": 5,
                  "role_hypothesis": "MAIN", "role_confidence": 0.8, "support_scope": "FULL_SPAN",
                  "relative_length_evidence": "UNKNOWN", "span_relationship": "UNKNOWN",
                  "confidence": 0.9, "evidence": "visible"}],
      "stirrups": [{"spec": "4L-Y8@100C/C", "confidence": 0.8, "evidence": "label"}],
      "ambiguities": [],
      "neighbour_evidence_detected": false,
      "response_status": "OK"
    }"""
    rec = parse_and_validate(raw, requested_beam_id="T01")
    assert rec.get("usable") is True
    assert rec["groups"][0]["layer"] == "TOP"


def test_forbidden_fields() -> None:
    obj = {"target_beam_id": "T01", "production_action": "WRITE", "groups": [], "stirrups": []}
    ok, errors = validate_claude_payload(obj, requested_beam_id="T01")
    assert ok is False
    assert any("forbidden" in e for e in errors)


def test_normalize_and_parse_count() -> None:
    assert normalize_spec("5-Y20") == normalize_spec("5Y20")
    assert parse_bar_count("5-Y20") == 5


def test_production_and_no_dxf() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert SHADOW_ONLY is True
    assert PRODUCTION_ACTION == "NO_CHANGE"
    leak = runtime_leakage_scan(_pkg())
    assert leak.get("ok") is True, leak
    for name in ("sampler.py", "discovery.py", "phase_p2610c5_orchestrator.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "ezdxf" not in text
        assert "RenderSession" not in text


def test_fingerprints_and_prior() -> None:
    assert prior_artefacts_intact(_v10()).get("ok") is True
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True
    fw = firewall_check(_v10())
    assert fw.get("ok") is True, fw.get("offenders")
    assert prior_phase_unit_ok(_v10(), "PhaseP266_semantic_longitudinal_resolver", 36).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610C3_visual_completeness_claude_shadow", 19).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610C4_shadow_truth_reconciliation_benchmark_calibration", 22).get("ok") is True


def test_rename_invariance() -> None:
    assert rename_invariance().get("ok") is True


def test_control_exclusion_generic() -> None:
    recs = [_cand(i) for i in range(1, 16)]
    out = select_sample(recs, exclude_ids=["T01", "T02"], target_size=10)
    ids = out.get("selected_ids") or []
    assert "T01" not in ids and "T02" not in ids


def test_anti_bundle() -> None:
    out = run_anti_hardcoding(package_dir=_pkg())
    assert out.get("ok") is True, out


def test_api_failure_unusable() -> None:
    from .vision_contract import unusable

    rec = unusable("api_error:timeout", call_status="API_FAILED")
    assert rec["usable"] is False
    assert rec["call_status"] == "API_FAILED"
    assert rec["groups"] == []


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("sample_size_cap", test_sample_size_cap),
        ("fourth_set_membership", test_fourth_set_membership),
        ("no_duplicate_ids", test_no_duplicate_ids),
        ("repeatability", test_repeatability),
        ("no_hardcoded_selection", test_no_hardcoded_selection),
        ("invalid_excluded", test_invalid_excluded),
        ("mixed_source_preserved", test_mixed_source_preserved),
        ("role_only_not_total_failure", test_role_only_not_total_failure),
        ("same_spec_distinct", test_same_spec_distinct),
        ("count_classification", test_count_classification),
        ("length_does_not_override_role", test_length_does_not_override_role),
        ("schema_fail_closed", test_schema_fail_closed),
        ("valid_schema", test_valid_schema),
        ("forbidden_fields", test_forbidden_fields),
        ("normalize_and_parse_count", test_normalize_and_parse_count),
        ("production_and_no_dxf", test_production_and_no_dxf),
        ("fingerprints_and_prior", test_fingerprints_and_prior),
        ("rename_invariance", test_rename_invariance),
        ("control_exclusion_generic", test_control_exclusion_generic),
        ("anti_bundle", test_anti_bundle),
        ("api_failure_unusable", test_api_failure_unusable),
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
        "max_sample": MAX_SAMPLE_SIZE,
        "target_sample": TARGET_SAMPLE_SIZE,
    }


__all__ = ["run_unit_tests"]
