"""
Beam group parser — identify OfficialBeam blocks and attach reinforcement rows.
MODEL_VERSION: 8.6.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from header_matcher import beam_mark, is_beam_mark, normalize_text
from models import OfficialBeam
from reinforcement_row_parser import ReinforcementRowParser
from terminology_mapper import map_official_description

MODEL_VERSION = "8.6.0"


def _num(v: Any) -> float:
    try:
        if v is None or v == "":
            return 0.0
        return float(v)
    except (TypeError, ValueError):
        return 0.0


class BeamGroupParser:
    def __init__(self):
        self._row_parser = ReinforcementRowParser()

    def parse(
        self,
        grid: List[List[Any]],
        sheet_name: str,
        header_row: int,
        column_map: Dict[str, int],
        diameters: Dict[int, int],
        data_start_row: int,
    ) -> List[OfficialBeam]:
        desc_col = column_map.get("description")
        if desc_col is None:
            return []

        beams: List[OfficialBeam] = []
        current: Optional[OfficialBeam] = None
        r = data_start_row

        while r < len(grid):
            row = grid[r]
            if desc_col >= len(row):
                r += 1
                continue
            cell = row[desc_col]
            if cell is None or str(cell).strip() == "":
                r += 1
                continue

            text = str(cell).strip()

            # stop conditions: grand totals / new abstract banners
            nt = normalize_text(text)
            if nt.startswith("abstract") or "quantity breakup" in nt:
                break
            if nt.startswith("total") and current and not is_beam_mark(text):
                # floor/project total row — end of beam list typically after all beams
                # Don't break immediately; skip non-beam totals between sections
                if "total" in nt and not any(
                    k in nt for k in ("top", "bottom", "stirrup", "spacer", "hook", "sfr")
                ):
                    if beams and current is None:
                        break
                    if current:
                        self._finalize(current)
                        beams.append(current)
                        current = None
                    r += 1
                    continue

            if is_beam_mark(text):
                if current:
                    self._finalize(current)
                    beams.append(current)
                bid = beam_mark(text) or text.upper()
                floor = ""
                # floor often in column before description
                for c in range(max(0, desc_col - 2), desc_col):
                    if c < len(row) and row[c] is not None:
                        floor = str(row[c]).strip()
                        break
                current = OfficialBeam(
                    beam_id=bid,
                    floor=floor,
                    length_m=_num(row[column_map["spacing"]]) if column_map.get("spacing") is not None else None,
                    width_m=_num(row[column_map["breadth_no"]]) if column_map.get("breadth_no") is not None else None,
                    depth_m=_num(row[column_map["development"]]) if column_map.get("development") is not None else None,
                    concrete_m3=round(_num(row[column_map["quantity"]]), 4)
                    if column_map.get("quantity") is not None else 0.0,
                    shuttering_m2=round(_num(row[column_map["shuttering"]]), 4)
                    if column_map.get("shuttering") is not None else 0.0,
                    source_start_row=r + 1,
                    source_end_row=r + 1,
                    source_sheet=sheet_name,
                )
                r += 1
                continue

            if current is None:
                r += 1
                continue

            # Skip section titles that are not reinforcement
            role = map_official_description(text)
            reinf = self._row_parser.parse_row(
                current.beam_id, row, column_map, diameters, r + 1
            )
            if reinf is None:
                r += 1
                continue

            # Do not treat unknown non-reinforcement narrative as bars
            if role == "UNKNOWN" and reinf.steel <= 0 and not reinf.diameter:
                r += 1
                continue

            current.reinforcement_rows.append(reinf)
            current.source_end_row = r + 1
            r += 1

        if current:
            self._finalize(current)
            beams.append(current)
        return beams

    @staticmethod
    def _finalize(beam: OfficialBeam) -> None:
        dia_totals: Dict[int, float] = {}
        total = 0.0
        for row in beam.reinforcement_rows:
            total += row.steel
            for d, kg in row.diameter_kg.items():
                dia_totals[d] = dia_totals.get(d, 0.0) + kg
        beam.total_steel_kg = round(total, 4)
        beam.diameter_kg = {d: round(v, 4) for d, v in dia_totals.items() if v > 0}
