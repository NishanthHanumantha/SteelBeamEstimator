"""Build per-beam propagation matrix and compare R.1 vs workbook."""
from __future__ import annotations
from typing import Any, Dict, List

from .propagation_models import BeamPropagationRecord
from .reinforcement_model_reader import ReinforcementModelReader


class PropagationComparator:

    def build_matrix(
        self, reader: ReinforcementModelReader
    ) -> List[BeamPropagationRecord]:
        records: List[BeamPropagationRecord] = []
        for beam_id in reader.beam_ids():
            reg = reader.registry_beam(beam_id)
            r1 = reader.r1_model(beam_id)
            gc, qty, r1_roles = reader.count_r1_groups(r1)
            adapter = reader.adapter_model(beam_id)
            adapter_bars, _ = reader.count_l2_bars(adapter)
            l2 = reader.l2_model(beam_id)
            l2_bars, l2_roles = reader.count_l2_bars(l2)
            steel = reader.steel_beam(beam_id)
            steel_bars = len(steel.get("bar_weights") or [])
            steel_kg = float(steel.get("total_weight_kg") or 0)
            bbs_rows = reader.bbs_rows_for_beam(beam_id)
            eng_bbs = sum(
                1 for r in bbs_rows
                if not r.get("is_beam_header") and (
                    r.get("total_weight_kg") or r.get("quantity")
                )
            )

            geom = {
                "clear_span_mm": reg.get("clear_span_mm") or (l2.get("geometry") or {}).get("clear_span_mm"),
                "width_mm": (reg.get("section") or {}).get("width_mm") or (l2.get("geometry") or {}).get("width_mm"),
                "depth_mm": (reg.get("section") or {}).get("depth_mm") or (l2.get("geometry") or {}).get("depth_mm"),
            }

            records.append(BeamPropagationRecord(
                beam_id=beam_id,
                in_registry=bool(reg),
                geometry=geom,
                r1_group_count=gc,
                r1_total_quantity=qty,
                r1_roles=r1_roles,
                adapter_bar_count=adapter_bars,
                l2_bar_count=l2_bars,
                l2_roles=l2_roles,
                steel_bar_count=steel_bars,
                steel_weight_kg=steel_kg,
                bbs_row_count=len(bbs_rows),
                bbs_engineering_rows=eng_bbs,
                excel_has_steel=steel_kg > 0,
            ))
        return records

    def compare_r1_vs_workbook(
        self, reader: ReinforcementModelReader
    ) -> Dict[str, Any]:
        r1_totals: Dict[str, int] = {}
        for beam_id in reader.beam_ids():
            _, _, roles = reader.count_r1_groups(reader.r1_model(beam_id))
            for role, qty in roles.items():
                r1_totals[role] = r1_totals.get(role, 0) + qty

        steel_roles: Dict[str, int] = {}
        for beam_id in reader.beam_ids():
            steel = reader.steel_beam(beam_id)
            for bw in steel.get("bar_weights") or []:
                role = bw.get("role", "UNKNOWN")
                steel_roles[role] = steel_roles.get(role, 0) + int(bw.get("quantity") or 1)

        return {
            "r1_groups_discovered": dict(sorted(r1_totals.items())),
            "r1_total_quantity": sum(r1_totals.values()),
            "engineering_bars_in_l2": sum(
                reader.count_l2_bars(reader.l2_model(b))[0]
                for b in reader.beam_ids()
            ),
            "steel_bars_in_workbook": sum(steel_roles.values()),
            "steel_roles_in_workbook": dict(sorted(steel_roles.items())),
            "workbook_engineering_rows": sum(
                len(reader.steel_beam(b).get("bar_weights") or [])
                for b in reader.beam_ids()
            ),
            "propagation_loss": {
                "r1_to_l2": sum(r1_totals.values()) - sum(
                    reader.count_l2_bars(reader.l2_model(b))[0]
                    for b in reader.beam_ids()
                ),
                "l2_to_steel": sum(
                    reader.count_l2_bars(reader.l2_model(b))[0]
                    for b in reader.beam_ids()
                ) - sum(steel_roles.values()),
            },
        }
