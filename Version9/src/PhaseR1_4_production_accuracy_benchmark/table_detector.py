"""
Semantic table detector — searches every worksheet by header meaning.
MODEL_VERSION: 8.6.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from header_matcher import (
    ABSTRACT_PATTERNS,
    DETAIL_HEADER_PATTERNS,
    QUANTITY_BREAKUP_PATTERNS,
    REINF_MT_KG_PATTERNS,
    SUMMARY_HEADER_PATTERNS,
    fuzzy_score,
    normalize_text,
    parse_diameter_mm,
)
from models import DetectedTable

MODEL_VERSION = "8.6.0"


class TableDetector:
    """Locate summary / breakup tables without worksheet-name dependency."""

    def __init__(self, sheets: Dict[str, Any]):
        """
        sheets: {sheet_name: list[list[cell_value]]}  (1-indexed conceptually via row/col ints)
        Actually we accept openpyxl worksheets via loader grid.
        """
        self._grids = sheets  # name -> rows (list of lists, 0-indexed)

    def detect_all(self) -> List[DetectedTable]:
        found: List[DetectedTable] = []
        for name, grid in self._grids.items():
            found.extend(self._scan_sheet(name, grid))
        found.sort(key=lambda t: t.score, reverse=True)
        return found

    def find_best(self, table_type: str) -> Optional[DetectedTable]:
        matches = [t for t in self.detect_all() if t.table_type == table_type]
        return matches[0] if matches else None

    def _scan_sheet(self, sheet_name: str, grid: List[List[Any]]) -> List[DetectedTable]:
        out: List[DetectedTable] = []
        max_r = len(grid)
        for r, row in enumerate(grid):
            for c, val in enumerate(row):
                text = normalize_text(val)
                if not text:
                    continue
                # ABSTRACT banner
                if fuzzy_score(text, ABSTRACT_PATTERNS) >= 0.85:
                    out.append(DetectedTable(
                        table_type="ABSTRACT_BANNER",
                        sheet_name=sheet_name,
                        anchor_row=r,
                        anchor_col=c,
                        header_text=str(val),
                        score=fuzzy_score(text, ABSTRACT_PATTERNS),
                    ))
                if fuzzy_score(text, REINF_MT_KG_PATTERNS) >= 0.75:
                    out.append(DetectedTable(
                        table_type="REINFORCEMENT_MT_KG_BANNER",
                        sheet_name=sheet_name,
                        anchor_row=r,
                        anchor_col=c,
                        header_text=str(val),
                        score=fuzzy_score(text, REINF_MT_KG_PATTERNS),
                    ))
                if fuzzy_score(text, QUANTITY_BREAKUP_PATTERNS) >= 0.7:
                    out.append(DetectedTable(
                        table_type="QUANTITY_BREAKUP",
                        sheet_name=sheet_name,
                        anchor_row=r,
                        anchor_col=c,
                        header_text=str(val),
                        score=fuzzy_score(text, QUANTITY_BREAKUP_PATTERNS),
                    ))

            # Summary header row: TOTAL-MT + KG + diameter columns
            cmap = self._map_summary_header_row(row)
            if cmap.get("total_mt") is not None and (
                cmap.get("kg") is not None or len(cmap.get("diameters", {})) >= 3
            ):
                score = 0.8 + 0.02 * min(10, len(cmap.get("diameters", {})))
                if self._nearby_abstract(grid, r):
                    score += 0.1
                out.append(DetectedTable(
                    table_type="STEEL_SUMMARY",
                    sheet_name=sheet_name,
                    anchor_row=r,
                    anchor_col=cmap.get("total_mt") or 0,
                    header_text="STEEL_SUMMARY_HEADER",
                    score=min(1.0, score),
                    column_map={
                        **{k: v for k, v in cmap.items() if k != "diameters" and v is not None},
                        **{f"dia_{d}": col for d, col in cmap.get("diameters", {}).items()},
                    },
                ))

            # Detail header row
            dmap = self._map_detail_header_row(row)
            if dmap.get("description") is not None and (
                dmap.get("cutting_length") is not None
                or dmap.get("total_length") is not None
                or dmap.get("no_dia") is not None
            ):
                score = 0.75 + 0.02 * min(10, len(dmap))
                out.append(DetectedTable(
                    table_type="BEAM_DETAIL_HEADER",
                    sheet_name=sheet_name,
                    anchor_row=r,
                    anchor_col=dmap.get("description") or 0,
                    header_text="BEAM_DETAIL_HEADER",
                    score=min(1.0, score),
                    column_map={k: v for k, v in dmap.items() if isinstance(v, int)},
                ))
        return out

    def _nearby_abstract(self, grid: List[List[Any]], header_row: int) -> bool:
        start = max(0, header_row - 3)
        for r in range(start, header_row + 1):
            for val in grid[r]:
                if fuzzy_score(val, ABSTRACT_PATTERNS) >= 0.85:
                    return True
                if fuzzy_score(val, REINF_MT_KG_PATTERNS) >= 0.75:
                    return True
        return False

    def _map_summary_header_row(self, row: List[Any]) -> Dict[str, Any]:
        from header_matcher import SUMMARY_HEADER_EXACT
        result: Dict[str, Any] = {"diameters": {}}
        for c, val in enumerate(row):
            if val is None or str(val).strip() == "":
                continue
            dia = parse_diameter_mm(val)
            if dia is not None:
                # Prefer mm-labelled diameter headers over bare numbers when both exist
                text = normalize_text(val)
                if dia not in result["diameters"] or "mm" in text:
                    result["diameters"][dia] = c
                continue
            for key, patterns in SUMMARY_HEADER_PATTERNS.items():
                score = fuzzy_score(val, patterns)
                if key in SUMMARY_HEADER_EXACT:
                    # require near-exact so compound headers do not steal columns
                    if normalize_text(val) not in SUMMARY_HEADER_EXACT[key] and score < 0.98:
                        continue
                if score >= 0.85:
                    # keep first / best (do not overwrite better match)
                    prev = result.get(key)
                    if prev is None or score > 0.95:
                        if prev is None or normalize_text(val) in SUMMARY_HEADER_EXACT.get(key, ()):
                            result[key] = c
                        elif prev is None:
                            result[key] = c
        return result

    def _map_detail_header_row(self, row: List[Any]) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for c, val in enumerate(row):
            if val is None or str(val).strip() == "":
                continue
            for key, patterns in DETAIL_HEADER_PATTERNS.items():
                if key in result:
                    continue
                thr = 0.78 if key != "depth" else 0.9
                if fuzzy_score(val, patterns) >= thr:
                    result[key] = c
            # bare diameter column headers in breakup steel split
            dia = parse_diameter_mm(val)
            if dia is not None and fuzzy_score(val, ("mm",)) < 0.5:
                # numeric-only diameter headers (8, 10, ...)
                text = normalize_text(val)
                if re_full_number(text) or "mm" in text or text.isdigit():
                    result[f"dia_{dia}"] = c
        return result


def re_full_number(text: str) -> bool:
    import re
    return bool(re.fullmatch(r"\d{1,2}", text or ""))
