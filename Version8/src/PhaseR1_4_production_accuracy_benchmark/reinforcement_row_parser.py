"""
Parse OfficialReinforcementRow from breakup table rows.
MODEL_VERSION: 8.6.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from models import OfficialReinforcementRow
from terminology_mapper import map_official_description

MODEL_VERSION = "8.6.0"


def _num(v: Any) -> float:
    try:
        if v is None or v == "":
            return 0.0
        return float(v)
    except (TypeError, ValueError):
        return 0.0


class ReinforcementRowParser:
    def parse_row(
        self,
        beam_id: str,
        row: List[Any],
        column_map: Dict[str, int],
        diameters: Dict[int, int],
        source_row: int,
    ) -> Optional[OfficialReinforcementRow]:
        desc_col = column_map.get("description")
        if desc_col is None or desc_col >= len(row):
            return None
        desc_val = row[desc_col]
        if desc_val is None:
            return None
        description = str(desc_val).strip()
        if not description:
            return None

        role = map_official_description(description)
        if role == "UNKNOWN":
            # still accept if it looks like reinforcement (has diameter/steel)
            pass

        diameter = None
        if column_map.get("no_dia") is not None:
            diameter = _num(row[column_map["no_dia"]]) or None

        spacing = None
        if column_map.get("spacing") is not None:
            spacing = _num(row[column_map["spacing"]]) or None

        number_of_bars = None
        if column_map.get("breadth_no") is not None:
            number_of_bars = _num(row[column_map["breadth_no"]]) or None

        development_length = None
        if column_map.get("development") is not None:
            development_length = _num(row[column_map["development"]]) or None

        cut_length = None
        if column_map.get("cutting_length") is not None:
            cut_length = _num(row[column_map["cutting_length"]]) or None

        total_length = None
        if column_map.get("total_length") is not None:
            total_length = _num(row[column_map["total_length"]]) or None

        dia_kg: Dict[int, float] = {}
        for d, col in diameters.items():
            if col < len(row):
                kg = _num(row[col])
                if kg > 0:
                    dia_kg[d] = round(kg, 4)

        steel = 0.0
        if column_map.get("steel") is not None and column_map["steel"] < len(row):
            steel = _num(row[column_map["steel"]])
        if steel <= 0:
            steel = sum(dia_kg.values())

        diameter_column = None
        if diameter:
            d_int = int(round(diameter))
            if d_int in diameters:
                diameter_column = d_int
            elif dia_kg:
                diameter_column = max(dia_kg.items(), key=lambda x: x[1])[0]

        return OfficialReinforcementRow(
            beam_id=beam_id,
            description=description,
            role=role,
            diameter=diameter,
            spacing=spacing,
            number_of_bars=number_of_bars,
            development_length=development_length,
            cut_length=cut_length,
            total_length=total_length,
            steel=round(steel, 4),
            diameter_column=diameter_column,
            diameter_kg=dia_kg,
            source_row=source_row,
        )
