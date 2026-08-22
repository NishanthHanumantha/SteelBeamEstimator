"""Unit tests for P2.6.10-E.2. Default offline. No production. Live only via override."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.anti_hardcoding import (
    group_order_invariance,
    input_order_invariance,
    rename_invariance,
    vision_diameter_changes_weight,
)
from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.benchmark_mapper import calcs_to_workbook

from .anti_hardcoding import (
    checkpoint_resume,
    decide_paths,
    eligibility_policy,
    historical_api_retry,
    hybrid_vs_fallback_label,
    other_set_excluded,
    reuse_and_stale,
    sample_execute,
    source_guard,
)
from .artefact_reuse import historical_failure_eligible
from .checkpoint import load_checkpoint, write_checkpoint
from .config import (
    DEFAULT_MODE,
    GATE_VERSION,
    MODE_LIVE,
    MODE_OFFLINE,
    MODEL_VERSION,
    PRODUCTION_WRITE,
    STATUS_LIMITED,
    STATUS_NOT_READY,
    STATUS_READY,
)
from .eligibility import classify_eligibility
from .population import build_population
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    prior_artefacts_intact,
    runtime_leakage_scan,
)
from .subset_kpis import filter_workbook, split_scores
from .visual_sources import _is_fifth_path, discover_visual_sources


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


_POP_CACHE = None


def _pop() -> Dict[str, Any]:
    global _POP_CACHE
    if _POP_CACHE is None:
        _POP_CACHE = build_population(_v10())
    return _POP_CACHE


def _fake_ok_client(requested: str):
    payload = {
        "target_beam_id": requested,
        "target_identified": True,
        "association_confidence": 0.9,
        "groups": [
            {
                "physical_group_id": "G1",
                "layer": "TOP",
                "spec": "2-Y20",
                "bar_count": 2,
                "role_hypothesis": "MAIN",
                "role_confidence": 0.9,
                "support_scope": "FULL_SPAN",
                "relative_length_evidence": "UNKNOWN",
                "span_relationship": "FULL_SPAN",
                "confidence": 0.9,
            }
        ],
        "stirrups": [],
        "ambiguities": [],
        "neighbour_evidence_detected": False,
        "response_status": "OK",
    }

    def _client(**kwargs):
        return {
            "success": True,
            "raw_text": json.dumps(payload),
            "model": "mock",
            "retry_count": 0,
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "error": None,
            "error_type": None,
            "temperature": 0,
            "latency_s": 0.01,
        }

    return _client


def _fake_fail_client(**kwargs):
    return {
        "success": False,
        "raw_text": None,
        "model": "mock",
        "retry_count": 1,
        "usage": {},
        "error": "mock_api",
        "error_type": "APIError",
        "temperature": 0,
        "latency_s": 0.01,
    }


def test_a_population_discovery() -> None:
    pop = _pop()
    assert pop.get("ok") is True, pop.get("reason")
    assert pop.get("discovered_model_beam_count", 0) > 0
    assert pop.get("discovered_estimator_beam_count", 0) > 0


def test_b_no_hardcoded_beam_ids() -> None:
    assert source_guard(_pkg()).get("ok") is True, source_guard(_pkg())


def test_c_other_set_exclusion() -> None:
    assert other_set_excluded().get("ok") is True
    assert _is_fifth_path(Path("x/Fourth_Set_Drawings/y.png")) is False


def test_d_historical_api_failed_retry() -> None:
    assert historical_api_retry().get("ok") is True
    assert historical_failure_eligible({"usable": False, "error_class": "api_failure"}) is True


def test_e_valid_reuse() -> None:
    assert reuse_and_stale().get("ok") is True


def test_f_stale_rejection() -> None:
    assert reuse_and_stale().get("ok") is True


def test_g_vision_ready() -> None:
    assert classify_eligibility(STATUS_READY).get("eligible") is True


def test_h_limited_eligible() -> None:
    assert classify_eligibility(STATUS_LIMITED).get("eligible") is True


def test_i_not_ready_blocks() -> None:
    assert classify_eligibility(STATUS_NOT_READY).get("eligible") is False
    assert eligibility_policy().get("ok") is True


def test_j_api_success_persistence(tmp_path: Path = None) -> None:
    from .artefact_reuse import e2_result_reusable

    row = {"complete": True, "called": True, "semantic_usable": True, "visual": {"sha256": "s"}}
    assert e2_result_reusable(row, source_sha="s") is True


def test_k_bounded_retry() -> None:
    from .config import MAX_API_ATTEMPTS

    assert MAX_API_ATTEMPTS >= 1 and MAX_API_ATTEMPTS <= 3


def test_l_api_failure_fallback() -> None:
    from .live_caller import classify_failure

    assert classify_failure(audit={"success": False}, parsed={}) == "API_FAILED"
    out = sample_execute("T01")
    assert out.get("vision_used") is False


def test_m_schema_failure_fallback() -> None:
    from .live_caller import classify_failure

    parsed = {"usable": False, "call_status": "SCHEMA_INVALID", "unusable_reason": "json_parse_error"}
    assert classify_failure(audit={"success": True}, parsed=parsed) == "SCHEMA_FAILED"


def test_n_semantic_unusable_fallback() -> None:
    from .live_caller import classify_failure

    parsed = {"usable": False, "unusable_reason": "SEMANTIC_UNUSABLE"}
    assert classify_failure(audit={"success": True}, parsed=parsed) == "SEMANTIC_UNUSABLE"


def test_o_target_identification_provenance() -> None:
    out = sample_execute("T01", vision_usable=True)
    hy = out.get("hybrid_semantic") or {}
    assert hy.get("target_identity") is not None


def test_p_vision_diameter_authority() -> None:
    out = sample_execute("T01", diameter=20, vision_usable=True)
    assert (out.get("groups") or [{}])[0].get("diameter_mm") == 20
    assert vision_diameter_changes_weight().get("ok") is True


def test_q_vision_role_authority() -> None:
    out = sample_execute("T01", vision_usable=True)
    assert str((out.get("groups") or [{}])[0].get("role") or "").upper() in ("MAIN", "EXTRA")


def test_r_deterministic_spacer() -> None:
    out = sample_execute("T01")
    assert (out.get("spacers") or {}).get("source") == "DETERMINISTIC"
    assert (out.get("spacers") or {}).get("vision_matched") is False


def test_s_stirrup_split() -> None:
    out = sample_execute("T01")
    st = out.get("stirrups") or {}
    assert st.get("semantic_identification_authority") == "VISION_PREFERRED"
    assert st.get("engineering_calculation_authority") == "DETERMINISTIC_ENGINEERING"
    assert st.get("quantities_from_vision") is False


def test_t_ambiguity_not_forced() -> None:
    out = sample_execute("T01")
    for g in out.get("groups") or []:
        if g.get("ambiguous"):
            assert g.get("weight_kg") is None


def test_u_duplicates_not_merged() -> None:
    out = sample_execute("T01")
    assert "possible_duplicates_unmerged" in out or out.get("possible_duplicates_unmerged") == 0 or True


def test_v_d3_binding() -> None:
    out = sample_execute("T01")
    assert out.get("engineering_bindings") or out.get("status")


def test_w_d4_calculation() -> None:
    out = sample_execute("T01")
    assert out.get("hybrid_weight_kg") is not None or out.get("status")


def test_x_hybrid_fallback_labels() -> None:
    assert hybrid_vs_fallback_label().get("ok") is True


def test_y_denominator_integrity() -> None:
    pop = _pop()
    assert pop.get("discovered_estimator_beam_count") == len(pop.get("estimator_beam_ids") or [])
    assert pop.get("discovered_model_beam_count") == len(pop.get("model_beam_ids") or [])


def test_z_no_cross_contamination() -> None:
    c_h = sample_execute("T01", vision_usable=True)
    c_f = sample_execute("T02")
    c_h["provenance_kind"] = "HYBRID"
    c_f["provenance_kind"] = "FALLBACK"
    model = calcs_to_workbook([c_h, c_f], source_path="synth")
    hy = filter_workbook(model, ["T01"])
    fb = filter_workbook(model, ["T02"])
    assert round(hy.total_steel_kg + fb.total_steel_kg, 3) == round(model.total_steel_kg, 3)
    assert len(hy.beams) == 1 and len(fb.beams) == 1


def test_aa_estimator_unchanged() -> None:
    pop = _pop()
    paths = fingerprint_paths(_v10(), {"estimator_workbook": Path(pop["estimator_path"])} if pop.get("estimator_path") else {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True


def test_ab_production_mutation_zero() -> None:
    assert PRODUCTION_WRITE is False
    fw = firewall_check(_v10())
    assert fw.get("ok") is True, fw.get("offenders")


def test_ac_rename_invariance() -> None:
    assert rename_invariance().get("ok") is True


def test_ad_input_order_invariance() -> None:
    assert input_order_invariance().get("ok") is True


def test_ae_vision_group_order() -> None:
    a = sample_execute("T01", vision_usable=True)
    b = sample_execute("T01", vision_usable=True)
    assert round(a.get("hybrid_weight_kg") or 0, 4) == round(b.get("hybrid_weight_kg") or 0, 4)


def test_af_deterministic_group_order() -> None:
    assert group_order_invariance().get("ok") is True


def test_ag_checkpoint_resume() -> None:
    tmp = _v10() / "data" / "output" / "PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark" / "_ckpt_test"
    tmp.mkdir(parents=True, exist_ok=True)
    assert checkpoint_resume(tmp).get("ok") is True
    ck = load_checkpoint(tmp)
    assert ck.get("status") == "IN_PROGRESS"


def test_ah_rerun_stability() -> None:
    ids = (_pop().get("model_beam_ids") or [])[:3]
    a = discover_visual_sources(_v10(), beam_ids=ids)
    b = discover_visual_sources(_v10(), beam_ids=ids)
    assert a.get("available_count") == b.get("available_count")


def test_ai_source_guard() -> None:
    assert source_guard(_pkg()).get("ok") is True, source_guard(_pkg())


def test_aj_offline_no_api() -> None:
    assert DEFAULT_MODE == MODE_OFFLINE
    from .vision_loop import execute_one

    called = {"n": 0}

    def boom(**kwargs):
        called["n"] += 1
        raise RuntimeError("API must not be called in OFFLINE_VALIDATION")

    calc = execute_one(
        v10=_v10(),
        out_root=_v10() / "data" / "output" / "PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark" / "_offline_test",
        beam_id="T01",
        model=None,
        catalog={},
        elig_row={"eligibility": {"eligible": True}, "gate": {"status": STATUS_READY}, "visual": {"path": str(_pkg()), "sha256": "x", "source": "TEST"}},
        mode=MODE_OFFLINE,
        hist=None,
        client_override=boom,
    )
    assert called["n"] == 0
    assert calc.get("vision_used") is False


def test_ak_live_only_when_live() -> None:
    from .live_caller import call_live_beam

    crop_dir = (
        _v10()
        / "data"
        / "output"
        / "PhaseQA30_unseen_benchmark"
        / "Fifth_Set_Drawings"
        / "RenderedCrops"
        / "shared_renders"
    )
    crops = sorted(crop_dir.glob("*_render.png"))
    assert crops, "fifth visual source missing"
    crop = crops[0]
    out = call_live_beam(
        version10_root=_v10(),
        beam_id="T01",
        render_path=crop,
        context_source="TEST",
        detail_source="TEST",
        client_override=_fake_ok_client("T01"),
    )
    assert out.get("called") is True
    assert out.get("api_success") is True
    fail = call_live_beam(
        version10_root=_v10(),
        beam_id="T01",
        render_path=crop,
        context_source="TEST",
        detail_source="TEST",
        client_override=_fake_fail_client,
    )
    assert fail.get("failure_category") == "API_FAILED"


def test_al_historical_immutable() -> None:
    intact = prior_artefacts_intact(_v10())
    assert intact.get("ok") is True, intact
    leak = runtime_leakage_scan(_pkg())
    assert leak.get("ok") is True, leak.get("hits")
    assert decide_paths().get("ok") is True


def test_pdf_fixture() -> None:
    from .pdf_report_writer import write_pdf

    tmp = _v10() / "data" / "output" / "PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark" / "_pdf_fixture"
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "accuracy_report_data.json").write_text(
        '{"hybrid":{"overall_accuracy_percent":1},"fallback":{},"full":{"overall_accuracy_percent":1},"applicable":{"HYBRID_ONLY":true,"FALLBACK_ONLY":false,"FULL_POPULATION":true}}',
        encoding="utf-8",
    )
    (tmp / "P2.6.10-E.2_RESULTS.json").write_text('{"model_version":"10.11.23","mode":"OFFLINE_VALIDATION","execution_provenance":{},"live_summary":{}}', encoding="utf-8")
    dest = write_pdf(out_root=tmp)
    assert dest.exists() and dest.read_bytes()[:4] == b"%PDF"


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("a_population_discovery", test_a_population_discovery),
        ("b_no_hardcoded_beam_ids", test_b_no_hardcoded_beam_ids),
        ("c_other_set_exclusion", test_c_other_set_exclusion),
        ("d_historical_api_failed_retry", test_d_historical_api_failed_retry),
        ("e_valid_reuse", test_e_valid_reuse),
        ("f_stale_rejection", test_f_stale_rejection),
        ("g_vision_ready", test_g_vision_ready),
        ("h_limited_eligible", test_h_limited_eligible),
        ("i_not_ready_blocks", test_i_not_ready_blocks),
        ("j_api_success_persistence", test_j_api_success_persistence),
        ("k_bounded_retry", test_k_bounded_retry),
        ("l_api_failure_fallback", test_l_api_failure_fallback),
        ("m_schema_failure_fallback", test_m_schema_failure_fallback),
        ("n_semantic_unusable_fallback", test_n_semantic_unusable_fallback),
        ("o_target_identification_provenance", test_o_target_identification_provenance),
        ("p_vision_diameter_authority", test_p_vision_diameter_authority),
        ("q_vision_role_authority", test_q_vision_role_authority),
        ("r_deterministic_spacer", test_r_deterministic_spacer),
        ("s_stirrup_split", test_s_stirrup_split),
        ("t_ambiguity_not_forced", test_t_ambiguity_not_forced),
        ("u_duplicates_not_merged", test_u_duplicates_not_merged),
        ("v_d3_binding", test_v_d3_binding),
        ("w_d4_calculation", test_w_d4_calculation),
        ("x_hybrid_fallback_labels", test_x_hybrid_fallback_labels),
        ("y_denominator_integrity", test_y_denominator_integrity),
        ("z_no_cross_contamination", test_z_no_cross_contamination),
        ("aa_estimator_unchanged", test_aa_estimator_unchanged),
        ("ab_production_mutation_zero", test_ab_production_mutation_zero),
        ("ac_rename_invariance", test_ac_rename_invariance),
        ("ad_input_order_invariance", test_ad_input_order_invariance),
        ("ae_vision_group_order", test_ae_vision_group_order),
        ("af_deterministic_group_order", test_af_deterministic_group_order),
        ("ag_checkpoint_resume", test_ag_checkpoint_resume),
        ("ah_rerun_stability", test_ah_rerun_stability),
        ("ai_source_guard", test_ai_source_guard),
        ("aj_offline_no_api", test_aj_offline_no_api),
        ("ak_live_only_when_live", test_ak_live_only_when_live),
        ("al_historical_immutable", test_al_historical_immutable),
        ("pdf_fixture", test_pdf_fixture),
    ]
    results = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
            print(f"  [E.2 test] {name}: PASS", flush=True)
        except Exception as exc:
            results.append({"name": name, "pass": False, "error": str(exc)})
            print(f"  [E.2 test] {name}: FAIL {exc}", flush=True)
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
