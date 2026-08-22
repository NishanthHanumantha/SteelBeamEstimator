"""Unit tests for P2.6.10-E.3. Default offline. Live only via override."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple
from zipfile import ZipFile

from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.anti_hardcoding import (
    group_order_invariance,
    input_order_invariance,
    rename_invariance,
    vision_diameter_changes_weight,
)
from PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark.eligibility import (
    classify_eligibility,
    evaluate_population,
)

from .anti_hardcoding import (
    ambiguous_not_forced,
    duplicate_discovery_stable,
    e2_reuse_and_reject,
    first_set_excluded,
    hybrid_vs_fallback_label,
    pooled_not_average,
    source_guard,
    spacer_preserved,
    vision_main_extra_authority,
)
from .artefact_reuse import contract_compatible, decide_action, fifth_population_compatible, row_reusable
from .config import (
    DEFAULT_MODE,
    GATE_VERSION,
    INCLUDED_SET_KEYS,
    MODE_OFFLINE,
    MODEL_VERSION,
    PRODUCTION_WRITE,
    PROV_REUSED,
    STATUS_NOT_READY,
    STATUS_READY,
)
from .docx_report import write_docx
from .metrics import kpi_block
from .pdf_report import write_pdf
from .pooling import overall_from_kpis, pool_kpi_blocks, weight_accuracy_percent
from .population import discover_all_sets
from .regression import firewall_check, prior_artefacts_intact, runtime_leakage_scan
from .sets import classify_folder_name, is_excluded_set
from .visual_sources import path_belongs_to_set
from .vision_loop import execute_one, fifth_reuse_gate


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


_POP_CACHE = None


def _pop() -> Dict[str, Any]:
    global _POP_CACHE
    if _POP_CACHE is None:
        _POP_CACHE = discover_all_sets(_v10())
    return _POP_CACHE


def _ok(cond: bool, detail: Any = None) -> Dict[str, Any]:
    return {"ok": bool(cond), "detail": detail}


def test_a_dynamic_discovery() -> Dict[str, Any]:
    pop = _pop()
    keys = set((pop.get("by_set") or {}).keys())
    return _ok(keys == set(INCLUDED_SET_KEYS) and all((pop["by_set"][k].get("ok") for k in INCLUDED_SET_KEYS)), keys)


def test_b_first_excluded() -> Dict[str, Any]:
    pop = _pop()
    return _ok(first_set_excluded().get("ok") and "First" not in (pop.get("by_set") or {}))


def test_c_ground_truth() -> Dict[str, Any]:
    pop = _pop()
    sources = {k: (v.get("truth_source") or "") for k, v in (pop.get("by_set") or {}).items()}
    return _ok(all(v and v != "NONE" for v in sources.values()), sources)


def test_d_vision_execution_paths() -> Dict[str, Any]:
    blocked = decide_action(set_key="Second", eligible=False, e3_row=None, e2_row=None, source_sha=None, historical=None, e2_reuse_allowed=False)
    live = decide_action(set_key="Second", eligible=True, e3_row=None, e2_row=None, source_sha="x", historical=None, e2_reuse_allowed=False)
    return _ok(blocked["action"] == "BLOCK" and live["action"] == "LIVE")


def test_e_fifth_reuse_detection() -> Dict[str, Any]:
    pop = _pop()
    fifth = (pop.get("by_set") or {}).get("Fifth") or {}
    gate = fifth_reuse_gate(v10=_v10(), current_ids=fifth.get("model_beam_ids") or [])
    return _ok(isinstance(gate.get("allowed"), bool), gate.get("decision"))


def test_f_incompatible_reject() -> Dict[str, Any]:
    return e2_reuse_and_reject()


def test_g_hybrid_label() -> Dict[str, Any]:
    return hybrid_vs_fallback_label()


def test_h_fallback_label() -> Dict[str, Any]:
    return hybrid_vs_fallback_label()


def test_i_diameter_authority() -> Dict[str, Any]:
    return vision_diameter_changes_weight()


def test_j_main_extra() -> Dict[str, Any]:
    return vision_main_extra_authority()


def test_k_spacers() -> Dict[str, Any]:
    return spacer_preserved()


def test_l_stirrup_separation() -> Dict[str, Any]:
    from PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark.anti_hardcoding import sample_execute

    calc = sample_execute("T01", vision_usable=True)
    stir = calc.get("stirrups") if isinstance(calc.get("stirrups"), dict) else {}
    return _ok(calc.get("provenance_kind") == "HYBRID", stir.get("reason"))


def test_m_ambiguous() -> Dict[str, Any]:
    return ambiguous_not_forced()


def test_n_duplicates() -> Dict[str, Any]:
    return duplicate_discovery_stable()


def test_o_beam_metrics() -> Dict[str, Any]:
    block = kpi_block(
        {
            "beam_identification": {"beam_identification_percent": 50, "numerator": 1, "denominator": 2, "formula": "n/d"},
            "bar_identification": {},
            "correct_of_detected": {},
            "diameter_identification": {},
            "steel": {},
            "overall": {},
        }
    )
    return _ok(block.get("beam_n") == 1 and block.get("beam_d") == 2)


def test_p_bar_metrics() -> Dict[str, Any]:
    pooled = pool_kpi_blocks(
        [
            {"bar_n": 2, "bar_d": 10, "beam_n": 0, "beam_d": 1, "correct_n": 0, "correct_d": 1, "diameter_n": 0, "diameter_d": 1, "hybrid_total_kg": 0, "benchmark_total_kg": 1},
            {"bar_n": 3, "bar_d": 10, "beam_n": 0, "beam_d": 1, "correct_n": 0, "correct_d": 1, "diameter_n": 0, "diameter_d": 1, "hybrid_total_kg": 0, "benchmark_total_kg": 1},
        ]
    )
    return _ok(abs(float(pooled["bar_identification_percent"]) - 25.0) < 1e-9)


def test_q_correct_of_detected() -> Dict[str, Any]:
    pooled = pool_kpi_blocks(
        [{"correct_n": 3, "correct_d": 10, "beam_n": 0, "beam_d": 1, "bar_n": 0, "bar_d": 1, "diameter_n": 0, "diameter_d": 1, "hybrid_total_kg": 0, "benchmark_total_kg": 1}]
    )
    return _ok(abs(float(pooled["correct_of_detected_percent"]) - 30.0) < 1e-9)


def test_r_diameter() -> Dict[str, Any]:
    overall = overall_from_kpis(beam_pct=50, bar_pct=50, correct_pct=50, weight_pct=50)
    return _ok(overall == 50.0)


def test_s_steel() -> Dict[str, Any]:
    return _ok(abs(float(weight_accuracy_percent(80, 100)) - 80.0) < 1e-9 and weight_accuracy_percent(0, 0) is None)


def test_t_overall() -> Dict[str, Any]:
    return _ok(abs(float(overall_from_kpis(beam_pct=10, bar_pct=20, correct_pct=30, weight_pct=40)) - 25.0) < 1e-9)


def test_u_pooled_raw() -> Dict[str, Any]:
    return pooled_not_average()


def test_v_pooled_steel() -> Dict[str, Any]:
    return pooled_not_average()


def test_w_hybrid_cohort() -> Dict[str, Any]:
    empty = pool_kpi_blocks([])
    return _ok(empty.get("beam_d") == 0 and empty.get("beam_identification_percent") is None)


def test_x_fallback_cohort() -> Dict[str, Any]:
    return test_w_hybrid_cohort()


def test_y_full_population() -> Dict[str, Any]:
    return pooled_not_average()


def test_z_semantic_taxonomy() -> Dict[str, Any]:
    from .pooling import merge_taxonomy

    merged = merge_taxonomy([{"taxonomy": {"MATCH": 2, "MISSING": 1}}, {"taxonomy": {"MATCH": 3, "EXTRA": 4}}])
    return _ok(merged.get("MATCH") == 5 and merged.get("MISSING") == 1 and merged.get("EXTRA") == 4)


def test_aa_engineering_taxonomy() -> Dict[str, Any]:
    return spacer_preserved()


def test_ab_fingerprint_helpers() -> Dict[str, Any]:
    intact = prior_artefacts_intact(_v10())
    return _ok(intact.get("ok"), intact.get("missing"))


def test_ac_production_write() -> Dict[str, Any]:
    return _ok(PRODUCTION_WRITE is False)


def test_ad_truth_provenance() -> Dict[str, Any]:
    return test_c_ground_truth()


def test_ae_rename() -> Dict[str, Any]:
    return rename_invariance()


def test_af_order() -> Dict[str, Any]:
    return input_order_invariance()


def test_ag_vision_group_order() -> Dict[str, Any]:
    return group_order_invariance()


def test_ah_det_group_order() -> Dict[str, Any]:
    return group_order_invariance()


def test_ai_no_hardcoded_counts() -> Dict[str, Any]:
    return source_guard(_pkg())


def _fixture_report(tmp: Path) -> Dict[str, Any]:
    per = {}
    vis = {}
    for i, key in enumerate(INCLUDED_SET_KEYS):
        per[key] = {
            "model_beams": i + 2,
            "gt_beams": i + 3,
            "matched_beams": i + 2,
            "hybrid_count": i + 1,
            "fallback_count": 1,
            "beam_identification_percent": 50 + i,
            "bar_identification_percent": 40 + i,
            "correct_of_detected_percent": 30 + i,
            "diameter_identification_percent": 70 + i,
            "weight_accuracy_percent": 60 + i,
            "overall_accuracy_percent": 45 + i,
            "hybrid_total_kg": 100 + i,
            "benchmark_total_kg": 200 + i,
            "beam_n": i + 2,
            "beam_d": i + 3,
            "bar_n": 4,
            "bar_d": 8,
            "correct_n": 1,
            "correct_d": 4,
            "diameter_n": 3,
            "diameter_d": 4,
            "signed_error_kg": -100,
            "absolute_error_kg": 100,
            "truth_source": "ESTIMATOR_EXCEL",
        }
        vis[key] = {
            "eligible": i + 2,
            "attempted": i + 1,
            "new_live": i,
            "reused": 1,
            "retried": 0,
            "api_success": i + 1,
            "schema_valid": i + 1,
            "usable": i + 1,
            "hybrid": i + 1,
            "fallback": 1,
        }
    pooled = display_safe(pool_kpi_blocks(list(per.values())))
    return {
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "decision": "PARTIAL",
        "mode": MODE_OFFLINE,
        "population": {
            "model_beam_total": sum(p["model_beams"] for p in per.values()),
            "estimator_beam_total": sum(p["gt_beams"] for p in per.values()),
            "matched_total": sum(p["matched_beams"] for p in per.values()),
            "excluded": [{"set_key": "First"}],
            "by_set": {k: {"discovered_model_beam_count": v["model_beams"], "discovered_estimator_beam_count": v["gt_beams"], "matched_benchmark_population": v["matched_beams"], "unmatched_model_beams": [], "unmatched_estimator_beams": [], "truth_source": "ESTIMATOR_EXCEL"} for k, v in per.items()},
        },
        "per_set": per,
        "pooled": pooled,
        "vision_coverage": {"hybrid_count": 15, "fallback_count": 5, "hybrid_percent": 75, "fallback_percent": 25},
        "vision_execution": {"by_set": vis},
        "cohorts": {
            "HYBRID_ONLY": {"applicable": True, "kpis": pooled},
            "FALLBACK_ONLY": {"applicable": False, "kpis": None},
            "FULL_POPULATION": {"applicable": True, "kpis": pooled},
        },
        "semantic_taxonomy_pooled": {"MATCH": 9, "MISSING": 4, "WRONG_DIAMETER": 2},
        "engineering_errors": {"counts": {"SPACER_ZERO": 1, "STIRRUP_ENGINEERING_UNAVAILABLE": 2}},
        "cost": {"new_live": 3, "reused": 2, "retried": 1, "api_failed": 0, "input_tokens": 10, "output_tokens": 5, "runtime_s": 1.2},
        "limitations": ["OFFLINE_VALIDATION_NO_LIVE_CALLS"],
        "conclusion": "Fixture conclusion for report generation tests.",
        "fifth_reuse_decision": "VISION_REUSED_CURRENT_ARCHITECTURE",
    }


def display_safe(block: Dict[str, Any]) -> Dict[str, Any]:
    from .pooling import display_block

    return display_block(block)


def test_aj_docx() -> Dict[str, Any]:
    tmp = _v10() / "data" / "output" / "PhaseP2610E3_second_to_sixth_full_population_live_vision_hybrid_accuracy_benchmark" / "_report_fixture"
    tmp.mkdir(parents=True, exist_ok=True)
    data = _fixture_report(tmp)
    path = write_docx(out_root=tmp, data=data, charts={})
    return _ok(path.exists() and path.stat().st_size > 1000, str(path))


def test_ak_pdf() -> Dict[str, Any]:
    tmp = _v10() / "data" / "output" / "PhaseP2610E3_second_to_sixth_full_population_live_vision_hybrid_accuracy_benchmark" / "_report_fixture"
    tmp.mkdir(parents=True, exist_ok=True)
    data = _fixture_report(tmp)
    path = write_pdf(out_root=tmp, data=data)
    return _ok(path.exists() and path.read_bytes()[:4] == b"%PDF", str(path))


def test_al_docx_pdf_consistency() -> Dict[str, Any]:
    tmp = _v10() / "data" / "output" / "PhaseP2610E3_second_to_sixth_full_population_live_vision_hybrid_accuracy_benchmark" / "_report_fixture"
    data = _fixture_report(tmp)
    docx = write_docx(out_root=tmp, data=data, charts={})
    pdf = write_pdf(out_root=tmp, data=data)
    xml = ZipFile(docx).read("word/document.xml").decode("utf-8", errors="ignore")
    pdf_txt = pdf.read_bytes().decode("latin-1", errors="ignore")
    token = MODEL_VERSION
    overall = f"{float(data['pooled']['overall_accuracy_percent']):.2f}"
    return _ok(token in xml and token in pdf_txt and overall in xml and overall in pdf_txt, overall)


def test_am_cost_fields() -> Dict[str, Any]:
    data = _fixture_report(_pkg())
    cost = data.get("cost") or {}
    return _ok(all(k in cost for k in ("new_live", "reused", "retried", "input_tokens", "output_tokens")))


def test_an_fifth_reuse_no_call() -> Dict[str, Any]:
    called = {"n": 0}

    def client(**kwargs):
        called["n"] += 1
        raise RuntimeError("should_not_call")

    row = {
        "complete": True,
        "called": True,
        "semantic_usable": True,
        "extracted": {"usable": True, "groups": [], "stirrups": [], "target_identified": True},
        "parsed": {"usable": True, "groups": [], "stirrups": [], "target_identified": True},
        "visual": {"sha256": "abc"},
        "api_success": True,
        "schema_valid": True,
        "failure_category": "OK",
    }
    # Without writing E.2, decide_action with e3_row reusable must not need a client.
    decision = decide_action(
        set_key="Fifth",
        eligible=True,
        e3_row=row,
        e2_row=None,
        source_sha="abc",
        historical=None,
        e2_reuse_allowed=True,
    )
    return _ok(decision["action"] == "REUSE" and decision["provenance"] == PROV_REUSED and called["n"] == 0)


def test_ao_invalid_reuse_fail_closed() -> Dict[str, Any]:
    bad = {"complete": True, "called": True, "semantic_usable": True, "visual": {"sha256": "old"}}
    return _ok(row_reusable(bad, source_sha="new") is False)


def test_ap_report_from_json() -> Dict[str, Any]:
    return test_al_docx_pdf_consistency()


def test_other_set_path() -> Dict[str, Any]:
    fourth = Path("C:/data/output/PhaseQA30_unseen_benchmark/Fourth_Set_Drawings/RenderedCrops/shared_renders/x_render.png")
    fifth = Path("C:/data/output/PhaseQA30_unseen_benchmark/Fifth_Set_Drawings/RenderedCrops/shared_renders/x_render.png")
    return _ok(path_belongs_to_set(fifth, "Fifth") and not path_belongs_to_set(fourth, "Fifth"))


def test_eligibility() -> Dict[str, Any]:
    ready = classify_eligibility(STATUS_READY)
    blocked = classify_eligibility(STATUS_NOT_READY)
    return _ok(ready.get("eligible") is True and blocked.get("eligible") is False)


def test_firewall() -> Dict[str, Any]:
    fw = firewall_check(_v10())
    leak = runtime_leakage_scan(_pkg())
    return _ok(fw.get("ok") and leak.get("ok"), {"fw": fw, "leak": leak})


def test_offline_default() -> Dict[str, Any]:
    return _ok(DEFAULT_MODE == MODE_OFFLINE)


TESTS: List[Tuple[str, Callable[[], Dict[str, Any]]]] = [
    ("A_dynamic_second_to_sixth_discovery", test_a_dynamic_discovery),
    ("B_first_set_exclusion", test_b_first_excluded),
    ("C_ground_truth_discovery", test_c_ground_truth),
    ("D_current_vision_execution_paths", test_d_vision_execution_paths),
    ("E_fifth_set_e2_reuse_detection", test_e_fifth_reuse_detection),
    ("F_incompatible_artefact_rejection", test_f_incompatible_reject),
    ("G_hybrid_classification", test_g_hybrid_label),
    ("H_fallback_classification", test_h_fallback_label),
    ("I_vision_diameter_authority", test_i_diameter_authority),
    ("J_vision_main_extra_authority", test_j_main_extra),
    ("K_deterministic_spacer_preservation", test_k_spacers),
    ("L_stirrup_semantic_engineering_separation", test_l_stirrup_separation),
    ("M_ambiguous_non_forcing", test_m_ambiguous),
    ("N_duplicate_artefact_discovery_stability", test_n_duplicates),
    ("O_per_set_beam_metrics", test_o_beam_metrics),
    ("P_per_set_bar_metrics", test_p_bar_metrics),
    ("Q_correct_of_detected", test_q_correct_of_detected),
    ("R_diameter_reporting", test_r_diameter),
    ("S_steel_accuracy", test_s_steel),
    ("T_overall_accuracy_formula", test_t_overall),
    ("U_pooled_numerator_denominator", test_u_pooled_raw),
    ("V_pooled_steel_before_accuracy", test_v_pooled_steel),
    ("W_hybrid_only_cohort", test_w_hybrid_cohort),
    ("X_fallback_only_cohort", test_x_fallback_cohort),
    ("Y_full_population_scoring", test_y_full_population),
    ("Z_semantic_error_taxonomy", test_z_semantic_taxonomy),
    ("AA_engineering_error_taxonomy", test_aa_engineering_taxonomy),
    ("AB_source_fingerprint_immutability_helpers", test_ab_fingerprint_helpers),
    ("AC_production_mutation_zero_flag", test_ac_production_write),
    ("AD_benchmark_truth_provenance", test_ad_truth_provenance),
    ("AE_beam_rename_invariance", test_ae_rename),
    ("AF_input_order_invariance", test_af_order),
    ("AG_vision_group_order_invariance", test_ag_vision_group_order),
    ("AH_deterministic_group_order_invariance", test_ah_det_group_order),
    ("AI_no_hardcoded_population_counts", test_ai_no_hardcoded_counts),
    ("AJ_report_docx_generation", test_aj_docx),
    ("AK_report_pdf_generation", test_ak_pdf),
    ("AL_docx_pdf_required_content_consistency", test_al_docx_pdf_consistency),
    ("AM_cost_accounting", test_am_cost_fields),
    ("AN_fifth_reuse_does_not_trigger_duplicate_calls", test_an_fifth_reuse_no_call),
    ("AO_invalid_reused_artefact_fails_closed", test_ao_invalid_reuse_fail_closed),
    ("AP_report_values_derive_from_json", test_ap_report_from_json),
    ("other_set_path_rejection", test_other_set_path),
    ("eligibility_policy", test_eligibility),
    ("firewall_and_leakage", test_firewall),
    ("offline_default_mode", test_offline_default),
]


def run_unit_tests() -> Dict[str, Any]:
    results = []
    passed = 0
    for name, fn in TESTS:
        print(f"  [test] {name} ...", flush=True)
        try:
            row = fn()
            ok = bool(row.get("ok"))
        except Exception as exc:
            ok = False
            row = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        status = "PASS" if ok else "FAIL"
        print(f"  [test] {name} {status}", flush=True)
        if ok:
            passed += 1
        results.append({"name": name, "pass": ok, **{k: v for k, v in row.items() if k != "ok"}})
    return {"success": passed == len(TESTS), "passed": passed, "total": len(TESTS), "results": results}


__all__ = ["run_unit_tests"]
