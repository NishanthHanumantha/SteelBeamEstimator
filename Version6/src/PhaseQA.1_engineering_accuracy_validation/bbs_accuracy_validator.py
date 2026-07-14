"""
Phase QA.1 — Module 7: BBS Accuracy Validator
Compare Expected BBS (V5 i_10_bbs) vs L.2 model BBS data.
Metrics: Row Accuracy, Overall Accuracy.
MODEL_VERSION: 6.5.1
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from benchmark_models import BBSRowRecord, KPIRecord, safe_pct
from ground_truth_loader import GroundTruth


class BBSAccuracyValidator:
    """Validates BBS entries against V5 reference BBS."""

    def validate(
        self,
        ground_truth: GroundTruth,
        v5_bbs_list: List[Dict[str, Any]],
        l2_models_by_beam: Dict[str, Any],
        v5_bar_identity_list: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:

        if not v5_bbs_list:
            kpi = KPIRecord(
                kpi_name="BBS Accuracy",
                expected=None, detected=None, correct=None, accuracy_pct=None,
                status="NOT_AVAILABLE",
                notes="V5 BBS data not found",
            )
            return {"kpi": kpi, "bbs_row_records": [], "overall_accuracy_pct": None}

        # Build V5 reference map: beam_id -> list of BBS entries
        # V5 BBS uses "member_beams" list and "diameter"/"cut_length" field names
        v5_by_beam: Dict[str, List[Dict]] = {}
        for bbs_entry in v5_bbs_list:
            member_beams = bbs_entry.get("member_beams", [])
            if not member_beams and bbs_entry.get("beam_id"):
                member_beams = [bbs_entry["beam_id"]]
            for bid in member_beams:
                v5_by_beam.setdefault(bid, []).append(bbs_entry)

        # Build L.2 bar map from role-specific lists
        l2_bars_by_beam: Dict[str, List[Dict]] = {}
        for bid, model in l2_models_by_beam.items():
            bars: List[Dict] = []
            for field in ["top_main_bars", "bottom_main_bars", "top_extra_bars",
                          "bottom_extra_bars", "stirrups", "side_face_reinforcement"]:
                lst = model.get(field, [])
                if isinstance(lst, list):
                    bars.extend(lst)
            l2_bars_by_beam[bid] = bars

        records: List[BBSRowRecord] = []
        total_rows = 0
        correct_rows = 0

        for bid in ground_truth.expected_beam_ids:
            v5_entries = v5_by_beam.get(bid, [])
            l2_bars = l2_bars_by_beam.get(bid, [])

            for i, v5_entry in enumerate(v5_entries):
                bbs_id = v5_entry.get("bbs_id", f"BBS::{bid}::{i}")

                # V5 BBS field names: "diameter", "cut_length", "role", "member_roles"
                v5_role = v5_entry.get("role") or (v5_entry.get("member_roles") or [None])[0]

                # Find matching L.2 bar by role
                role_match = None
                for bar in l2_bars:
                    bar_role = bar.get("semantic_role") or bar.get("role")
                    if bar_role == v5_role:
                        role_match = bar
                        break
                if role_match is None and l2_bars:
                    role_match = l2_bars[min(i, len(l2_bars) - 1)]

                # Compare fields — V5 uses "diameter" (not "diameter_mm"), "cut_length" (not "cut_length_mm")
                v5_dia = v5_entry.get("diameter") or v5_entry.get("diameter_mm") or 0
                l2_dia = (role_match.get("diameter_mm") or 0) if role_match else 0

                v5_qty = v5_entry.get("quantity") or v5_entry.get("no_of_bars") or 1
                l2_qty = (role_match.get("quantity") or role_match.get("no_of_bars") or 1) if role_match else 0

                v5_shape = v5_entry.get("shape_code") or ""
                l2_shape = (role_match.get("shape_code") or "") if role_match else ""

                # Cut length: V5 uses "cut_length" (mm)
                v5_cut = v5_entry.get("cut_length") or v5_entry.get("cut_length_mm")
                l2_cut = (role_match.get("cut_length_mm")) if role_match else None
                cut_match = (v5_cut is None or l2_cut is None or abs((v5_cut or 0) - (l2_cut or 0)) <= 10)

                dia_match = abs(float(v5_dia or 0) - float(l2_dia or 0)) < 1
                # V5 BBS does not store quantity directly — treat as matching when v5_qty=1 (default)
                qty_match = (v5_qty == 1) or (int(v5_qty or 0) == int(l2_qty or 0))
                shape_match = not v5_shape or not l2_shape or v5_shape == l2_shape

                # Primary correctness: diameter must match (cut_length/qty are supplementary)
                row_correct = dia_match and cut_match

                records.append(BBSRowRecord(
                    bbs_id=bbs_id,
                    beam_id=bid,
                    diameter_match=dia_match,
                    shape_match=shape_match,
                    quantity_match=qty_match,
                    cut_length_match=cut_match,
                    row_correct=row_correct,
                    notes=f"V5 dia={v5_dia} L2 dia={l2_dia} | V5 qty={v5_qty} L2 qty={l2_qty}",
                ))
                total_rows += 1
                if row_correct:
                    correct_rows += 1

        expected_bbs_count = ground_truth.expected_bbs_count
        overall_accuracy = safe_pct(correct_rows, total_rows)

        kpi = KPIRecord(
            kpi_name="BBS Accuracy",
            expected=float(expected_bbs_count),
            detected=float(len(v5_bbs_list)),
            correct=float(correct_rows),
            accuracy_pct=overall_accuracy,
            status="OK" if total_rows > 0 else "NOT_AVAILABLE",
            notes=f"Row accuracy: {correct_rows}/{total_rows}",
        )

        return {
            "kpi": kpi,
            "bbs_row_records": records,
            "total_rows": total_rows,
            "correct_rows": correct_rows,
            "overall_accuracy_pct": overall_accuracy,
            "diameter_match_pct": safe_pct(sum(1 for r in records if r.diameter_match), total_rows),
            "quantity_match_pct": safe_pct(sum(1 for r in records if r.quantity_match), total_rows),
            "shape_match_pct":    safe_pct(sum(1 for r in records if r.shape_match), total_rows),
            "cut_length_match_pct": safe_pct(sum(1 for r in records if r.cut_length_match), total_rows),
        }
