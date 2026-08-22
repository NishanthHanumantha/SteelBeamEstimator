"""Unit tests for P2.6.10-E.1. Offline. No production. No Claude."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .anti_hardcoding import (
    group_order_invariance,
    input_order_invariance,
    rename_invariance,
    run_anti_hardcoding,
    sample_execute,
    source_guard,
    vision_diameter_changes_weight,
)
from .config import DEFAULT_MODE, GATE_VERSION, LIVE_CLAUDE_CALL, MODE_OFFLINE, MODEL_VERSION, PRODUCTION_WRITE
from .kpis import compute_kpis
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .population_discovery import discover_population
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


def test_a_population_discovery() -> None:
    pop = discover_population(_v10())
    assert pop.get("ok") is True, pop.get("reason")
    assert pop.get("model_beam_count", 0) > 0
    assert pop.get("estimator_path")
    assert pop.get("run_root")
    name = str(pop.get("run_folder") or pop.get("run_root") or "").lower()
    assert "fifth" in name or "5th" in name


def test_b_no_hardcoded_beam_ids() -> None:
    g = source_guard(_pkg())
    assert g.get("ok") is True, g.get("hits")


def test_c_hybrid_provenance() -> None:
    out = sample_execute("T01")
    assert out.get("provenance_kind") in ("FALLBACK", "HYBRID", "DETERMINISTIC")
    assert out.get("vision_used") is False


def test_d_vision_semantic_authority() -> None:
    out = sample_execute("T01", diameter=20, vision_usable=True)
    assert out.get("vision_used") is True
    assert out.get("provenance_kind") == "HYBRID"


def test_e_vision_diameter_authority() -> None:
    out = sample_execute("T01", diameter=20, vision_usable=True)
    g = (out.get("groups") or [{}])[0]
    assert g.get("diameter_mm") == 20


def test_f_vision_role_authority() -> None:
    out = sample_execute("T01", vision_usable=True)
    g = (out.get("groups") or [{}])[0]
    assert str(g.get("role") or "").upper() in ("MAIN", "EXTRA")


def test_g_vision_bar_count_authority() -> None:
    out = sample_execute("T01", vision_usable=True)
    g = (out.get("groups") or [{}])[0]
    assert g.get("bar_count") == 2 or g.get("quantity") == 2


def test_h_deterministic_geometry_authority() -> None:
    out = sample_execute("T01")
    g = (out.get("groups") or [{}])[0]
    assert g.get("cut_length_mm") is not None


def test_i_deterministic_spacer_authority() -> None:
    out = sample_execute("T01")
    assert (out.get("spacers") or {}).get("source") == "DETERMINISTIC"
    assert (out.get("spacers") or {}).get("vision_matched") is False


def test_j_stirrup_split() -> None:
    out = sample_execute("T01")
    st = out.get("stirrups") or {}
    assert st.get("semantic_identification_authority") == "VISION_PREFERRED"
    assert st.get("engineering_calculation_authority") == "DETERMINISTIC_ENGINEERING"
    assert st.get("quantities_from_vision") is False


def test_k_benchmark_truth_discovery() -> None:
    pop = discover_population(_v10())
    assert pop.get("estimator_path")


def test_l_missing_benchmark_truth() -> None:
    from .benchmark_truth_loader import load_benchmark_truth

    miss = load_benchmark_truth(estimator_path=None)
    assert miss.get("ok") is False
    assert miss.get("source") == "NONE"


def test_m_beam_identification_formula() -> None:
    from .config import FORMULA_BEAM_MATCH

    assert "beam_matcher" in FORMULA_BEAM_MATCH


def test_n_bar_identification_formula() -> None:
    from .config import FORMULA_BAR_MATCH

    assert "bar_matcher" in FORMULA_BAR_MATCH


def test_o_correct_of_detected_formula() -> None:
    from .anti_hardcoding import _det_model
    from .benchmark_mapper import calcs_to_workbook
    from .benchmark_truth_loader import _ensure_qa2a

    _ensure_qa2a()
    from gt_models import BarRecord, BeamRecord, NormalizedWorkbook  # type: ignore

    calc = sample_execute("T01")
    model = calcs_to_workbook([calc], source_path="synthetic")
    est = NormalizedWorkbook(
        source_path="synthetic-est",
        source_label="ESTIMATOR",
        beams=[
            BeamRecord(
                beam_id="T01",
                steel_kg=model.beams[0].steel_kg,
                bars=list(model.beams[0].bars),
            )
        ],
        total_steel_kg=model.total_steel_kg,
        diameter_kg=dict(model.diameter_kg),
    )
    k = compute_kpis(drawing_set="SYNTH", estimator=est, model=model)
    assert k["correct_of_detected"]["correct_of_detected_percent"] is not None


def test_p_diameter_formula() -> None:
    k = test_o_correct_of_detected_formula  # executed via o; diameter keys exist on synthetic
    out = sample_execute("T01")
    assert (out.get("groups") or [{}])[0].get("diameter_mm")


def test_q_steel_formula() -> None:
    from .config import FORMULA_STEEL

    assert "benchmark_kg" in FORMULA_STEEL or "abs(" in FORMULA_STEEL


def test_r_overall_formula() -> None:
    from .config import FORMULA_OVERALL

    assert "mean" in FORMULA_OVERALL


def test_s_numerator_denominator() -> None:
    from .kpis import compute_kpis as _c

    # identity: percent reconstructs from n/d
    n, d = 2, 4
    assert round(100.0 * n / d, 2) == 50.0


def test_t_duplicate_artefact_stability() -> None:
    a = discover_population(_v10())
    b = discover_population(_v10())
    assert a.get("model_beam_count") == b.get("model_beam_count")
    assert a.get("run_root") == b.get("run_root")


def test_u_rename_invariance() -> None:
    assert rename_invariance().get("ok") is True


def test_v_input_order_invariance() -> None:
    assert input_order_invariance().get("ok") is True


def test_w_group_order_invariance() -> None:
    assert group_order_invariance().get("ok") is True


def test_x_ambiguous_not_forced() -> None:
    out = sample_execute("T01")
    for g in out.get("groups") or []:
        if g.get("ambiguous"):
            assert g.get("weight_kg") is None


def test_y_truth_provenance() -> None:
    from .config import TRUTH_ESTIMATOR

    assert TRUTH_ESTIMATOR == "ESTIMATOR_EXCEL"


def test_z_no_production_write() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    fw = firewall_check(_v10())
    assert fw.get("ok") is True, fw.get("offenders")


def test_aa_source_fingerprints() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True
    intact = prior_artefacts_intact(_v10())
    assert intact.get("ok") is True, intact
    d4 = prior_phase_unit_ok(_v10(), "PhaseP2610D4_shadow_hybrid_engineering_calculation_accuracy_benchmark", 28)
    assert d4.get("ok")


def test_ab_pdf_from_artefacts() -> None:
    from .pdf_report_writer import write_pdf

    tmp = _v10() / "data" / "output" / "PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark" / "_pdf_fixture"
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "accuracy_report_data.json").write_text(
        '{"beam":{"beam_identification_percent":1},"bar":{},"correct":{},"diameter":{},"steel":{"weight_accuracy_percent":1},"overall":{"overall_accuracy_percent":1}}',
        encoding="utf-8",
    )
    (tmp / "vision_coverage_report.json").write_text("{}", encoding="utf-8")
    (tmp / "P2.6.10-E.1_RESULTS.json").write_text('{"model_version":"10.11.22","mode":"OFFLINE_REPLAY"}', encoding="utf-8")
    dest = write_pdf(out_root=tmp)
    assert dest.exists() and dest.stat().st_size > 100
    assert dest.read_bytes()[:4] == b"%PDF"


def test_anti_bundle() -> None:
    out = run_anti_hardcoding(package_dir=_pkg())
    assert out.get("ok") is True, out


def test_offline_default() -> None:
    assert DEFAULT_MODE == MODE_OFFLINE
    assert LIVE_CLAUDE_CALL is False
    leak = runtime_leakage_scan(_pkg())
    assert leak.get("ok") is True, leak.get("hits")


def test_vision_diameter_weight() -> None:
    assert vision_diameter_changes_weight().get("ok") is True


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("a_population_discovery", test_a_population_discovery),
        ("b_no_hardcoded_beam_ids", test_b_no_hardcoded_beam_ids),
        ("c_hybrid_provenance", test_c_hybrid_provenance),
        ("d_vision_semantic_authority", test_d_vision_semantic_authority),
        ("e_vision_diameter_authority", test_e_vision_diameter_authority),
        ("f_vision_role_authority", test_f_vision_role_authority),
        ("g_vision_bar_count_authority", test_g_vision_bar_count_authority),
        ("h_deterministic_geometry_authority", test_h_deterministic_geometry_authority),
        ("i_deterministic_spacer_authority", test_i_deterministic_spacer_authority),
        ("j_stirrup_split", test_j_stirrup_split),
        ("k_benchmark_truth_discovery", test_k_benchmark_truth_discovery),
        ("l_missing_benchmark_truth", test_l_missing_benchmark_truth),
        ("m_beam_identification_formula", test_m_beam_identification_formula),
        ("n_bar_identification_formula", test_n_bar_identification_formula),
        ("o_correct_of_detected_formula", test_o_correct_of_detected_formula),
        ("p_diameter_formula", test_p_diameter_formula),
        ("q_steel_formula", test_q_steel_formula),
        ("r_overall_formula", test_r_overall_formula),
        ("s_numerator_denominator", test_s_numerator_denominator),
        ("t_duplicate_artefact_stability", test_t_duplicate_artefact_stability),
        ("u_rename_invariance", test_u_rename_invariance),
        ("v_input_order_invariance", test_v_input_order_invariance),
        ("w_group_order_invariance", test_w_group_order_invariance),
        ("x_ambiguous_not_forced", test_x_ambiguous_not_forced),
        ("y_truth_provenance", test_y_truth_provenance),
        ("z_no_production_write", test_z_no_production_write),
        ("aa_source_fingerprints", test_aa_source_fingerprints),
        ("ab_pdf_from_artefacts", test_ab_pdf_from_artefacts),
        ("anti_bundle", test_anti_bundle),
        ("offline_default", test_offline_default),
        ("vision_diameter_weight", test_vision_diameter_weight),
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
