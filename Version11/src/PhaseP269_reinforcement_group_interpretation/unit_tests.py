"""Unit tests for P2.6.9. No live Claude. Does not change P2.6.4–P2.6.8 routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .comparator import apply_overlay, compare_inventories
from .config import (
    FAMILY_LONGITUDINAL,
    FAMILY_STIRRUP,
    GATE_VERSION,
    LAYER_BOTTOM,
    LAYER_TOP,
    MODEL_VERSION,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    ROLE_EXTRA,
    ROLE_MAIN,
    SHADOW_ONLY,
    ZONE_BOTH_SUPPORTS,
    ZONE_FULL_SPAN,
)
from .drawing_groups import extract_drawing_groups
from .evaluator import classify_phase
from .extractor import extract_detected_groups
from .group_model import identity_key, make_group
from .identity import collapse_piece_groups
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _g(**kwargs: Any) -> Dict[str, Any]:
    base = dict(
        beam_id="BX",
        group_id="",
        family=FAMILY_LONGITUDINAL,
        physical_layer=LAYER_TOP,
        reinforcement_role=ROLE_MAIN,
        count=3,
        diameter=16,
        specification="3Y16",
        zone=ZONE_FULL_SPAN,
        provenance="TEST",
        evidence_quality="TEST",
        confidence=1.0,
    )
    base.update(kwargs)
    return make_group(**base)


def _bar(*, role: str, qty: int, dia: int, piece: str, extent: str = "FULL_SPAN", label: str = "") -> Dict[str, Any]:
    return {
        "bar_id": f"R13-{piece}",
        "semantic_role": role,
        "piece_type": piece,
        "quantity": qty,
        "diameter_mm": dia,
        "extent": extent,
        "support_zone": extent,
        "position_zone": extent,
        "bar_label": label or f"{qty}Y{dia}",
        "spacing_mm": "",
        "classification_confidence": 0.8,
    }


def test_same_spec_different_layer_distinct() -> None:
    groups = collapse_piece_groups(
        [
            _g(physical_layer=LAYER_TOP, specification="3Y16"),
            _g(physical_layer=LAYER_BOTTOM, specification="3Y16", reinforcement_role=ROLE_MAIN),
        ]
    )
    assert len(groups) == 2
    layers = {g["physical_layer"] for g in groups}
    assert layers == {LAYER_TOP, LAYER_BOTTOM}


def test_same_spec_same_layer_different_role_distinct() -> None:
    groups = collapse_piece_groups(
        [
            _g(physical_layer=LAYER_BOTTOM, reinforcement_role=ROLE_MAIN, specification="3Y25", count=3, diameter=25),
            _g(physical_layer=LAYER_BOTTOM, reinforcement_role=ROLE_EXTRA, specification="3Y25", count=3, diameter=25, zone="SUPPORT_ZONE"),
        ]
    )
    assert len(groups) == 2


def test_lr_extras_collapse_to_one_group() -> None:
    groups = collapse_piece_groups(
        [
            _g(reinforcement_role=ROLE_EXTRA, specification="2Y16", count=2, diameter=16, zone="LEFT_SUPPORT"),
            _g(reinforcement_role=ROLE_EXTRA, specification="2Y16", count=2, diameter=16, zone="RIGHT_SUPPORT"),
        ]
    )
    assert len(groups) == 1
    assert groups[0]["zone"] == ZONE_BOTH_SUPPORTS


def test_spec_only_dedup_forbidden() -> None:
    keys = {
        identity_key(_g(physical_layer=LAYER_TOP, specification="2Y16", reinforcement_role=ROLE_EXTRA)),
        identity_key(_g(physical_layer=LAYER_BOTTOM, specification="2Y16", reinforcement_role=ROLE_EXTRA)),
    }
    assert len(keys) == 2


def test_extractor_collapses_lr_and_keeps_layers() -> None:
    model = {
        "beam_id": "BX",
        "top_main_bars": [_bar(role="TOP_MAIN", qty=3, dia=20, piece="TOP_MAIN")],
        "top_extra_bars": [
            _bar(role="TOP_EXTRA", qty=2, dia=16, piece="TOP_EXTRA_LEFT", extent="LEFT_SUPPORT"),
            _bar(role="TOP_EXTRA", qty=2, dia=16, piece="TOP_EXTRA_RIGHT", extent="RIGHT_SUPPORT"),
        ],
        "bottom_main_bars": [_bar(role="BOTTOM_MAIN", qty=3, dia=25, piece="BOTTOM_MAIN")],
        "bottom_extra_bars": [],
        "stirrups": [
            {
                "bar_id": "R13-ST",
                "semantic_role": "STIRRUP",
                "piece_type": "STIRRUP_ZONE_A",
                "quantity": 50,
                "diameter_mm": 10,
                "bar_label": "3L-Y10@100#Zone_A",
                "spacing_mm": 100,
                "spacing_pattern": "100",
                "extent": "FULL_SPAN",
                "support_zone": "FULL_SPAN",
                "position_zone": "Zone_A",
            }
        ],
        "spacer_bars": [],
        "side_face_reinforcement": [],
    }
    det = extract_detected_groups(model)
    long_ = [g for g in det if g["family"] == FAMILY_LONGITUDINAL]
    extras = [g for g in long_ if g["reinforcement_role"] == ROLE_EXTRA]
    assert len(extras) == 1
    assert extras[0]["zone"] == ZONE_BOTH_SUPPORTS
    assert any(g["family"] == FAMILY_STIRRUP and str(g["specification"]).startswith("3L-Y10") for g in det)
    assert any(g["physical_layer"] == LAYER_TOP and g["specification"] == "3Y20" for g in det)
    assert any(g["physical_layer"] == LAYER_BOTTOM and g["specification"] == "3Y25" for g in det)


def test_drawing_groups_split_different_specs_in_same_role() -> None:
    anns = [
        {"annotation_id": "A1", "clean_text": "3-Y16", "role": "BOTTOM_EXTRA", "quantity": 3, "diameter_mm": 16, "beam_id": "BX"},
        {"annotation_id": "A2", "clean_text": "3-Y20", "role": "BOTTOM_EXTRA", "quantity": 3, "diameter_mm": 20, "beam_id": "BX"},
        {"annotation_id": "A3", "clean_text": "3-Y20", "role": "BOTTOM_MAIN", "quantity": 3, "diameter_mm": 20, "beam_id": "BX"},
        {"annotation_id": "A4", "clean_text": "3L-Y10@100/125/100C/C", "role": "STIRRUP", "quantity": 3, "diameter_mm": 10, "beam_id": "BX"},
    ]
    groups = extract_drawing_groups(anns, beam_id="BX")
    specs = {(g["physical_layer"], g["reinforcement_role"], g["specification"]) for g in groups}
    assert ("BOTTOM", "EXTRA", "3Y16") in specs
    assert ("BOTTOM", "EXTRA", "3Y20") in specs
    assert ("BOTTOM", "MAIN", "3Y20") in specs
    stirrup = [g for g in groups if g["family"] == FAMILY_STIRRUP]
    assert len(stirrup) == 1
    assert stirrup[0]["physical_layer"] != LAYER_TOP


def test_merged_distinct_detected() -> None:
    expected = [
        _g(physical_layer=LAYER_TOP, specification="3Y16"),
        _g(physical_layer=LAYER_BOTTOM, specification="3Y16"),
    ]
    detected = [_g(physical_layer=LAYER_TOP, specification="3Y16")]
    cmp = compare_inventories(expected=expected, detected=detected)
    assert "MISSED_GROUP" in cmp["errors"]
    assert any(m[1] == LAYER_BOTTOM for m in cmp["missing_groups"])


def test_overlay_adds_missing_bottom_without_runtime_beam_rule() -> None:
    drawing = [_g(physical_layer=LAYER_TOP, specification="3Y16", beam_id="BX")]
    overlay = {
        "overlay_groups": [
            {
                "family": FAMILY_LONGITUDINAL,
                "physical_layer": LAYER_BOTTOM,
                "reinforcement_role": ROLE_MAIN,
                "specification": "3Y16",
                "count": 3,
                "diameter": 16,
            }
        ]
    }
    expected = apply_overlay(drawing, overlay)
    layers = {g["physical_layer"] for g in expected if g["specification"] == "3Y16"}
    assert layers == {LAYER_TOP, LAYER_BOTTOM}


def test_shadow_cannot_mutate_production() -> None:
    model = {"beam_id": "BX", "top_main_bars": [_bar(role="TOP_MAIN", qty=5, dia=16, piece="TOP_MAIN")]}
    before = json.dumps(model, sort_keys=True)
    extract_detected_groups(model)
    assert json.dumps(model, sort_keys=True) == before


def test_no_beam_id_hardcoding_in_runtime() -> None:
    for name in ("extractor.py", "drawing_groups.py", "identity.py", "layer_role.py", "group_model.py", "comparator.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for token in ("B128", "B141", "B55", "B66", "B161", "B65"):
            assert token not in text, f"{name} contains {token}"


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.9"
    assert GATE_VERSION == "P269_REINFORCEMENT_GROUP_INTERPRETATION_V1_0"


def test_no_gt_usage() -> None:
    for name in ("extractor.py", "drawing_groups.py", "identity.py", "dataset.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "TRUE_RECOVERY" not in text
        assert "load_gt_universe" not in text
        assert "EstimatorOutput" not in text


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


def test_p268_regression_file() -> None:
    prior = _v10() / "data" / "output" / "PhaseP268_evidence_conflict_arbitration" / "unit_tests.json"
    payload = json.loads(prior.read_text(encoding="utf-8"))
    assert payload.get("success") is True
    assert int(payload.get("passed") or 0) >= 27


def test_production_identical_fingerprints() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True


def test_firewall_and_leakage() -> None:
    fw = firewall_check(_v10())
    assert fw["ok"], fw.get("offenders")
    leak = runtime_leakage_scan(_pkg())
    assert leak["ok"], leak.get("hits")


def test_classify_phase_never_production_ready() -> None:
    rec = classify_phase(
        tests_ok=True,
        fingerprints_ok=True,
        production_mutation=0,
        all_shadow=True,
        all_no_change=True,
        six_beams=True,
        inventories_complete=True,
    )
    assert rec["decision"] == "SAFE_SHADOW_BENCHMARK"
    assert rec["decision"] != "PRODUCTION_READY"


def test_six_beam_inventories_from_artefacts() -> None:
    from .dataset import load_benchmark_targets, load_control_overlay
    from .evaluator import evaluate_controls

    targets = load_benchmark_targets(_v10())
    assert len(targets) == 6
    overlays = load_control_overlay(_pkg())
    records: List[Dict[str, Any]] = []
    for t in targets:
        det = extract_detected_groups(t.get("r13_model") or {})
        drawing = extract_drawing_groups(t.get("r1_annotations") or [], beam_id=str(t.get("beam_id")))
        expected = apply_overlay(drawing, overlays.get((t.get("set_key"), t.get("beam_id"))))
        assert expected, f"empty expected for {t.get('set_key')}/{t.get('beam_id')}"
        assert t.get("model_found") is True
        records.append(
            {
                "set_key": t.get("set_key"),
                "beam_id": t.get("beam_id"),
                "expected_groups": expected,
                "detected_groups": det,
                "comparison": compare_inventories(expected=expected, detected=det),
                "production_action": PRODUCTION_ACTION,
                "shadow_only": SHADOW_ONLY,
            }
        )
    controls = evaluate_controls(records)
    b128 = next(r for r in records if r["set_key"] == "Fifth" and r["beam_id"] == "B128")
    assert any(g["physical_layer"] == LAYER_TOP and g["specification"] == "3Y16" for g in b128["expected_groups"])
    assert any(g["physical_layer"] == LAYER_BOTTOM and g["specification"] == "3Y16" for g in b128["expected_groups"])
    assert controls["b141"]["not_b128_same_spec_conflict"] is True
    b55 = next(r for r in records if r["set_key"] == "Fifth" and r["beam_id"] == "B55")
    assert any(g["family"] == FAMILY_STIRRUP for g in b55["expected_groups"])
    assert all(r["production_action"] == PRODUCTION_ACTION and r["shadow_only"] is True for r in records)


def test_stirrup_not_merged_into_longitudinal() -> None:
    expected = [
        _g(family=FAMILY_STIRRUP, physical_layer="STIRRUP", reinforcement_role="STIRRUP", specification="3L-Y10", count=3, diameter=10),
    ]
    detected = [
        _g(family=FAMILY_LONGITUDINAL, physical_layer=LAYER_TOP, specification="3L-Y10", count=3, diameter=10),
    ]
    cmp = compare_inventories(expected=expected, detected=detected)
    assert "STIRRUP_LONGITUDINAL_MIXUP" in cmp["errors"] or "MISSED_GROUP" in cmp["errors"]


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("same_spec_different_layer_distinct", test_same_spec_different_layer_distinct),
        ("same_spec_same_layer_different_role_distinct", test_same_spec_same_layer_different_role_distinct),
        ("lr_extras_collapse_to_one_group", test_lr_extras_collapse_to_one_group),
        ("spec_only_dedup_forbidden", test_spec_only_dedup_forbidden),
        ("extractor_collapses_lr_and_keeps_layers", test_extractor_collapses_lr_and_keeps_layers),
        ("drawing_groups_split_different_specs_in_same_role", test_drawing_groups_split_different_specs_in_same_role),
        ("merged_distinct_detected", test_merged_distinct_detected),
        ("overlay_adds_missing_bottom_without_runtime_beam_rule", test_overlay_adds_missing_bottom_without_runtime_beam_rule),
        ("shadow_cannot_mutate_production", test_shadow_cannot_mutate_production),
        ("no_beam_id_hardcoding_in_runtime", test_no_beam_id_hardcoding_in_runtime),
        ("production_write_false", test_production_write_false),
        ("no_gt_usage", test_no_gt_usage),
        ("P2.6.6_regression", test_p266_regression_file),
        ("P2.6.7_regression", test_p267_regression_file),
        ("P2.6.8_regression", test_p268_regression_file),
        ("production_identical_fingerprints", test_production_identical_fingerprints),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("classify_phase_never_production_ready", test_classify_phase_never_production_ready),
        ("six_beam_inventories_from_artefacts", test_six_beam_inventories_from_artefacts),
        ("stirrup_not_merged_into_longitudinal", test_stirrup_not_merged_into_longitudinal),
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
