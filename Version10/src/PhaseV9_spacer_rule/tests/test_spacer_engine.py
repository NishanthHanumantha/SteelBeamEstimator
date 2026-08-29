"""
Unit tests for Phase M.2 Spacer Bar Rule Engine.
Hand-computed vectors from ground-truth / frozen M.2 spec.
MODEL_VERSION: 9.2.0
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Allow `pytest` from repo root or package dir without install
_PKG = Path(__file__).resolve().parents[1]
_SRC = _PKG.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from PhaseV9_spacer_rule.spacer_engine import (  # noqa: E402
    COVER_FALLBACK_MM,
    SPACER_DIA_MM,
    SPACER_SPACING_MM,
    compute_overlap_zones,
    compute_spacers_for_beam,
    cut_length_mm,
    spacer_quantity,
)
from PhaseV9_spacer_rule.spacer_models import (  # noqa: E402
    BeamSpacerInput,
    LongitudinalGroup,
)


def _beam(
    beam_id: str,
    width: float,
    cover: float,
    groups: list,
    already: bool = False,
) -> BeamSpacerInput:
    return BeamSpacerInput(
        beam_id=beam_id,
        beam_width_mm=width,
        cover_mm=cover,
        groups=groups,
        already_has_spacer=already,
    )


def _g(role: str, face: str, start=None, end=None, clear=None) -> LongitudinalGroup:
    return LongitudinalGroup(
        role=role,
        face=face,
        start_mm=start,
        end_mm=end,
        clear_length_mm=clear,
        extent_confidence="HIGH" if start is not None else "MISSING",
    )


# ---------------------------------------------------------------------------
# Vector 1 — B2 single zone length 4000 → qty 5, cut 0.15 m
# ---------------------------------------------------------------------------
def test_b2_single_zone_qty5_cut150():
    beam = _beam(
        "B2", 250.0, 50.0,
        [
            _g("TOP_MAIN", "TOP", 0, 8000),
            _g("TOP_EXTRA", "TOP", 1000, 5000),  # overlap 4000
        ],
    )
    res = compute_spacers_for_beam(beam)
    assert len(res.rows) == 1
    assert res.rows[0].quantity == 5
    assert res.rows[0].cut_length_mm == 150.0
    assert res.rows[0].diameter_mm == 25
    assert res.rows[0].zone_length_mm == 4000.0


# ---------------------------------------------------------------------------
# Vector 2 — B4 two zones 3000 & 7000 → qty 4 and 8, two rows
# ---------------------------------------------------------------------------
def test_b4_two_zones_qty4_and_qty8():
    beam = _beam(
        "B4", 250.0, 50.0,
        [
            _g("BOTTOM_MAIN", "BOTTOM", 0, 12000),
            _g("BOTTOM_EXTRA", "BOTTOM", 0, 3000),
            _g("BOTTOM_EXTRA", "BOTTOM", 5000, 12000),  # overlap 7000 with main
        ],
    )
    res = compute_spacers_for_beam(beam)
    bottom = [r for r in res.rows if r.face == "BOTTOM"]
    assert len(bottom) == 2
    qtys = sorted(r.quantity for r in bottom)
    assert qtys == [4, 8]
    assert all(r.cut_length_mm == 150.0 for r in bottom)


# ---------------------------------------------------------------------------
# Vector 3 — W.18B: (2150/1000)+1 = 3.15 → round-half-up 3
# ---------------------------------------------------------------------------
def test_qty_2150_round_half_up_3():
    assert spacer_quantity(2150) == 3


# ---------------------------------------------------------------------------
# Vector 4 — exact multiple 3000 → qty 4
# ---------------------------------------------------------------------------
def test_exact_multiple_3000_qty4():
    assert spacer_quantity(3000) == 4
    assert math.floor(3.0 + 0.5) == 3  # 3000 mm → raw 4.0
    assert spacer_quantity(3000) == 4


# ---------------------------------------------------------------------------
# Vector 5 — face with single bar group → 0 spacers
# ---------------------------------------------------------------------------
def test_single_group_no_spacers():
    beam = _beam(
        "Sx", 250.0, 50.0,
        [_g("TOP_MAIN", "TOP", 0, 5000)],
    )
    res = compute_spacers_for_beam(beam)
    assert res.rows == []


# ---------------------------------------------------------------------------
# Vector 6 — face with main only (no extra) → 0
# ---------------------------------------------------------------------------
def test_main_only_no_spacers():
    beam = _beam(
        "Sy", 250.0, 50.0,
        [
            _g("TOP_MAIN", "TOP", 0, 5000),
            _g("BOTTOM_MAIN", "BOTTOM", 0, 5000),
        ],
    )
    res = compute_spacers_for_beam(beam)
    assert res.rows == []


# ---------------------------------------------------------------------------
# Vector 7 — stirrups/SFR alongside ONE longitudinal → 0
# ---------------------------------------------------------------------------
def test_stirrup_sfr_excluded():
    # Engine input only receives longitudinal groups from injector;
    # simulate a face that would have had stirrups filtered out → only 1 long.
    beam = _beam(
        "Sz", 250.0, 50.0,
        [_g("TOP_MAIN", "TOP", 0, 5000)],
    )
    res = compute_spacers_for_beam(beam)
    assert res.rows == []


# ---------------------------------------------------------------------------
# Vector 8 — three stacked bars → ONE zone (no double-emit)
# ---------------------------------------------------------------------------
def test_three_stacked_one_zone():
    # Main [0,10000], Extra1 [0,4000], Extra2 [1000,3500]
    # Overlap ≥2: [0,4000] only (one maximal zone)
    extents = [(0.0, 10000.0), (0.0, 4000.0), (1000.0, 3500.0)]
    zones = compute_overlap_zones(extents)
    assert len(zones) == 1
    assert zones[0] == (0.0, 4000.0)

    beam = _beam(
        "T3", 250.0, 50.0,
        [
            _g("TOP_MAIN", "TOP", 0, 10000),
            _g("TOP_EXTRA", "TOP", 0, 4000),
            _g("TOP_EXTRA", "TOP", 1000, 3500),
        ],
    )
    res = compute_spacers_for_beam(beam)
    top = [r for r in res.rows if r.face == "TOP"]
    assert len(top) == 1
    assert top[0].quantity == spacer_quantity(4000)


# ---------------------------------------------------------------------------
# Vector 9 — cut length width 250, cover 50 → 150 mm
# ---------------------------------------------------------------------------
def test_cut_length_150():
    assert cut_length_mm(250, 50) == 150.0


# ---------------------------------------------------------------------------
# Vector 10 — constants hardcoded; cover from context changes cut only
# ---------------------------------------------------------------------------
def test_constants_not_context_derived():
    assert SPACER_DIA_MM == 25
    assert SPACER_SPACING_MM == 1000
    # Inject fake cover 40 → cut changes; dia/spacing unchanged
    beam = _beam(
        "C10", 250.0, 40.0,
        [
            _g("TOP_MAIN", "TOP", 0, 5000),
            _g("TOP_EXTRA", "TOP", 0, 3000),
        ],
    )
    res = compute_spacers_for_beam(beam)
    assert len(res.rows) == 1
    assert res.rows[0].diameter_mm == 25
    assert res.rows[0].spacing_mm == 1000
    assert res.rows[0].cut_length_mm == 170.0  # 250 - 2*40
    assert res.rows[0].cover_mm == 40.0


# ---------------------------------------------------------------------------
# Vector 11 — extras without geometric extents are unresolved (no cut fallback)
# ---------------------------------------------------------------------------
def test_extent_fallback_not_cut_length():
    beam = _beam(
        "Fb", 250.0, 50.0,
        [
            _g("TOP_MAIN", "TOP", 0, 8000),
            _g("TOP_EXTRA", "TOP", start=None, end=None, clear=4000),
        ],
    )
    res = compute_spacers_for_beam(beam)
    assert res.rows == []
    assert any("cut_length_mm is not used" in w or "no geometric extra" in w for w in res.warnings)


# ---------------------------------------------------------------------------
# Vector 12 — dedup guard
# ---------------------------------------------------------------------------
def test_dedup_guard():
    beam = _beam(
        "Dup", 250.0, 50.0,
        [
            _g("TOP_MAIN", "TOP", 0, 5000),
            _g("TOP_EXTRA", "TOP", 0, 3000),
        ],
        already=True,
    )
    res = compute_spacers_for_beam(beam)
    assert res.skipped is True
    assert res.rows == []
    assert res.skip_reason == "already_has_spacer"


# ---------------------------------------------------------------------------
# Vector 13 — cover fallback 30 mm → cut 190 for width 250
# ---------------------------------------------------------------------------
def test_cover_fallback():
    beam = BeamSpacerInput(
        beam_id="Cov",
        beam_width_mm=250.0,
        cover_mm=None,
        groups=[
            _g("TOP_MAIN", "TOP", 0, 5000),
            _g("TOP_EXTRA", "TOP", 0, 3000),
        ],
    )
    res = compute_spacers_for_beam(beam)
    assert len(res.rows) == 1
    assert res.rows[0].cover_fallback is True
    assert res.rows[0].cover_mm == COVER_FALLBACK_MM
    assert res.rows[0].cut_length_mm == 190.0  # 250 - 2*30


def test_missing_width_skips():
    beam = BeamSpacerInput(
        beam_id="NoW",
        beam_width_mm=None,
        cover_mm=50.0,
        groups=[
            _g("TOP_MAIN", "TOP", 0, 5000),
            _g("TOP_EXTRA", "TOP", 0, 3000),
        ],
    )
    res = compute_spacers_for_beam(beam)
    assert res.skipped is True
    assert res.rows == []


def test_top_and_bottom_independent():
    beam = _beam(
        "TB", 250.0, 50.0,
        [
            _g("TOP_MAIN", "TOP", 0, 5000),
            _g("TOP_EXTRA", "TOP", 0, 3000),
            _g("BOTTOM_MAIN", "BOTTOM", 0, 5000),
            _g("BOTTOM_EXTRA", "BOTTOM", 0, 2000),
        ],
    )
    res = compute_spacers_for_beam(beam)
    faces = {r.face for r in res.rows}
    assert faces == {"TOP", "BOTTOM"}
    assert len(res.rows) == 2
