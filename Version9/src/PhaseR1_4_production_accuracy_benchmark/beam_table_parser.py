"""
Reinforcement Quantity Breakup — dynamic column detection.
MODEL_VERSION: 8.6.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from header_matcher import DETAIL_HEADER_PATTERNS, fuzzy_score, normalize_text, parse_diameter_mm
from models import DetectedTable

MODEL_VERSION = "8.6.0"


class BeamTableParser:
    """Resolve column map for the beam reinforcement breakup table."""

    def __init__(self, grids: Dict[str, List[List[Any]]], detected: List[DetectedTable]):
        self.grids = grids
        self.detected = detected

    def locate(self) -> Optional[Dict[str, Any]]:
        """
        Returns {
          sheet_name, header_row, column_map, diameters, data_start_row
        }
        """
        header = self._pick_detail_header()
        breakup = self._pick_breakup_anchor()

        if header is None and breakup is None:
            return None

        # Prefer detail header on same sheet as breakup (or best score)
        if header is None:
            # search below breakup for description header
            sheet = breakup.sheet_name
            grid = self.grids[sheet]
            header_row = self._find_header_near(grid, breakup.anchor_row)
            if header_row is None:
                return None
            cmap = self._map_row(grid[header_row])
        else:
            sheet = header.sheet_name
            # if breakup exists on another sheet with higher score for QUANTITY_BREAKUP,
            # still use header sheet (headers define the table)
            if breakup and breakup.sheet_name == header.sheet_name:
                # ensure header is after breakup banner when multiple headers exist
                pass
            grid = self.grids[sheet]
            header_row = header.anchor_row
            cmap = self._map_row(grid[header_row])

        if cmap.get("description") is None:
            return None

        diameters = {
            int(k.split("_")[1]): v
            for k, v in cmap.items()
            if k.startswith("dia_")
        }
        # also scan next row for unit sub-headers / numeric dia weights — keep diameters from header
        if not diameters:
            diameters = self._scan_diameter_columns(grid, header_row)

        return {
            "sheet_name": sheet,
            "header_row": header_row,
            "column_map": cmap,
            "diameters": diameters,
            "data_start_row": header_row + 1,
            "breakup_anchor_row": breakup.anchor_row if breakup and breakup.sheet_name == sheet else None,
        }

    def _pick_detail_header(self) -> Optional[DetectedTable]:
        cands = [t for t in self.detected if t.table_type == "BEAM_DETAIL_HEADER"]
        if not cands:
            return None
        # Prefer the later header near quantity breakup (detail section, not title page)
        breakup_rows = {
            (t.sheet_name, t.anchor_row)
            for t in self.detected
            if t.table_type == "QUANTITY_BREAKUP"
        }
        scored = []
        for t in cands:
            bonus = 0.0
            for sn, br in breakup_rows:
                if sn == t.sheet_name and t.anchor_row >= br:
                    bonus = 0.15
            scored.append((t.score + bonus, t.anchor_row, t))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return scored[0][2]

    def _pick_breakup_anchor(self) -> Optional[DetectedTable]:
        cands = [t for t in self.detected if t.table_type == "QUANTITY_BREAKUP"]
        if not cands:
            return None
        # Prefer the later occurrence (detail section) when duplicates exist
        return max(cands, key=lambda t: (t.anchor_row, t.score))

    def _find_header_near(self, grid: List[List[Any]], start: int) -> Optional[int]:
        for r in range(start, min(len(grid), start + 15)):
            cmap = self._map_row(grid[r])
            if cmap.get("description") is not None and (
                cmap.get("cutting_length") is not None
                or cmap.get("total_length") is not None
                or cmap.get("no_dia") is not None
            ):
                return r
        return None

    def _map_row(self, row: List[Any]) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for c, val in enumerate(row):
            if val is None or str(val).strip() == "":
                continue
            for key, patterns in DETAIL_HEADER_PATTERNS.items():
                if key in result:
                    continue
                thr = 0.78 if key != "depth" else 0.92
                if fuzzy_score(val, patterns) >= thr:
                    result[key] = c
            dia = parse_diameter_mm(val)
            if dia is not None:
                text = normalize_text(val)
                # accept "8", "8 mm", "10mm"
                result[f"dia_{dia}"] = c
        return result

    def _scan_diameter_columns(self, grid: List[List[Any]], header_row: int) -> Dict[int, int]:
        dias: Dict[int, int] = {}
        for r in range(header_row, min(len(grid), header_row + 3)):
            for c, val in enumerate(grid[r]):
                dia = parse_diameter_mm(val)
                if dia is not None:
                    dias[dia] = c
        return dias
