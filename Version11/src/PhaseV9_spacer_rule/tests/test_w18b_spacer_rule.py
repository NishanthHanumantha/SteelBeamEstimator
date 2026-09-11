"""
W.18B spacer-rule regression tests.

Estimator rules: geometric overlap only, round-half-up quantity,
CONTINUOUS+LEFT+RIGHT piece-representation dedupe, BBS aggregation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2]
_VB1 = _SRC / "PhaseVB.1_production_output_completion"
_R13 = _SRC / "PhaseR1.3_pipeline_integration"
for _p in (_SRC, _VB1, _R13):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from PhaseV9_spacer_rule.r13_injector import inject_spacers, _bar_to_group
from PhaseV9_spacer_rule.spacer_engine import (
    SPACER_DIA_MM,
    SPACER_SPACING_MM,
    aggregate_equivalent_spacer_rows,
    compute_spacers_for_beam,
    cut_length_mm,
    round_half_up,
    spacer_quantity,
    spacer_raw_quantity,
)
from PhaseV9_spacer_rule.spacer_models import BeamSpacerInput, LongitudinalGroup
from production_output_models import (
    BarSteelWeight,
    BeamSteelWeight,
    ProjectSteelSummary,
)
from bbs_completion_engine import BBSCompletionEngine

import importlib.util
import types


def _load_r13():
    pkg_name = "PhaseR13W18B"
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(_R13)]
        pkg.__package__ = pkg_name
        sys.modules[pkg_name] = pkg
    for sub in ("engineering_bar_model", "engineering_bar_builder"):
        key = f"{pkg_name}.{sub}"
        if key in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(key, _R13 / f"{sub}.py")
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = pkg_name
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return (
        sys.modules[f"{pkg_name}.engineering_bar_builder"].EngineeringBarBuilder,
        sys.modules[f"{pkg_name}.engineering_bar_model"].EngineeringBarModel,
        sys.modules[f"{pkg_name}.engineering_bar_model"].BeamEngineeringModel,
    )


EngineeringBarBuilder, EngineeringBarModel, BeamEngineeringModel = _load_r13()


def _g(
    role: str,
    face: str,
    start=None,
    end=None,
    *,
    piece_type: str = "",
    bar_label: str = "",
    diameter_mm: float = 16.0,
    clear=None,
) -> LongitudinalGroup:
    return LongitudinalGroup(
        role=role,
        face=face,
        start_mm=start,
        end_mm=end,
        clear_length_mm=clear if clear is not None else (
            (end - start) if start is not None and end is not None else None
        ),
        extent_confidence="HIGH" if start is not None else "MISSING",
        piece_type=piece_type,
        bar_label=bar_label,
        diameter_mm=diameter_mm,
    )


def _beam(beam_id: str, width: float, cover: float, groups: list, span=None) -> BeamSpacerInput:
    return BeamSpacerInput(
        beam_id=beam_id,
        beam_width_mm=width,
        cover_mm=cover,
        groups=groups,
        clear_span_mm=span,
    )


def _eng_bar(
    beam_id: str,
    role: str,
    dia: float,
    qty: int,
    label: str,
    *,
    piece_type: str = "",
    start=None,
    end=None,
    cut=None,
    zone: str = "TOP_ZONE",
) -> EngineeringBarModel:
    return EngineeringBarModel(
        beam_id=beam_id,
        bar_role=role,
        diameter_mm=dia,
        quantity=qty,
        zone=zone,
        bar_label=label,
        source_phase="R.1.3",
        engineering_metadata={
            "piece_type": piece_type,
            "piece_start_mm": start,
            "piece_end_mm": end,
            "cut_length_mm": cut,
            "piece_id": f"PCE::{beam_id}::{label}",
            "detail_id": f"DET::{beam_id}::{label}",
        },
    )


def test_w18b_qty_1040_is_2():
    raw = spacer_raw_quantity(1040)
    assert abs(raw - 2.04) < 1e-9
    assert spacer_quantity(1040) == 2
    assert round_half_up(2.04) == 2


def test_w18b_qty_1500_is_3():
    raw = spacer_raw_quantity(1500)
    assert abs(raw - 2.50) < 1e-9
    assert spacer_quantity(1500) == 3
    assert round_half_up(2.50) == 3


def test_w18b_qty_half_up_boundaries():
    assert spacer_quantity(2490) == 3
    assert spacer_quantity(2500) == 4
    assert round_half_up(3.5) == 4


def test_w18b_single_layer_zero_spacers():
    res = compute_spacers_for_beam(_beam(
        "F", 200.0, 30.0, [_g("TOP_MAIN", "TOP", 0, 4000)], span=4000,
    ))
    assert res.rows == []


def test_w18b_two_mains_no_extra_zero_spacers():
    res = compute_spacers_for_beam(_beam(
        "G", 200.0, 30.0,
        [
            _g("TOP_MAIN", "TOP", 0, 4000, diameter_mm=16, bar_label="2-Y16"),
            _g("TOP_MAIN", "TOP", 0, 4000, diameter_mm=20, bar_label="2-Y20"),
        ],
        span=4000,
    ))
    assert res.rows == []


def test_w18b_cut_width_minus_2cover():
    assert cut_length_mm(200.0, 30.0) == 140.0
    assert SPACER_DIA_MM == 25
    assert SPACER_SPACING_MM == 1000
    res = compute_spacers_for_beam(_beam(
        "H", 200.0, 30.0,
        [
            _g("TOP_MAIN", "TOP", 0, 4000),
            _g("TOP_EXTRA", "TOP", 0, 1040, piece_type="TOP_EXTRA_LEFT"),
        ],
        span=4000,
    ))
    assert res.rows
    assert all(r.cut_length_mm == 140.0 for r in res.rows)
    assert all(r.diameter_mm == 25 for r in res.rows)


def test_w18b_stacked_identical_extents_not_collapsed():
    res = compute_spacers_for_beam(_beam(
        "J", 250.0, 50.0,
        [
            _g("TOP_MAIN", "TOP", 0, 8000, diameter_mm=20, bar_label="2Y20"),
            _g("TOP_EXTRA", "TOP", 0, 8000, diameter_mm=16, bar_label="2Y16",
               piece_type="CONTINUOUS_BAR"),
        ],
        span=8000,
    ))
    assert len(res.rows) == 1
    assert res.rows[0].zone_length_mm == pytest.approx(8000.0)
    assert res.rows[0].quantity == spacer_quantity(8000)


def _b1_groups() -> list:
    span = 4158.3
    left_end = span * 0.25
    right_start = span * 0.75
    return [
        _g("TOP_MAIN", "TOP", 0, span, piece_type="TOP_MAIN",
           bar_label="2-Y20", diameter_mm=20),
        _g("TOP_EXTRA", "TOP", 0, span, piece_type="CONTINUOUS_BAR",
           bar_label="2-Y16", diameter_mm=16),
        _g("TOP_EXTRA", "TOP", 0, left_end, piece_type="TOP_EXTRA_LEFT",
           bar_label="2-Y16#L", diameter_mm=16),
        _g("TOP_EXTRA", "TOP", right_start, span, piece_type="TOP_EXTRA_RIGHT",
           bar_label="2-Y16#R", diameter_mm=16),
    ]


def test_w18b_b1_zones_not_3_7_3():
    span = 4158.3
    res = compute_spacers_for_beam(_beam("B1", 200.0, 30.0, _b1_groups(), span=span))
    qtys = sorted(r.quantity for r in res.rows)
    assert 7 not in qtys
    assert qtys != [3, 3, 7]
    assert len(res.rows) == 2
    assert all(r.quantity == 2 for r in res.rows)
    assert all(abs(r.zone_length_mm - span * 0.25) < 1.0 for r in res.rows)
    assert all(not r.extent_fallback for r in res.rows)


def test_w18b_b1_aggregate_one_line_qty4():
    span = 4158.3
    res = compute_spacers_for_beam(_beam("B1", 200.0, 30.0, _b1_groups(), span=span))
    agg = aggregate_equivalent_spacer_rows(res.rows)
    assert len(agg) == 1
    assert agg[0].quantity == 4
    assert agg[0].cut_length_mm == 140.0
    assert len(agg[0].component_zones) == 2


def test_w18b_b1_inject_and_l2_one_spacer():
    span = 4158.3
    left_end = span * 0.25
    right_start = span * 0.75
    beam = BeamEngineeringModel(
        beam_id="B1",
        beam_name="B1",
        geometry={"width_mm": 200.0, "depth_mm": 750.0, "clear_span_mm": span},
        bars=[
            _eng_bar("B1", "TOP_MAIN", 20, 2, "2-Y20", piece_type="TOP_MAIN",
                     start=0, end=span, cut=6358.3),
            _eng_bar("B1", "TOP_EXTRA", 16, 2, "2-Y16", piece_type="CONTINUOUS_BAR",
                     start=0, end=span, cut=5918.3),
            _eng_bar("B1", "TOP_EXTRA", 16, 2, "2Y16#L", piece_type="TOP_EXTRA_LEFT",
                     start=0, end=left_end, cut=2799.6),
            _eng_bar("B1", "TOP_EXTRA", 16, 2, "2Y16#R", piece_type="TOP_EXTRA_RIGHT",
                     start=right_start, end=span, cut=2799.6),
        ],
    )
    out, _report = inject_spacers([beam], 30.0, bar_model_cls=EngineeringBarModel)
    spacers = [b for b in out[0].bars if b.bar_role == "SPACER_BAR"]
    assert len(spacers) == 1
    assert spacers[0].quantity == 4
    assert spacers[0].diameter_mm == 25
    meta = spacers[0].engineering_metadata
    assert meta.get("extent_fallback") is False
    assert len(meta.get("zones") or []) == 2
    assert meta.get("cut_length_mm") == 140.0
    assert all(z["zone_length_mm"] != 5918.3 for z in meta["zones"])

    builder = EngineeringBarBuilder.__new__(EngineeringBarBuilder)
    builder._ctx = {"cover_beam_mm": 30}
    l2 = builder.to_l2_compatible(out)
    rec = l2["models"][0]
    long_bar = rec["top_main_bars"][0]
    assert "piece_start_mm" in long_bar
    assert long_bar["piece_start_mm"] == 0
    sp = rec["spacer_bars"]
    assert len(sp) == 1
    assert sp[0]["quantity"] == 4
    assert sp[0]["zone_length_mm"] is not None
    assert sp[0]["zones"]
    assert sp[0]["extent_fallback"] is False


def test_w18b_b10_left_right_not_hooked_cut():
    span = 2656.6
    left_end = span * 0.25
    hooked_cut = 2424.2
    res = compute_spacers_for_beam(_beam(
        "B10", 600.0, 30.0,
        [
            _g("TOP_MAIN", "TOP", 0, span, piece_type="TOP_MAIN",
               bar_label="5Y20", diameter_mm=20),
            _g("TOP_EXTRA", "TOP", 0, left_end, piece_type="TOP_EXTRA_LEFT",
               bar_label="5-Y16", diameter_mm=16),
            _g("TOP_EXTRA", "TOP", span * 0.75, span, piece_type="TOP_EXTRA_RIGHT",
               bar_label="5-Y16", diameter_mm=16),
        ],
        span=span,
    ))
    assert len(res.rows) == 2
    assert all(abs(r.zone_length_mm - left_end) < 1.0 for r in res.rows)
    assert all(abs(r.zone_length_mm - hooked_cut) > 100 for r in res.rows)
    assert all(r.quantity == 2 for r in res.rows)
    agg = aggregate_equivalent_spacer_rows(res.rows)
    assert len(agg) == 1
    assert agg[0].quantity == 4
    assert agg[0].cut_length_mm == 540.0


def test_w18b_b23_lr_zones_not_hooked_cut():
    span = 7800.351
    hooked_cut = 3710.1
    res = compute_spacers_for_beam(_beam(
        "B23", 600.0, 30.0,
        [
            _g("TOP_MAIN", "TOP", 0, span, piece_type="TOP_MAIN",
               bar_label="5-Y20", diameter_mm=20),
            _g("TOP_EXTRA", "TOP", 0, span * 0.25, piece_type="TOP_EXTRA_LEFT",
               bar_label="5Y16#L", diameter_mm=16),
            _g("TOP_EXTRA", "TOP", span * 0.75, span, piece_type="TOP_EXTRA_RIGHT",
               bar_label="5Y16#R", diameter_mm=16),
        ],
        span=span,
    ))
    assert len(res.rows) == 2
    assert all(abs(r.zone_length_mm - hooked_cut) > 100 for r in res.rows)
    assert all(r.quantity == 3 for r in res.rows)
    agg = aggregate_equivalent_spacer_rows(res.rows)
    assert len(agg) == 1
    assert agg[0].quantity == 6


def test_w18b_cut_length_never_used_as_overlap_by_injector():
    bar = _eng_bar(
        "X", "TOP_EXTRA", 16, 2, "2Y16",
        piece_type="TOP_EXTRA_LEFT", start=None, end=None, cut=5918.3,
    )
    g = _bar_to_group(bar, span_mm=4158.3)
    assert g is not None
    assert g.has_extent() is False
    assert g.clear_length_mm is None


def test_w18b_bbs_aggregates_equivalent_spacers():
    def _sw(qty, bar_id):
        return BarSteelWeight(
            bar_id=bar_id, beam_id="B1", role="SPACER", bar_label="SPACER 25@1000",
            diameter_mm=25, quantity=qty, steel_grade="Y",
            cut_length_mm=140.0, cut_length_source="SpacerRuleEngine_M.2",
            area_mm2=1.0, weight_per_bar_kg=0.1, total_weight_kg=0.1 * qty,
            formula_used="test",
        )
    proj = ProjectSteelSummary(
        total_weight_kg=0.4,
        beam_weights=[BeamSteelWeight(
            beam_id="B1", beam_name="B1", span_mm=4158.3,
            depth_mm=750.0, width_mm=200.0,
            bar_weights=[_sw(2, "L"), _sw(2, "R")],
            total_weight_kg=0.4,
            weight_by_diameter={25: 0.4},
        )],
        diameter_summary=[],
        total_bars=2,
        total_beams=1,
    )
    rows = BBSCompletionEngine(proj, frame_type="GF").generate()
    spacer_rows = [r for r in rows if not r.is_beam_header and r.description == "Spacer bars"]
    assert len(spacer_rows) == 1
    assert spacer_rows[0].quantity == 4
    assert spacer_rows[0].cut_length_m == pytest.approx(0.140)


def test_w18b_r12b_merge_preserves_piece_extents():
    """R.1.2B duplicate merge must not drop piece_start_mm / piece_end_mm."""
    import importlib.util
    import types

    r12b = _SRC / "PhaseR1_2B_engineeringbar_consolidation"
    pkg_name = "PhaseR12BW18B"
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(r12b)]
        pkg.__package__ = pkg_name
        sys.modules[pkg_name] = pkg
    for sub in (
        "physical_reinforcement_model",
        "engineeringbar_duplicate_detector",
        "engineeringbar_consolidator",
    ):
        key = f"{pkg_name}.{sub}"
        if key in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(key, r12b / f"{sub}.py")
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = pkg_name
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    EngineeringBarConsolidator = sys.modules[
        f"{pkg_name}.engineeringbar_consolidator"
    ].EngineeringBarConsolidator

    def _bar(label, start, end, idx_meta=""):
        return {
            "beam_id": "B10",
            "bar_role": "TOP_EXTRA",
            "diameter_mm": 16.0,
            "quantity": 5,
            "zone": "LEFT_SUPPORT",
            "bar_label": label,
            "steel_grade": "Y",
            "engineering_metadata": {
                "piece_type": "TOP_EXTRA_LEFT",
                "piece_start_mm": start,
                "piece_end_mm": end,
                "cut_length_mm": 2424.2,
                "piece_id": f"PCE::B10::{idx_meta}",
            },
        }

    models = [{"beam_id": "B10", "bars": [
        _bar("5Y16#L", 0.0, 664.15, "0007"),
        _bar("5Y16#L", 0.0, 664.15, "dup"),
    ]}]
    out, _ = EngineeringBarConsolidator().consolidate(models)
    bars = out[0]["bars"]
    assert bars
    meta = bars[0].get("engineering_metadata") or {}
    assert meta.get("piece_start_mm") == 0.0
    assert abs(float(meta.get("piece_end_mm")) - 664.15) < 1e-6
    assert abs(float(meta.get("cut_length_mm")) - 2424.2) < 1e-6
    assert meta.get("piece_start_mm") != meta.get("cut_length_mm")
