"""Unit tests for P2.6.10-C.3. Mocked Claude only. No production mutation."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

from .anti_hardcoding import run_anti_hardcoding, source_guard
from .comparison import group_identity, match_groups
from .config import (
    GATE_VERSION,
    MODEL_VERSION,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    SHADOW_ONLY,
    STATUS_LIMITED,
    STATUS_NOT_READY,
    STATUS_READY,
    STATUS_REVIEW,
)
from .evidence_model import SelectedRender, beam_from_manifest_row
from .manifest_loader import sha256_file, verify_selected_image
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
from .target_anchor_validator import validate_target_anchor
from .vision_benchmark import should_call
from .vision_contract import parse_and_validate, validate_claude_payload
from .visual_completeness_gate import evaluate_completeness


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _img(**kwargs) -> SelectedRender:
    defaults = dict(
        crop_type="context",
        source_phase="B.1",
        path="/x.png",
        sha256="aaa",
        primary_status="VALID",
        critical_failure=False,
        selection_status="RETAIN_PREFERRED",
        reason_codes=[],
        usable_status=True,
        score=4.0,
        foreground_ratio=0.12,
        coverage_x=0.85,
        coverage_y=0.80,
        empty_sides=[],
        quality_flags=[],
        integrity={"exists": True, "sha_mismatch": False, "file_missing": False, "integrity_ok": True},
    )
    defaults.update(kwargs)
    return SelectedRender(**defaults)


def _write_png(path: Path, color=(30, 30, 30), ink=True) -> Path:
    from PIL import Image, ImageDraw

    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (160, 120), color)
    if ink:
        d = ImageDraw.Draw(im)
        d.rectangle([12, 12, 90, 70], outline=(0, 180, 0), width=3)
    im.save(path)
    return path


def test_manifest_row_mixed_source() -> None:
    row = {
        "beam_id": "ZX",
        "context": {"selected_source_phase": "B.1", "selected_path": "/c.png", "selected_sha256": "1", "selected_critical_failure": False, "candidates": []},
        "detail": {"selected_source_phase": "B.3", "selected_path": "/d.png", "selected_sha256": "2", "selected_critical_failure": False, "candidates": []},
    }
    b = beam_from_manifest_row(row)
    assert b.context.source_phase == "B.1"
    assert b.detail.source_phase == "B.3"


def test_missing_png_and_sha_mismatch() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = _write_png(Path(td) / "a.png")
        h = sha256_file(p)
        miss = verify_selected_image({"selected_path": str(Path(td) / "nope.png"), "selected_sha256": h})
        assert miss["file_missing"] is True
        bad = verify_selected_image({"selected_path": str(p), "selected_sha256": "0" * 64})
        assert bad["sha_mismatch"] is True
        ok = verify_selected_image({"selected_path": str(p), "selected_sha256": h})
        assert ok["integrity_ok"] is True


def test_blank_black_low_info_not_ready() -> None:
    for status in ("EMPTY_RENDER", "BLACK_RENDER", "LOW_INFORMATION_RENDER"):
        ctx = _img(primary_status=status, critical_failure=True, usable_status=False)
        det = _img(crop_type="detail")
        r = evaluate_completeness(ctx, det)
        assert r["status"] == STATUS_NOT_READY


def test_clip_sufficient_is_limited() -> None:
    ctx = _img(primary_status="BORDER_CLIPPING_SUSPECT", quality_flags=["BORDER_CLIPPING_SUSPECT"])
    det = _img(crop_type="detail", primary_status="BORDER_CLIPPING_SUSPECT", quality_flags=["BORDER_CLIPPING_SUSPECT"])
    r = evaluate_completeness(ctx, det)
    assert r["status"] == STATUS_LIMITED


def test_valid_ready() -> None:
    r = evaluate_completeness(_img(), _img(crop_type="detail", path="/d.png"))
    assert r["status"] == STATUS_READY


def test_association_ambiguous_review() -> None:
    ctx = _img(coverage_x=0.2)
    det = _img(crop_type="detail", path="/d.png")
    r = evaluate_completeness(ctx, det)
    assert r["status"] == STATUS_REVIEW
    assert "TARGET_ASSOCIATION_AMBIGUOUS" in r["reason_codes"]


def test_unusable_not_critical_review() -> None:
    ctx = _img(usable_status=False, primary_status="LOW_CONTEXT_QUALITY")
    det = _img(crop_type="detail", path="/d.png")
    r = evaluate_completeness(ctx, det)
    assert r["status"] == STATUS_REVIEW


def test_should_call_policy() -> None:
    assert should_call(gate_status=STATUS_NOT_READY, six_beam_control=False, include_limitations=False)[0] is False
    assert should_call(gate_status=STATUS_READY, six_beam_control=False, include_limitations=False)[0] is True
    assert should_call(gate_status=STATUS_LIMITED, six_beam_control=False, include_limitations=False)[0] is False
    assert should_call(gate_status=STATUS_LIMITED, six_beam_control=True, include_limitations=False)[0] is True


def test_valid_claude_json() -> None:
    payload = {
        "target_beam_id": "ZX",
        "target_beam_identified": True,
        "target_association_confidence": 0.8,
        "visual_assessment": {},
        "reinforcement_groups": [{"layer": "TOP", "role": "MAIN", "spec": "3Y16", "support_scope": "FULL_SPAN", "confidence": 0.7}],
        "stirrups": [],
        "uncertainties": [],
        "neighbor_evidence_detected": False,
        "response_status": "OK",
    }
    ok, errs = validate_claude_payload(payload, requested_beam_id="ZX")
    assert ok, errs
    parsed = parse_and_validate(json.dumps(payload), requested_beam_id="ZX")
    assert parsed["usable"] is True
    assert parsed["production_action"] == "NO_CHANGE"


def test_malformed_and_unknown_enum_and_forbidden() -> None:
    assert parse_and_validate("not-json", requested_beam_id="ZX")["usable"] is False
    bad_enum = {
        "target_beam_id": "ZX",
        "reinforcement_groups": [{"layer": "WEIRD", "role": "MAIN", "spec": "3Y16", "support_scope": "FULL_SPAN"}],
        "stirrups": [],
    }
    ok, errs = validate_claude_payload(bad_enum, requested_beam_id="ZX")
    assert ok is False and any("unknown_layer" in e for e in errs)
    forbid = {"target_beam_id": "ZX", "production_action": "INSERT", "reinforcement_groups": [], "stirrups": []}
    ok, errs = validate_claude_payload(forbid, requested_beam_id="ZX")
    assert ok is False and any("forbidden_field" in e for e in errs)


def test_same_spec_distinct_identities() -> None:
    pred = [
        {"layer": "TOP", "role": "MAIN", "spec": "3-Y16"},
        {"layer": "BOTTOM", "role": "MAIN", "spec": "3Y16"},
    ]
    exp = [
        {"physical_layer": "TOP", "reinforcement_role": "MAIN", "specification": "3Y16"},
        {"physical_layer": "BOTTOM", "reinforcement_role": "MAIN", "specification": "3Y16"},
    ]
    m = match_groups(pred, exp)
    assert m["correctly_matched_count"] == 2
    assert group_identity(pred[0]) != group_identity(pred[1])
    roles = [
        {"layer": "BOTTOM", "role": "MAIN", "spec": "3Y20"},
        {"layer": "BOTTOM", "role": "EXTRA", "spec": "3Y20"},
    ]
    assert group_identity(roles[0]) != group_identity(roles[1])
    collapsed = match_groups([{"layer": "TOP", "role": "MAIN", "spec": "3Y16"}], exp)
    assert collapsed["merged_distinct_groups"] >= 1


def test_timeout_unusable() -> None:
    parsed = parse_and_validate("", requested_beam_id="ZX")
    assert parsed["usable"] is False


def test_source_guard_and_invariance() -> None:
    g = source_guard(_pkg())
    assert g.get("ok") is True, g.get("hits")
    for name in ("visual_completeness_gate.py", "target_anchor_validator.py", "comparison.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for tok in ("B32", "B19", "B24A", "B141", "B55", "B128"):
            assert tok not in text, f"{name} contains {tok}"
    anti = run_anti_hardcoding(package_dir=_pkg())
    assert anti.get("ok") is True, anti


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.16"
    assert GATE_VERSION == "P2610C3_VISUAL_COMPLETENESS_CLAUDE_SHADOW_BENCHMARK_V1_0"
    assert SHADOW_ONLY is True
    assert PRODUCTION_ACTION == "NO_CHANGE"


def test_prior_phase_artefacts() -> None:
    assert prior_phase_unit_ok(_v10(), "PhaseP266_semantic_longitudinal_resolver", 36).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP269_reinforcement_group_interpretation", 20).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B1_population_generalization", 16).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610C1C2_evidence_inventory_candidate_selection", 21).get("ok") is True
    intact = prior_artefacts_intact(_v10())
    assert intact.get("ok") is True, intact.get("missing")


def test_fingerprints_firewall() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True
    fw = firewall_check(_v10())
    assert fw.get("ok") is True, fw.get("offenders")
    leak = runtime_leakage_scan(_pkg())
    assert leak.get("ok") is True, leak.get("hits")


def test_decision_never_production_ready() -> None:
    from .phase_p2610c3_orchestrator import _classify_decision

    d = _classify_decision(
        tests_ok=True,
        fingerprints_ok=True,
        anti_ok=True,
        hardcoding=False,
        production_mutations=0,
        live_failed=False,
        unresolved_limitations=True,
    )
    assert d == "PASS_WITH_LIMITATIONS"
    assert "PRODUCTION_READY" not in d


def test_no_rerender_imports() -> None:
    for name in ("visual_completeness_gate.py", "manifest_loader.py", "phase_p2610c3_orchestrator.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "ezdxf" not in text
        assert "RenderSession" not in text


def test_anchor_mixed_source() -> None:
    a = validate_target_anchor(_img(source_phase="B.1"), _img(crop_type="detail", source_phase="B.3", path="/d.png"))
    assert a["mixed_source"] is True


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("manifest_row_mixed_source", test_manifest_row_mixed_source),
        ("missing_png_and_sha_mismatch", test_missing_png_and_sha_mismatch),
        ("blank_black_low_info_not_ready", test_blank_black_low_info_not_ready),
        ("clip_sufficient_is_limited", test_clip_sufficient_is_limited),
        ("valid_ready", test_valid_ready),
        ("association_ambiguous_review", test_association_ambiguous_review),
        ("unusable_not_critical_review", test_unusable_not_critical_review),
        ("should_call_policy", test_should_call_policy),
        ("valid_claude_json", test_valid_claude_json),
        ("malformed_and_unknown_enum_and_forbidden", test_malformed_and_unknown_enum_and_forbidden),
        ("same_spec_distinct_identities", test_same_spec_distinct_identities),
        ("timeout_unusable", test_timeout_unusable),
        ("source_guard_and_invariance", test_source_guard_and_invariance),
        ("production_write_false", test_production_write_false),
        ("prior_phase_artefacts", test_prior_phase_artefacts),
        ("fingerprints_firewall", test_fingerprints_firewall),
        ("decision_never_production_ready", test_decision_never_production_ready),
        ("no_rerender_imports", test_no_rerender_imports),
        ("anchor_mixed_source", test_anchor_mixed_source),
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
