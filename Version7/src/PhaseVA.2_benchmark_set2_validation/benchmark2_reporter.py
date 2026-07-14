"""
Phase V.A.2 -- benchmark2_reporter.py
Build the 10-section benchmark report comparing Set 1 vs Set 2.
MODEL_VERSION: 7.0.0
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from benchmark2_models import (
    Benchmark2Manifest,
    BenchmarkSetComparison,
    EngineeringKPIs,
    FullBenchmark2Result,
    PipelineRunResult,
    WorkbookComparison,
    WorkbookValidation,
)

# Benchmark Set 1 (MODEL_VERSION 6.6.3) hardcoded KPIs from V.A.1.1
_SET1_KPIS: Dict[str, Any] = {
    "model_version": "6.6.3",
    "benchmark_id": "BENCHMARK::DRAWING_1_V6",
    "drawing_name": "Beam_Reinforcement_Details (Clubhouse GF)",
    "total_beams": 18,
    "total_steel_kg": 2027.94,
    "stirrup_coverage_beams": 18,
    "bbs_completeness_pct": 0.0,
    "pipeline_success_rate_pct": 100.0,
    "workbook_generated": True,
    "stages_passed": 6,
    "has_estimator_reference": True,
}


class Benchmark2Reporter:
    """Generate the 10-section Benchmark Set 2 validation report."""

    def build_report(self, result: FullBenchmark2Result) -> Dict[str, Any]:
        return {
            "phase": "V.A.2",
            "phase_name": "End-to-End Validation (Benchmark Set 2)",
            "model_version": result.model_version,
            "benchmark_id": result.benchmark_id,
            "generated_at": datetime.now().isoformat(),
            "overall_passed": result.overall_passed,
            "rules_passed": result.rules_passed,
            "validation_errors": result.validation_errors,
            "1_executive_summary": self._executive_summary(result),
            "2_pipeline_summary": self._pipeline_summary(result.pipeline),
            "3_benchmark_set2_results": self._set2_results(result),
            "4_workbook_validation": self._workbook_validation(result.workbook_validation),
            "5_engineering_accuracy": self._engineering_accuracy(result.engineering_kpis),
            "6_set1_vs_set2_comparison": self._set1_vs_set2(result.set_comparison),
            "7_generalization_assessment": result.generalization_assessment or {},
            "8_recurring_engineering_issues": self._recurring_issues(result.recurring_issues),
            "9_drawing_specific_issues": self._drawing_specific(result.drawing_specific_issues, result.manifest),
            "10_recommendations": self._recommendations(result.recommendations),
        }

    # ------------------------------------------------------------------
    def _executive_summary(self, r: FullBenchmark2Result) -> Dict[str, Any]:
        pipeline = r.pipeline
        kpis     = r.engineering_kpis
        manifest = r.manifest
        return {
            "model_version": r.model_version,
            "benchmark_id": r.benchmark_id,
            "drawing_name": manifest.drawing_name if manifest else "UNKNOWN",
            "total_input_files": manifest.total_files if manifest else 0,
            "has_estimator_reference": manifest.has_estimator_excel if manifest else False,
            "pipeline_passed": pipeline.pipeline_passed if pipeline else False,
            "stages_passed": pipeline.stages_passed if pipeline else 0,
            "stages_failed": pipeline.stages_failed if pipeline else 0,
            "total_elapsed_s": pipeline.total_elapsed_seconds if pipeline else 0.0,
            "workbook_generated": r.workbook_validation.exists if r.workbook_validation else False,
            "workbook_readable": r.workbook_validation.readable if r.workbook_validation else False,
            "total_beams": kpis.total_beams if kpis else 0,
            "total_steel_kg": kpis.total_steel_kg if kpis else 0.0,
            "stirrup_coverage_beams": kpis.stirrup_coverage_beams if kpis else 0,
            "generalization_score": r.generalization_assessment.get("classification", "UNKNOWN") if r.generalization_assessment else "UNKNOWN",
            "overall_passed": r.overall_passed,
            "critical_finding": (
                "The production pipeline (MODEL_VERSION 6.6.3) is tightly coupled to "
                "Benchmark Set 1 pre-processed data (Version5 engineering/reinforcement objects). "
                "Benchmark Set 2 DXF files (Galera GF drawings) were not processed by the "
                "underlying DXF parsing infrastructure. The pipeline executed using the same "
                "Version5 dataset, producing outputs equivalent to Benchmark Set 1. "
                "New DXF parsing infrastructure is required to generalise to new drawings."
            ),
        }

    def _pipeline_summary(self, pipeline: PipelineRunResult) -> Dict[str, Any]:
        if not pipeline:
            return {"status": "NOT_RUN"}
        stages = []
        for s in pipeline.stages:
            stages.append({
                "stage": s.stage_name,
                "success": s.success,
                "elapsed_s": s.elapsed_seconds,
                "exit_code": s.exit_code,
                "output_files_count": len(s.output_files),
            })
        return {
            "total_stages": pipeline.stages_executed,
            "stages_passed": pipeline.stages_passed,
            "stages_failed": pipeline.stages_failed,
            "success_rate_pct": pipeline.success_rate_pct,
            "total_elapsed_s": pipeline.total_elapsed_seconds,
            "pipeline_passed": pipeline.pipeline_passed,
            "stages": stages,
        }

    def _set2_results(self, r: FullBenchmark2Result) -> Dict[str, Any]:
        kpis = r.engineering_kpis
        return {
            "drawing": r.manifest.drawing_name if r.manifest else "UNKNOWN",
            "source_folder": r.manifest.source_folder if r.manifest else "",
            "dxf_files": [
                {"filename": f.filename, "type": f.file_type, "size_bytes": f.size_bytes}
                for f in (r.manifest.files if r.manifest else [])
                if "DXF" in f.file_type
            ],
            "estimator_excel_available": r.manifest.has_estimator_excel if r.manifest else False,
            "pipeline_execution": {
                "passed": r.pipeline.pipeline_passed if r.pipeline else False,
                "success_rate_pct": r.pipeline.success_rate_pct if r.pipeline else 0.0,
            },
            "workbook_generated": r.workbook_validation.exists if r.workbook_validation else False,
            "engineering_kpis": {
                "total_beams": kpis.total_beams if kpis else 0,
                "total_steel_kg": kpis.total_steel_kg if kpis else 0.0,
                "stirrup_coverage_beams": kpis.stirrup_coverage_beams if kpis else 0,
                "bbs_completeness_pct": kpis.bbs_completeness_pct if kpis else 0.0,
            },
            "generalization_limitation": (
                "Benchmark Set 2 drawings (Galera GF) were catalogued but the pipeline "
                "could not independently parse them. The pipeline used pre-existing "
                "Version5 data (Benchmark Set 1) as its primary input. See Section 7 "
                "for generalization assessment."
            ),
        }

    def _workbook_validation(self, wv: WorkbookValidation) -> Dict[str, Any]:
        if not wv:
            return {"status": "NOT_RUN"}
        return {
            "workbook_path": wv.workbook_path,
            "exists": wv.exists,
            "readable": wv.readable,
            "size_kb": wv.size_kb,
            "total_sheets": wv.total_sheets,
            "sheet_names": wv.sheet_names,
            "total_rows": wv.total_rows,
            "has_data": wv.has_data,
            "validation_passed": wv.validation_passed,
            "issues": wv.issues,
            "worksheets": [
                {
                    "name": ws.sheet_name,
                    "rows": ws.row_count,
                    "cols": ws.col_count,
                    "has_data": ws.has_data_rows,
                    "passed": ws.validation_passed,
                }
                for ws in wv.worksheet_validations
            ],
        }

    def _engineering_accuracy(self, kpis: EngineeringKPIs) -> Dict[str, Any]:
        if not kpis:
            return {"status": "NOT_RUN"}
        return {
            "total_beams": kpis.total_beams,
            "total_engineering_rows": kpis.total_engineering_rows,
            "total_bbs_rows": kpis.total_bbs_rows,
            "total_steel_kg": kpis.total_steel_kg,
            "stirrup_coverage_beams": kpis.stirrup_coverage_beams,
            "bbs_completeness_pct": kpis.bbs_completeness_pct,
            "diameter_totals_kg": kpis.diameter_totals_kg,
            "data_source": kpis.data_source,
            "note": (
                "KPIs derived from Version7 production output. "
                "Values reflect execution on shared Version5 data (Benchmark Set 1 drawings)."
            ),
        }

    def _set1_vs_set2(self, sc: BenchmarkSetComparison) -> Dict[str, Any]:
        if not sc:
            return {"status": "NOT_RUN"}
        return {
            "set1_id": sc.set1_id,
            "set2_id": sc.set2_id,
            "generalization_score": sc.generalization_score,
            "stable_behaviours": sc.stable_behaviours,
            "new_failure_modes": sc.new_failure_modes,
            "drawing_specific_issues": sc.drawing_specific_issues,
            "common_issues": sc.common_issues,
            "metric_comparisons": [
                {
                    "metric": m.metric_name,
                    "set1": m.set1_value,
                    "set2": m.set2_value,
                    "delta": m.delta,
                    "status": m.status,
                }
                for m in sc.metric_comparisons
            ],
        }

    def _recurring_issues(self, issues: List[str]) -> Dict[str, Any]:
        return {
            "count": len(issues),
            "issues": issues,
        }

    def _drawing_specific(self, issues: List[str], manifest: Benchmark2Manifest) -> Dict[str, Any]:
        name = manifest.drawing_name if manifest else "UNKNOWN"
        return {
            "drawing": name,
            "issue_count": len(issues),
            "issues": issues,
        }

    def _recommendations(self, recs: List[str]) -> Dict[str, Any]:
        return {
            "count": len(recs),
            "recommendations": recs,
        }
