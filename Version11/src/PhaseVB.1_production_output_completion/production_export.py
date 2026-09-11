"""
Production Export — Phase V.B.1 MODULE 10

Exports 7 JSON reports to the production output directory.
"""
import json
import pathlib
from datetime import datetime
from typing import Dict, Any, List, Optional

from production_output_models import (
    ProductionStatistics, ProjectSteelSummary,
    BBSRow, WorkbookValidationResult, ProductionOutputResult,
)


def _serialise(obj: Any) -> Any:
    """Make objects JSON-serialisable."""
    if isinstance(obj, pathlib.Path):
        return str(obj)
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialise(v) for k, v in obj.__dict__.items()}
    if isinstance(obj, list):
        return [_serialise(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _serialise(v) for k, v in obj.items()}
    return obj


def _dump(data: Any, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_serialise(data), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


class ProductionExport:
    """Exports all Phase V.B.1 JSON artefacts."""

    def __init__(self, output_dir: pathlib.Path) -> None:
        self.out = output_dir

    def export_all(
        self,
        report: Dict[str, Any],
        validation: Optional[WorkbookValidationResult],
        steel_summary: ProjectSteelSummary,
        bbs_rows: List[BBSRow],
        statistics: ProductionStatistics,
        result: ProductionOutputResult,
    ) -> Dict[str, pathlib.Path]:

        paths: Dict[str, pathlib.Path] = {}

        # 1. production_output_report.json
        paths["production_output_report"] = self._export(
            "production_output_report.json", report
        )

        # 2. workbook_validation.json
        paths["workbook_validation"] = self._export(
            "workbook_validation.json",
            _serialise(validation) if validation else {"status": "NOT_RUN"},
        )

        # 3. steel_weight_summary.json
        paths["steel_weight_summary"] = self._export(
            "steel_weight_summary.json",
            {
                "total_weight_kg": round(steel_summary.total_weight_kg, 3),
                "total_beams": steel_summary.total_beams,
                "total_bars": steel_summary.total_bars,
                "formula": "W = (pi*d^2/4) * cut_length * qty * 7850 / 1e9",
                "calculation_method": steel_summary.calculation_method,
                "density_kg_m3": steel_summary.density_kg_m3,
                "diameter_summary": [
                    {
                        "diameter_mm": ds.diameter_mm,
                        "total_bars": ds.total_bars,
                        "total_length_mm": round(ds.total_length_mm, 1),
                        "total_weight_kg": round(ds.total_weight_kg, 3),
                        "weight_fraction_pct": round(ds.weight_fraction * 100, 2),
                    }
                    for ds in steel_summary.diameter_summary
                ],
                "beam_weights": [
                    {
                        "beam_id": bw.beam_id,
                        "total_weight_kg": round(bw.total_weight_kg, 3),
                        "weight_by_diameter": {
                            f"Y{d}": round(w, 3)
                            for d, w in bw.weight_by_diameter.items()
                        },
                    }
                    for bw in steel_summary.beam_weights
                ],
            },
        )

        # 4. bbs_summary.json
        eng_rows = [r for r in bbs_rows if not r.is_beam_header]
        paths["bbs_summary"] = self._export(
            "bbs_summary.json",
            {
                "total_bbs_rows": len(bbs_rows),
                "engineering_rows": len(eng_rows),
                "beam_header_rows": len(bbs_rows) - len(eng_rows),
                "rows": [_serialise(r) for r in bbs_rows],
            },
        )

        # 5. workbook_statistics.json
        paths["workbook_statistics"] = self._export(
            "workbook_statistics.json",
            _serialise(statistics),
        )

        # 6. engineering_totals.json
        paths["engineering_totals"] = self._export(
            "engineering_totals.json",
            {
                "total_beams": statistics.total_beams,
                "total_engineering_rows": statistics.total_engineering_rows,
                "total_steel_kg": statistics.steel_total_kg,
                "execution_time_sec": statistics.execution_time_sec,
                "diameter_totals_kg": statistics.diameter_summary,
            },
        )

        # 7. production_statistics.json
        paths["production_statistics"] = self._export(
            "production_statistics.json",
            _serialise(statistics),
        )

        return paths

    def _export(self, filename: str, data: Any) -> pathlib.Path:
        path = self.out / filename
        _dump(data, path)
        return path
