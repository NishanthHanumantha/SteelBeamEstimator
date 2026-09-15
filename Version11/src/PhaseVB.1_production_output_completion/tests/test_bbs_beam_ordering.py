"""V11.1 BBS drawing-order tests. Presentation layer only — no quantity logic."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

from bbs_beam_ordering import (  # noqa: E402
    BeamPosition,
    apply_bbs_drawing_order,
    assert_bbs_invariants,
    bbs_row_identity,
    order_beam_ids,
    reorder_bbs_rows,
)
from production_output_models import BBSRow  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "galera_gf_vroot1_centroids.json"


def _header(beam_id: str, si: int, kg: float = 10.0) -> BBSRow:
    return BBSRow(
        si_no=si,
        frame_type="GF",
        description=beam_id,
        diameter_mm=1,
        spacing_m=4.0,
        quantity=200,
        dvlp_length_m=0.75,
        cut_length_m=None,
        total_length_m=None,
        total_weight_kg=kg,
        is_beam_header=True,
        beam_id=beam_id,
    )


def _item(beam_id: str, desc: str, dia: float, qty: int, cut: float, kg: float) -> BBSRow:
    return BBSRow(
        si_no=None,
        frame_type="GF",
        description=desc,
        diameter_mm=dia,
        spacing_m=None,
        quantity=qty,
        dvlp_length_m=0.5,
        cut_length_m=cut,
        total_length_m=cut * qty,
        total_weight_kg=kg,
        is_beam_header=False,
        beam_id=beam_id,
        weight_d16=kg if int(dia) == 16 else None,
    )


def _group(beam_id: str, si: int) -> list:
    return [
        _header(beam_id, si, kg=12.5),
        _item(beam_id, "Top bars", 16, 3, 4.2, 6.0),
        _item(beam_id, "Bottom bars", 16, 3, 4.1, 5.8),
        _item(beam_id, "Stirrups", 8, 40, 1.2, 0.7),
    ]


class BbsBeamOrderingTests(unittest.TestCase):
    def test_01_left_to_right_same_row(self):
        positions = {
            "B_A": BeamPosition("B_A", 100.0, 500.0, "test"),
            "B_B": BeamPosition("B_B", 200.0, 500.0, "test"),
            "B_C": BeamPosition("B_C", 300.0, 500.0, "test"),
        }
        ordered, trace = order_beam_ids(["B_C", "B_A", "B_B"], positions)
        self.assertEqual(ordered, ["B_A", "B_B", "B_C"])
        self.assertEqual(len(trace.rows), 1)

    def test_02_multiple_drawing_rows_top_to_bottom(self):
        positions = {
            "B_A": BeamPosition("B_A", 100.0, 800.0, "test"),
            "B_B": BeamPosition("B_B", 200.0, 800.0, "test"),
            "B_C": BeamPosition("B_C", 100.0, 100.0, "test"),
            "B_D": BeamPosition("B_D", 200.0, 100.0, "test"),
        }
        ordered, trace = order_beam_ids(["B_D", "B_A", "B_C", "B_B"], positions)
        self.assertEqual(ordered, ["B_A", "B_B", "B_C", "B_D"])
        self.assertEqual(len(trace.rows), 2)

    def test_03_reversed_dxf_y_convention(self):
        # Image-like: larger Y is visually lower. Visual top is Y=100.
        positions = {
            "B_TOP_L": BeamPosition("B_TOP_L", 10.0, 100.0, "test"),
            "B_TOP_R": BeamPosition("B_TOP_R", 90.0, 100.0, "test"),
            "B_BOT_L": BeamPosition("B_BOT_L", 10.0, 900.0, "test"),
            "B_BOT_R": BeamPosition("B_BOT_R", 90.0, 900.0, "test"),
        }
        up, _ = order_beam_ids(
            list(positions), positions, y_increases_visually_up=True
        )
        down, _ = order_beam_ids(
            list(positions), positions, y_increases_visually_up=False
        )
        self.assertEqual(up, ["B_BOT_L", "B_BOT_R", "B_TOP_L", "B_TOP_R"])
        self.assertEqual(down, ["B_TOP_L", "B_TOP_R", "B_BOT_L", "B_BOT_R"])

    def test_04_within_beam_content_preserved(self):
        rows = _group("A", 1) + _group("B", 2)
        positions = {
            "A": BeamPosition("A", 200.0, 10.0, "test"),
            "B": BeamPosition("B", 100.0, 10.0, "test"),
        }
        out, _ = apply_bbs_drawing_order(rows, positions=positions)
        a_after = [r for r in out if r.beam_id == "A"]
        self.assertEqual(
            [bbs_row_identity(r) for r in a_after],
            [bbs_row_identity(r) for r in _group("A", 1)],
        )
        self.assertEqual([r.description for r in a_after[1:]], [
            "Top bars", "Bottom bars", "Stirrups"
        ])

    def test_05_value_preservation(self):
        rows = _group("B11", 1) + _group("B5", 2) + _group("B8", 3)
        positions = {
            "B5": BeamPosition("B5", 10.0, 50.0, "test"),
            "B8": BeamPosition("B8", 20.0, 50.0, "test"),
            "B11": BeamPosition("B11", 30.0, 50.0, "test"),
        }
        out, _ = apply_bbs_drawing_order(rows, positions=positions)
        assert_bbs_invariants(rows, out)
        self.assertEqual([r.beam_id for r in out if r.is_beam_header], ["B5", "B8", "B11"])
        self.assertEqual(
            sum(r.total_weight_kg or 0 for r in rows),
            sum(r.total_weight_kg or 0 for r in out),
        )
        before_items = [
            (r.beam_id, r.diameter_mm, r.quantity, r.cut_length_m, r.total_weight_kg)
            for r in rows if not r.is_beam_header
        ]
        after_items = [
            (r.beam_id, r.diameter_mm, r.quantity, r.cut_length_m, r.total_weight_kg)
            for r in out if not r.is_beam_header
        ]
        self.assertEqual(sorted(before_items), sorted(after_items))

    def test_06_complete_group_preservation_no_loss_or_dup(self):
        rows = _group("X", 1) + _group("Y", 2) + _group("Z", 3)
        positions = {
            "Z": BeamPosition("Z", 1.0, 9.0, "test"),
            "X": BeamPosition("X", 2.0, 9.0, "test"),
            "Y": BeamPosition("Y", 3.0, 1.0, "test"),
        }
        out, _ = apply_bbs_drawing_order(rows, positions=positions)
        self.assertEqual(len(out), len(rows))
        self.assertEqual(len({id(r) for r in out}), len(out))
        self.assertEqual(
            sorted(r.beam_id for r in out if r.is_beam_header),
            ["X", "Y", "Z"],
        )
        for bid in ("X", "Y", "Z"):
            self.assertEqual(sum(1 for r in out if r.beam_id == bid), 4)

    def test_07_determinism(self):
        positions = {
            "B_A": BeamPosition("B_A", 100.0, 800.0, "test"),
            "B_B": BeamPosition("B_B", 200.0, 800.0, "test"),
            "B_C": BeamPosition("B_C", 150.0, 100.0, "test"),
        }
        first, _ = order_beam_ids(["B_C", "B_B", "B_A"], positions)
        second, _ = order_beam_ids(["B_C", "B_B", "B_A"], positions)
        third, _ = order_beam_ids(["B_A", "B_C", "B_B"], positions)
        self.assertEqual(first, second)
        self.assertEqual(first, third)

    def test_08_missing_geometry_fallback(self):
        positions = {
            "B_A": BeamPosition("B_A", 10.0, 50.0, "test"),
            "B_B": BeamPosition("B_B", 20.0, 50.0, "test"),
        }
        ordered, trace = order_beam_ids(["B_UNK", "B_B", "B_A"], positions)
        self.assertEqual(ordered, ["B_A", "B_B", "B_UNK"])
        self.assertEqual(trace.missing_geometry_beam_ids, ["B_UNK"])
        self.assertEqual(trace.fallback, "APPEND_ORIGINAL_ORDER")

    def test_08b_all_missing_keeps_original(self):
        ordered, trace = order_beam_ids(["B_Z", "B_A"], {})
        self.assertEqual(ordered, ["B_Z", "B_A"])
        self.assertEqual(trace.fallback, "ORIGINAL_ENCOUNTER_ORDER_NO_GEOMETRY")

    def test_09_galera_gf_layout_is_row_then_left_to_right(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        positions = {
            bid: BeamPosition(bid, float(rec["centroid_x"]), float(rec["centroid_y"]), "fixture")
            for bid, rec in data["beams"].items()
        }
        lex = sorted(positions)
        ordered, trace = order_beam_ids(lex, positions)
        self.assertGreater(len(trace.rows), 3)
        self.assertEqual(ordered[:8], ["B1", "B2", "B3", "B6", "B48", "B49", "B50", "B51"])
        self.assertEqual(ordered[8:13], ["B7", "B8", "B9", "B10", "B11"])
        self.assertNotEqual(ordered, lex)
        self.assertLess(ordered.index("B2"), ordered.index("B10"))
        self.assertLess(ordered.index("B7"), ordered.index("B12"))
        xs_row1 = [positions[b].x for b in ordered[:8]]
        self.assertEqual(xs_row1, sorted(xs_row1))

    def test_disabled_leaves_order_unchanged(self):
        rows = _group("B11", 1) + _group("B5", 2)
        positions = {
            "B5": BeamPosition("B5", 1.0, 1.0, "test"),
            "B11": BeamPosition("B11", 2.0, 1.0, "test"),
        }
        out, trace = apply_bbs_drawing_order(rows, positions=positions, enabled=False)
        self.assertFalse(trace.enabled)
        self.assertEqual([r.beam_id for r in out if r.is_beam_header], ["B11", "B5"])

    def test_header_si_renumbered_after_move(self):
        rows = _group("B11", 1) + _group("B5", 2)
        positions = {
            "B5": BeamPosition("B5", 1.0, 1.0, "test"),
            "B11": BeamPosition("B11", 9.0, 1.0, "test"),
        }
        out = reorder_bbs_rows(rows, ["B5", "B11"])
        headers = [r for r in out if r.is_beam_header]
        self.assertEqual([h.beam_id for h in headers], ["B5", "B11"])
        self.assertEqual([h.si_no for h in headers], [1, 2])


if __name__ == "__main__":
    unittest.main()
