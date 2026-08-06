"""
Summary table parser — ABSTRACT / Reinforcement-in MT&KG.
MODEL_VERSION: 8.6.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from header_matcher import fuzzy_score, normalize_text, parse_diameter_mm
from models import DetectedTable, OfficialSteelSummary
from table_detector import TableDetector

MODEL_VERSION = "8.6.0"


def _num(v: Any) -> float:
    try:
        if v is None or v == "":
            return 0.0
        return float(v)
    except (TypeError, ValueError):
        return 0.0


class SummaryTableParser:
    def __init__(self, grids: Dict[str, List[List[Any]]], detected: List[DetectedTable]):
        self.grids = grids
        self.detected = detected

    def parse(self) -> OfficialSteelSummary:
        table = self._pick_summary_table()
        if not table:
            return OfficialSteelSummary(warnings=["STEEL_SUMMARY table not detected"])

        grid = self.grids[table.sheet_name]
        header_row = table.anchor_row
        col_map = self._rebuild_column_map(grid[header_row])
        data_row_idx, label = self._pick_data_row(grid, header_row, col_map)
        if data_row_idx is None:
            return OfficialSteelSummary(
                warnings=["STEEL_SUMMARY header found but no data row"],
                source_sheet=table.sheet_name,
                source_header_row=header_row + 1,
            )

        row = grid[data_row_idx]
        dia_mt: Dict[int, float] = {}
        for dia, col in col_map.get("diameters", {}).items():
            if col < len(row):
                dia_mt[dia] = round(_num(row[col]), 6)

        total_mt = _num(row[col_map["total_mt"]]) if col_map.get("total_mt") is not None else 0.0
        kg = _num(row[col_map["kg"]]) if col_map.get("kg") is not None else 0.0
        warnings: List[str] = []

        if kg > 0:
            total_kg = round(kg, 3)
        elif total_mt > 0:
            total_kg = round(total_mt * 1000.0, 3)
            warnings.append("kg column missing/zero — derived from TOTAL-MT×1000")
        else:
            total_kg = round(sum(dia_mt.values()) * 1000.0, 3)
            warnings.append("total derived from sum of diameter MT")

        if total_mt <= 0 and total_kg > 0:
            total_mt = round(total_kg / 1000.0, 6)

        project, floor, block = self._infer_meta(grid, header_row, data_row_idx, label)

        return OfficialSteelSummary(
            diameter_summary=dia_mt,
            total_mt=round(total_mt, 6),
            total_kg=total_kg,
            project_name=project,
            floor=floor,
            block=block,
            concrete_m3=round(_num(row[col_map["concrete"]]), 4)
            if col_map.get("concrete") is not None else 0.0,
            shuttering_m2=round(_num(row[col_map["shuttering"]]), 4)
            if col_map.get("shuttering") is not None else 0.0,
            source_sheet=table.sheet_name,
            source_header_row=header_row + 1,
            source_data_row=data_row_idx + 1,
            warnings=warnings,
        )

    def _pick_summary_table(self) -> Optional[DetectedTable]:
        cands = [t for t in self.detected if t.table_type == "STEEL_SUMMARY"]
        if not cands:
            # rebuild detection on the fly
            det = TableDetector(self.grids).find_best("STEEL_SUMMARY")
            return det
        return max(cands, key=lambda t: t.score)

    def _rebuild_column_map(self, row: List[Any]) -> Dict[str, Any]:
        from header_matcher import SUMMARY_HEADER_EXACT, SUMMARY_HEADER_PATTERNS
        result: Dict[str, Any] = {"diameters": {}}
        for c, val in enumerate(row):
            if val is None or str(val).strip() == "":
                continue
            dia = parse_diameter_mm(val)
            if dia is not None:
                text = normalize_text(val)
                if dia not in result["diameters"] or "mm" in text:
                    result["diameters"][dia] = c
                continue
            for key, patterns in SUMMARY_HEADER_PATTERNS.items():
                score = fuzzy_score(val, patterns)
                if key in SUMMARY_HEADER_EXACT:
                    if normalize_text(val) not in SUMMARY_HEADER_EXACT[key] and score < 0.98:
                        continue
                if score >= 0.85 and key not in result:
                    result[key] = c
                elif score >= 0.98:
                    result[key] = c
        return result

    def _pick_data_row(
        self, grid: List[List[Any]], header_row: int, col_map: Dict[str, Any]
    ) -> Tuple[Optional[int], str]:
        kg_col = col_map.get("kg")
        mt_col = col_map.get("total_mt")
        end = min(len(grid), header_row + 20)
        candidates: List[Tuple[float, int, int, str]] = []  # priority, kg, row, label

        for r in range(header_row + 1, end):
            row = grid[r]
            # stop at next quantity breakup
            joined = " ".join(normalize_text(v) for v in row if v is not None)
            if "quantity breakup" in joined or (
                "concrete" in joined and "shuttering" in joined and "reinforcement" in joined
                and "breakup" in joined
            ):
                break

            label = ""
            for c in range(min(6, len(row))):
                v = row[c]
                if v is None:
                    continue
                s = str(v).strip()
                if s and not s.replace(".", "", 1).isdigit():
                    label = s
                    break
            if not label or normalize_text(label) in ("description", "clubhouse", "abstract"):
                # still allow numeric-only rows if kg present
                pass

            kg = _num(row[kg_col]) if kg_col is not None and kg_col < len(row) else 0.0
            mt = _num(row[mt_col]) if mt_col is not None and mt_col < len(row) else 0.0
            if kg <= 0 and mt <= 0:
                continue

            ll = normalize_text(label)
            priority = 0
            if "terrace" in ll:
                priority = 3
            elif "total" in ll:
                priority = 2
            elif label:
                priority = 1
            candidates.append((priority, kg if kg > 0 else mt * 1000.0, r, label))

        if not candidates:
            return None, ""
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        _, _, r, label = candidates[0]
        return r, label

    def _infer_meta(
        self, grid: List[List[Any]], header_row: int, data_row: int, label: str
    ) -> Tuple[str, str, str]:
        project = ""
        floor = label
        block = ""
        # scan nearby rows for project / block labels
        for r in range(max(0, header_row - 5), min(len(grid), data_row + 3)):
            for val in grid[r][:8]:
                if val is None:
                    continue
                s = str(val).strip()
                ns = normalize_text(s)
                if not s or ns in ("abstract", "description", "si no"):
                    continue
                if not project and any(k in ns for k in ("club", "project", "tower", "block")):
                    if "floor" not in ns:
                        project = s
                if "floor" in ns or "terrace" in ns:
                    floor = s
                if "block" in ns:
                    block = s
        if not project:
            # use first non-empty text above summary
            for r in range(max(0, header_row - 8), header_row):
                for val in grid[r][:5]:
                    if val and isinstance(val, str) and len(val.strip()) > 2:
                        project = val.strip()
                        break
                if project:
                    break
        return project, floor, block
