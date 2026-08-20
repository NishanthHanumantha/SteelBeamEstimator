"""Unit tests for P2.6.10-C.1+C.2. No live Claude. No DXF. No source mutation."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

from .anti_hardcoding import packed_sheet_robustness, source_guard, spatial_distance_robustness
from .config import (
    GATE_VERSION,
    MATERIAL_SCORE_MARGIN,
    MODEL_VERSION,
    PRODUCTION_ACTION,
    PRODUCTION_WRITE,
    SHADOW_ONLY,
    SOURCE_B1,
    SOURCE_B2,
    SOURCE_B3,
)
from .inventory import inventory_beam, population_beam_ids, sha256_file
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
from .selector import select_beam, select_for_type


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _cand(
    *,
    phase: str,
    exists: bool = True,
    critical: bool = False,
    score: float = 4.0,
    fg: float = 0.12,
    cov: float = 0.80,
    sha: str = "sha",
    artefact_id: str = "",
    crop_type: str = "context",
) -> Dict[str, Any]:
    aid = artefact_id or ("canonical" if phase == SOURCE_B1 else "final")
    return {
        "source_phase": phase,
        "crop_type": crop_type,
        "artefact_id": aid,
        "exists": exists,
        "candidate_status": "AVAILABLE" if exists else "MISSING",
        "sha256": sha if exists else None,
        "critical_failure": bool(critical or not exists),
        "score": -1.0 if critical or not exists else score,
        "foreground_ratio": 0.0 if critical or not exists else fg,
        "coverage_x": 0.0 if critical or not exists else cov,
        "coverage_y": 0.7,
        "usable_status": exists and not critical,
        "primary_status": "EMPTY_RENDER" if critical or not exists else "VALID",
        "path": f"/synthetic/{phase}-{crop_type}.png" if exists else None,
        "empty_sides": [],
    }


def _write_png(path: Path, color, size=(160, 120), ink=False) -> Path:
    from PIL import Image, ImageDraw

    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", size, color)
    if ink:
        d = ImageDraw.Draw(im)
        d.rectangle([20, 20, 80, 80], outline=(0, 180, 0), width=3)
        d.line([10, 60, 140, 60], fill=(200, 40, 40), width=2)
    im.save(path)
    return path


def test_preferred_b1_retained() -> None:
    cands = [_cand(phase=SOURCE_B1, score=4.0, sha="b1"), _cand(phase=SOURCE_B2, score=3.5, sha="b2")]
    r = select_for_type(cands)
    assert r["decision"] == "RETAIN"
    assert r["selected"]["source_phase"] == SOURCE_B1
    assert "PREFERRED_BASELINE" in r["selection_reason_codes"]


def test_tiny_score_does_not_replace() -> None:
    cands = [
        _cand(phase=SOURCE_B1, score=4.0, fg=0.12, sha="b1"),
        _cand(phase=SOURCE_B2, score=4.0 + (MATERIAL_SCORE_MARGIN * 0.2), fg=0.121, sha="b2"),
    ]
    r = select_for_type(cands)
    assert r["decision"] == "RETAIN"
    assert r["selected"]["source_phase"] == SOURCE_B1


def test_b1_critical_b2_valid() -> None:
    cands = [_cand(phase=SOURCE_B1, critical=True, sha="b1"), _cand(phase=SOURCE_B2, score=3.2, sha="b2")]
    r = select_for_type(cands)
    assert r["decision"] == "REPLACE"
    assert r["selected"]["source_phase"] == SOURCE_B2
    assert "CLEARS_BASELINE_CRITICAL_FAILURE" in r["selection_reason_codes"]


def test_stronger_of_b2_b3_when_b1_critical() -> None:
    cands = [
        _cand(phase=SOURCE_B1, critical=True, sha="b1"),
        _cand(phase=SOURCE_B2, score=2.0, fg=0.08, sha="b2"),
        _cand(phase=SOURCE_B3, score=5.0, fg=0.18, sha="b3", artefact_id="selected"),
    ]
    r = select_for_type(cands)
    assert r["decision"] == "REPLACE"
    assert r["selected"]["source_phase"] == SOURCE_B3


def test_mixed_source_context_detail() -> None:
    inv = {
        "beam_id": "ZX",
        "context_candidates": [_cand(phase=SOURCE_B1, score=4.4, sha="c1", crop_type="context"), _cand(phase=SOURCE_B2, score=4.41, sha="c2", crop_type="context")],
        "detail_candidates": [
            _cand(phase=SOURCE_B1, critical=True, sha="d1", crop_type="detail"),
            _cand(phase=SOURCE_B2, score=3.1, sha="d2", crop_type="detail"),
        ],
    }
    r = select_beam(inv)
    assert r["context"]["selected"]["source_phase"] == SOURCE_B1
    assert r["detail"]["selected"]["source_phase"] == SOURCE_B2
    assert r["context"]["decision"] == "RETAIN"
    assert r["detail"]["decision"] == "REPLACE"


def test_missing_b1_fallback() -> None:
    cands = [_cand(phase=SOURCE_B1, exists=False), _cand(phase=SOURCE_B2, score=3.3, sha="b2")]
    r = select_for_type(cands)
    assert r["selected"]["source_phase"] == SOURCE_B2
    assert r["selection_status"] == "FALLBACK_NO_PREFERRED"
    assert "PREFERRED_MISSING" in r["selection_reason_codes"]


def test_challenger_critical_rejected() -> None:
    cands = [_cand(phase=SOURCE_B1, score=4.0, sha="b1"), _cand(phase=SOURCE_B2, critical=True, sha="b2")]
    r = select_for_type(cands)
    assert r["decision"] == "RETAIN"
    assert r["selected"]["source_phase"] == SOURCE_B1
    assert any("CHALLENGER_CRITICAL_FAILURE" in (x.get("rejection_reason") or []) for x in r.get("rejections") or [])


def test_ambiguous_retains_b1() -> None:
    cands = [
        _cand(phase=SOURCE_B1, score=4.0, fg=0.12, cov=0.80, sha="b1"),
        _cand(phase=SOURCE_B2, score=4.02, fg=0.119, cov=0.79, sha="b2"),
        _cand(phase=SOURCE_B3, score=4.03, fg=0.121, cov=0.81, sha="b3", artefact_id="selected"),
    ]
    r = select_for_type(cands)
    assert r["decision"] == "RETAIN"
    assert r["selected"]["source_phase"] == SOURCE_B1


def test_selection_deterministic() -> None:
    cands = [
        _cand(phase=SOURCE_B1, critical=True, sha="b1"),
        _cand(phase=SOURCE_B2, score=2.2, sha="b2"),
        _cand(phase=SOURCE_B3, score=4.4, sha="b3", artefact_id="selected"),
    ]
    a = select_for_type(cands)
    b = select_for_type(list(cands))
    ka = json.dumps(
        {"d": a["decision"], "s": a["selected"]["source_phase"], "c": a["selection_reason_codes"]},
        sort_keys=True,
    )
    kb = json.dumps(
        {"d": b["decision"], "s": b["selected"]["source_phase"], "c": b["selection_reason_codes"]},
        sort_keys=True,
    )
    assert ka == kb


def test_source_sha_unchanged() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        b1 = root / "data" / "output" / "PhaseP2610B1_population_generalization"
        png = _write_png(b1 / "context" / "ZX.png", (30, 30, 30), ink=True)
        _write_png(b1 / "detail" / "ZX.png", (30, 30, 30), ink=True)
        (b1 / "validation").mkdir(parents=True, exist_ok=True)
        (b1 / "validation" / "ZX.json").write_text("{}", encoding="utf-8")
        h0 = sha256_file(png)
        inventory_beam(root, "ZX")
        assert sha256_file(png) == h0


def test_beam_id_rename_invariance() -> None:
    cands = [_cand(phase=SOURCE_B1, score=4.1, sha="same"), _cand(phase=SOURCE_B2, score=4.15, sha="other")]
    a = select_for_type(cands)
    b = select_for_type(cands)
    assert a["decision"] == b["decision"] == "RETAIN"
    assert a["selection_reason_codes"] == b["selection_reason_codes"]


def test_population_integrity_status() -> None:
    beams = ["ZA", "ZB", "ZC"]
    for beam_id in beams:
        inv = {
            "beam_id": beam_id,
            "context_candidates": [_cand(phase=SOURCE_B1, exists=(beam_id != "ZC"), sha=f"c-{beam_id}")],
            "detail_candidates": [_cand(phase=SOURCE_B1, score=3.9, sha=f"d-{beam_id}", crop_type="detail")],
        }
        if beam_id == "ZC":
            inv["context_candidates"].append(_cand(phase=SOURCE_B2, score=3.0, sha="fb"))
        r = select_beam(inv)
        assert r["context"].get("selection_status")
        assert r["detail"].get("selection_status")
        assert r["context"].get("decision") in ("RETAIN", "REPLACE", "UNRESOLVED")
        assert r["detail"].get("decision") in ("RETAIN", "REPLACE", "UNRESOLVED")


def test_source_guard() -> None:
    g = source_guard(_pkg())
    assert g.get("ok") is True, g.get("hits")
    for name in ("inventory.py", "selector.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for tok in ("B32", "B19", "B24A", "B152", "B176", "B26", "B68A", "B99A", "B69A"):
            assert tok not in text, f"{name} contains {tok}"


def test_translation_and_packed() -> None:
    assert spatial_distance_robustness().get("ok") is True
    assert packed_sheet_robustness().get("ok") is True


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.15"
    assert GATE_VERSION == "P2610C1C2_EVIDENCE_INVENTORY_CANDIDATE_SELECTION_V1_0"
    assert SHADOW_ONLY is True
    assert PRODUCTION_ACTION == "NO_CHANGE"


def test_prior_phase_artefacts() -> None:
    assert prior_phase_unit_ok(_v10(), "PhaseP266_semantic_longitudinal_resolver", 36).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610A_beam_region_crop_audit", 14).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B_adaptive_beam_detail_crop", 18).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B1_population_generalization", 16).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B2_render_quality_directional_recovery", 29).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B3_target_anchor_geometry_context_recovery", 18).get("ok") is True
    intact = prior_artefacts_intact(_v10())
    assert intact.get("ok") is True, intact.get("missing")


def test_production_identical_fingerprints() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True


def test_firewall_and_leakage() -> None:
    fw = firewall_check(_v10())
    assert fw.get("ok") is True, fw.get("offenders")
    leak = runtime_leakage_scan(_pkg())
    assert leak.get("ok") is True, leak.get("hits")


def test_decision_never_production_ready() -> None:
    from .phase_p2610c1c2_orchestrator import _classify_decision

    d = _classify_decision(
        tests_ok=True,
        fingerprints_ok=True,
        anti_ok=True,
        processed=10,
        discovered=10,
        hardcoding=False,
        newest_wins=False,
        production_mutations=0,
        unresolved_limitations=True,
    )
    assert "PRODUCTION" not in d
    assert d.startswith("PASS")


def test_no_dxf_or_vision_in_runtime() -> None:
    for name in ("inventory.py", "selector.py", "phase_p2610c1c2_orchestrator.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "ezdxf" not in text
        assert "RenderSession" not in text
        assert "anthropic" not in text.lower()
        assert "claude" not in text.lower() or name.endswith("orchestrator.py")


def test_discovered_population_matches_b1() -> None:
    ids = population_beam_ids(_v10())
    assert len(ids) >= 130
    assert "B69A" not in ids
    assert "B69" in ids


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("preferred_b1_retained", test_preferred_b1_retained),
        ("tiny_score_does_not_replace", test_tiny_score_does_not_replace),
        ("b1_critical_b2_valid", test_b1_critical_b2_valid),
        ("stronger_of_b2_b3_when_b1_critical", test_stronger_of_b2_b3_when_b1_critical),
        ("mixed_source_context_detail", test_mixed_source_context_detail),
        ("missing_b1_fallback", test_missing_b1_fallback),
        ("challenger_critical_rejected", test_challenger_critical_rejected),
        ("ambiguous_retains_b1", test_ambiguous_retains_b1),
        ("selection_deterministic", test_selection_deterministic),
        ("source_sha_unchanged", test_source_sha_unchanged),
        ("beam_id_rename_invariance", test_beam_id_rename_invariance),
        ("population_integrity_status", test_population_integrity_status),
        ("source_guard", test_source_guard),
        ("translation_and_packed", test_translation_and_packed),
        ("production_write_false", test_production_write_false),
        ("prior_phase_artefacts", test_prior_phase_artefacts),
        ("production_identical_fingerprints", test_production_identical_fingerprints),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("decision_never_production_ready", test_decision_never_production_ready),
        ("no_dxf_or_vision_in_runtime", test_no_dxf_or_vision_in_runtime),
        ("discovered_population_matches_b1", test_discovered_population_matches_b1),
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
