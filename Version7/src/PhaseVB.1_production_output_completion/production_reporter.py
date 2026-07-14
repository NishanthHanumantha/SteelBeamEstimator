"""
Production Reporter — Phase V.B.1 MODULE 9

Generates the 9-section production report:
  1. Pipeline Summary
  2. Workbook Summary
  3. Steel Summary
  4. Beam Summary
  5. BBS Summary
  6. Workbook Validation
  7. Engineering Totals
  8. Known Differences
  9. Recommendations
"""
from datetime import datetime
from typing import List, Dict, Any, Optional

from production_output_models import (
    ProductionOutputResult, ProductionStatistics,
    ProjectSteelSummary, BBSRow, WorkbookValidationResult,
)


class ProductionReporter:
    """Builds the complete 9-section Phase V.B.1 report."""

    def __init__(
        self,
        result: ProductionOutputResult,
        steel_summary: ProjectSteelSummary,
        bbs_rows: List[BBSRow],
        statistics: ProductionStatistics,
        validation_result: Optional[WorkbookValidationResult],
        integration_report: Dict[str, Any],
    ) -> None:
        self.result = result
        self.steel = steel_summary
        self.bbs = bbs_rows
        self.stats = statistics
        self.val = validation_result
        self.int_report = integration_report

    def build(self) -> Dict[str, Any]:
        return {
            "phase": "V.B.1",
            "model_version": "6.6.0",
            "generated_at": datetime.now().isoformat(),
            "sections": {
                "1_pipeline_summary": self._pipeline_summary(),
                "2_workbook_summary": self._workbook_summary(),
                "3_steel_summary": self._steel_summary(),
                "4_beam_summary": self._beam_summary(),
                "5_bbs_summary": self._bbs_summary(),
                "6_workbook_validation": self._validation_section(),
                "7_engineering_totals": self._engineering_totals(),
                "8_known_differences": self._known_differences(),
                "9_recommendations": self._recommendations(),
            },
        }

    # ── Section builders ─────────────────────────────────────────────────────

    def _pipeline_summary(self) -> Dict[str, Any]:
        return {
            "phase_id": "V.B.1",
            "title": "Production Output Completion",
            "model_version": "6.6.0",
            "exit_code": self.result.pipeline_exit_code,
            "status": "PASS" if self.result.pipeline_exit_code == 0 else "FAIL",
            "steel_weight_kg": self.result.steel_weight_kg,
            "steel_weight_status": "COMPLETE" if self.result.steel_weight_kg > 0 else "ZERO",
            "workbook_generated": bool(self.result.workbook_path),
            "engineering_review_generated": bool(self.result.engineering_review_path),
            "archive_generated": bool(self.result.archive_path),
            "errors": self.result.errors,
            "warnings": self.result.warnings,
            "integration_engine_validation": self.int_report,
        }

    def _workbook_summary(self) -> Dict[str, Any]:
        return {
            "production_workbook": str(self.result.workbook_path),
            "engineering_review_workbook": str(self.result.engineering_review_path),
            "archive_workbook": str(self.result.archive_path),
            "worksheets_generated": 7,
            "worksheet_names": [
                "Project Header", "General Notes", "Beam Summary",
                "Bar Bending Schedule", "Steel Summary",
                "Diameter Summary", "Project Totals",
            ],
            "execution_time_sec": self.stats.execution_time_sec,
            "total_rows_generated": self.stats.total_rows_generated,
            "total_columns": self.stats.total_columns,
        }

    def _steel_summary(self) -> Dict[str, Any]:
        diam = [
            {
                "diameter_mm": ds.diameter_mm,
                "label": f"Y{ds.diameter_mm}",
                "total_bars": ds.total_bars,
                "total_length_mm": round(ds.total_length_mm, 1),
                "total_weight_kg": round(ds.total_weight_kg, 3),
                "weight_fraction_pct": round(ds.weight_fraction * 100, 2),
            }
            for ds in self.steel.diameter_summary
        ]
        return {
            "total_weight_kg": round(self.steel.total_weight_kg, 3),
            "total_beams": self.steel.total_beams,
            "total_bars": self.steel.total_bars,
            "calculation_method": self.steel.calculation_method,
            "density_kg_m3": self.steel.density_kg_m3,
            "formula": "W = (pi * d^2 / 4) * L * qty * 7850 / 1e9",
            "diameter_breakdown": diam,
        }

    def _beam_summary(self) -> Dict[str, Any]:
        beams = []
        for bw in self.steel.beam_weights:
            beams.append({
                "beam_id": bw.beam_id,
                "span_m": round(bw.span_mm / 1000, 3) if bw.span_mm else None,
                "depth_m": round(bw.depth_mm / 1000, 3) if bw.depth_mm else None,
                "width_m": round(bw.width_mm / 1000, 3) if bw.width_mm else None,
                "bar_count": len(bw.bar_weights),
                "total_weight_kg": round(bw.total_weight_kg, 3),
                "weight_by_diameter": {
                    f"Y{d}": round(w, 3)
                    for d, w in bw.weight_by_diameter.items()
                },
            })
        return {
            "total_beams": len(beams),
            "beams": beams,
        }

    def _bbs_summary(self) -> Dict[str, Any]:
        header_rows = [r for r in self.bbs if r.is_beam_header]
        eng_rows    = [r for r in self.bbs if not r.is_beam_header]
        role_counts: Dict[str, int] = {}
        for r in eng_rows:
            role_counts[r.description] = role_counts.get(r.description, 0) + 1
        return {
            "total_rows": len(self.bbs),
            "beam_header_rows": len(header_rows),
            "engineering_rows": len(eng_rows),
            "role_distribution": role_counts,
            "bbs_format": "Estimator-style per-bar rows",
        }

    def _validation_section(self) -> Dict[str, Any]:
        if self.val is None:
            return {"status": "NOT_RUN"}
        return {
            "validation_passed": self.val.validation_passed,
            "is_readable": self.val.is_readable,
            "is_complete": self.val.is_complete,
            "worksheet_count": self.val.worksheet_count,
            "worksheet_names": self.val.worksheet_names,
            "missing_worksheets": self.val.missing_worksheets,
            "header_checks_passed": all(self.val.header_checks.values()),
            "steel_total_found_kg": self.val.steel_total_found,
            "steel_total_check_passed": self.val.steel_total_check,
            "no_corrupted_cells": self.val.no_corrupted_cells,
            "validation_errors": self.val.validation_errors,
            "row_counts": self.val.row_counts,
        }

    def _engineering_totals(self) -> Dict[str, Any]:
        return {
            "total_beams": self.stats.total_beams,
            "total_bbs_rows": self.stats.total_bbs_rows,
            "total_engineering_rows": self.stats.total_engineering_rows,
            "total_steel_kg": self.stats.steel_total_kg,
            "diameter_summary_kg": self.stats.diameter_summary,
            "workbook_files": self.stats.workbook_files_generated,
            "worksheet_statistics": self.stats.worksheet_statistics,
        }

    def _known_differences(self) -> Dict[str, Any]:
        return {
            "cut_length": {
                "status": "COMPUTED",
                "method": "IS 456:2000 — 40d development length",
                "note": (
                    "Phase I cut lengths are DEFERRED (geometry unresolved). "
                    "V.B.1 derives cut lengths directly from L.2 span + IS 456 formulas."
                ),
            },
            "bbs": {
                "status": "GENERATED",
                "method": "L.2 bar data + IS 456 formulas",
                "note": (
                    "Phase I BBS records are FABRICATION_DEFERRED. "
                    "V.B.1 generates BBS independently from L.2 data."
                ),
            },
            "excel_comparison": {
                "status": "PARTIAL",
                "estimator_reference": "Galera_SteelBeamEst_SHR&OHT_TopFramingPan_OutputFormat.xlsx",
                "note": (
                    "Reference workbook uses OFFSET formulas (returns #REF! in data_only mode). "
                    "V.B.1 workbook uses computed values — comparison requires formula-aware reader."
                ),
            },
        }

    def _recommendations(self) -> List[str]:
        recs = [
            "Manual engineering review: open Estimation_Output.xlsx and verify beam steel weights.",
            "Compare B1 top bar weight: expected ~14.7 kg (2Y16, span=5.57m).",
            "Compare B1 stirrup weight: expected ~30-35 kg (57 stirrups Y8@100).",
            "Confirm development length assumption: 40d for Fe415/M25 (IS 456:2000 Table 65).",
            "Phase I geometry resolver should be upgraded to avoid DEFERRED cut lengths in future.",
        ]
        if self.val and not self.val.validation_passed:
            recs.insert(0, "PRIORITY: Re-run after fixing workbook validation errors.")
        return recs
