"""
Error classification for benchmark mismatches.
MODEL_VERSION: 8.6.0
"""
from __future__ import annotations

from typing import Any, Dict, List

MODEL_VERSION = "8.6.0"

ERROR_TYPES = (
    "Missing Beam",
    "Extra Beam",
    "Missing Reinforcement Row",
    "Wrong Diameter",
    "Wrong Quantity",
    "Wrong Cut Length",
    "Wrong Steel",
    "Wrong Piece Type",
    "Wrong Classification",
    "Wrong Shape",
    "Wrong Weight",
    "Wrong BBS",
    "Wrong Workbook Output",
)


class ErrorClassifier:
    def classify(self, comparison: Dict[str, Any]) -> Dict[str, Any]:
        diagnostics: List[Dict[str, Any]] = []

        beam = comparison.get("beam_accuracy") or {}
        for bid in beam.get("missing_beams") or []:
            diagnostics.append(self._item("Missing Beam", bid, f"Official beam {bid} absent in production"))
        for bid in beam.get("extra_beams") or []:
            diagnostics.append(self._item("Extra Beam", bid, f"Production beam {bid} not in official workbook"))

        for g in beam.get("geometry_comparisons") or []:
            if g.get("length_match") is False:
                diagnostics.append(self._item(
                    "Wrong Quantity",
                    g.get("beam_id"),
                    f"Beam length mismatch official={g.get('official_length_m')} prod={g.get('production_span_m')}",
                    field="geometry.length",
                ))

        reinf = comparison.get("reinforcement_accuracy") or {}
        for issue in reinf.get("sample_issues") or []:
            diagnostics.append(self._item(
                "Missing Reinforcement Row",
                issue.get("beam_id"),
                f"{issue.get('description')} ({issue.get('role')})",
                field="reinforcement",
            ))
        if int(reinf.get("diameter_mismatch_signals") or 0) > 0:
            diagnostics.append(self._item(
                "Wrong Diameter",
                "*",
                f"{reinf.get('diameter_mismatch_signals')} diameter mismatch signals vs official rows",
            ))

        steel = comparison.get("steel_accuracy") or {}
        if float(steel.get("pct_error") or 0) > 2.0:
            diagnostics.append(self._item(
                "Wrong Steel",
                "PROJECT",
                f"Total steel error {steel.get('pct_error')}% "
                f"(official {steel.get('official_total_kg')} kg vs prod {steel.get('production_total_kg')} kg)",
            ))
            diagnostics.append(self._item(
                "Wrong Weight",
                "PROJECT",
                f"Weight delta {steel.get('abs_diff_kg')} kg",
            ))
        for drow in steel.get("diameter_rows") or []:
            if float(drow.get("pct_error") or 0) > 5.0:
                diagnostics.append(self._item(
                    "Wrong Diameter",
                    f"DIA_{drow.get('diameter_mm')}",
                    f"Diameter {drow.get('diameter_mm')} mm steel error {drow.get('pct_error')}%",
                ))

        if float(steel.get("cut_length_accuracy") or 1) < 0.7 and int(steel.get("cut_length_comparisons") or 0) > 0:
            diagnostics.append(self._item(
                "Wrong Cut Length",
                "*",
                f"Cut length accuracy {steel.get('cut_length_accuracy')}",
            ))

        bbs = comparison.get("bbs_accuracy") or {}
        if float(bbs.get("bbs_score") or 0) < 0.6:
            diagnostics.append(self._item("Wrong BBS", "PROJECT", f"BBS score {bbs.get('bbs_score')}"))

        wb = comparison.get("workbook_accuracy") or {}
        if not wb.get("workbook_exists"):
            diagnostics.append(self._item("Wrong Workbook Output", "PROJECT", "Production workbook missing"))

        by_type: Dict[str, int] = {t: 0 for t in ERROR_TYPES}
        for d in diagnostics:
            by_type[d["error_type"]] = by_type.get(d["error_type"], 0) + 1

        return {
            "model_version": MODEL_VERSION,
            "diagnostic_count": len(diagnostics),
            "by_type": by_type,
            "diagnostics": diagnostics,
        }

    @staticmethod
    def _item(error_type: str, entity: str, message: str, field: str = "") -> Dict[str, Any]:
        return {
            "error_type": error_type,
            "entity": entity,
            "field": field,
            "message": message,
        }
