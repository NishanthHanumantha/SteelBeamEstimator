"""
execution_reporter.py — 9-section V.RUN.1 engineering report builder.
MODEL_VERSION: 7.2.0
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import List
from . import MODEL_VERSION, PHASE_ID, PHASE_TITLE
from .pipeline_execution_models import StageResult


class ExecutionReporter:

    def build(
        self,
        stages:        List[StageResult],
        propagation:   List[dict],
        freshness:     dict,
        statistics:    dict,
        validation:    List[dict],
        stale_archives: list,
        workbook_path: str,
    ) -> dict:
        failed_stages = [s for s in stages if s.status != "SUCCESS"]
        passed_rules  = sum(1 for v in validation if v.get("status") == "PASS")
        failed_rules  = sum(1 for v in validation if v.get("status") == "FAIL")
        overall       = "SUCCESS" if not failed_stages and failed_rules == 0 else "PARTIAL" if failed_stages else "SUCCESS"

        return {
            "phase":         PHASE_ID,
            "title":         PHASE_TITLE,
            "model_version": MODEL_VERSION,
            "generated_at":  datetime.now(timezone.utc).isoformat(),
            "sections": {
                "1_executive_summary": {
                    "overall_status":      overall,
                    "stages_executed":     len(stages),
                    "stages_successful":   len(stages) - len(failed_stages),
                    "stages_failed":       len(failed_stages),
                    "initial_beam_count":  statistics.get("initial_beam_count", 0),
                    "final_beam_count":    statistics.get("final_beam_count", 0),
                    "total_duration_s":    statistics.get("total_duration_s", 0),
                    "workbook_generated":  bool(workbook_path),
                    "workbook_path":       workbook_path,
                    "validation_pass":     passed_rules,
                    "validation_fail":     failed_rules,
                },
                "2_pipeline_execution_summary": {
                    "stage_order": [s.stage_id for s in stages],
                    "stage_status": {s.stage_id: s.status for s in stages},
                    "stage_durations": {s.stage_id: s.duration_s for s in stages},
                    "stale_files_archived": sum(a["file_count"] for a in stale_archives),
                },
                "3_stage_results": [s.to_dict() for s in stages],
                "4_beam_count_propagation": propagation,
                "5_freshness_validation": freshness,
                "6_workbook_generation": {
                    "workbook_path":   workbook_path,
                    "generated":       bool(workbook_path),
                    "vb1_files":       statistics.get("workbook_files", []),
                },
                "7_engineering_outputs": {
                    "total_json_files":   statistics.get("total_json_files", 0),
                    "artefact_counts":    statistics.get("artefact_counts", {}),
                },
                "8_remaining_issues": self._remaining_issues(stages, propagation, freshness),
                "9_production_readiness": self._production_readiness(stages, propagation, freshness),
            },
            "validation":  validation,
            "statistics":  statistics,
        }

    def _remaining_issues(self, stages, propagation, freshness) -> list:
        issues = []
        for s in stages:
            if s.status != "SUCCESS":
                issues.append({
                    "severity": "ERROR",
                    "stage":    s.stage_id,
                    "issue":    f"Stage failed with exit code {s.exit_code}",
                    "stderr":   s.stderr_tail[-300:],
                })
        for row in propagation:
            if row.get("lost_beams"):
                issues.append({
                    "severity": "WARNING",
                    "stage":    row["stage_id"],
                    "issue":    f"{len(row['lost_beams'])} beams lost: {row['lost_beams'][:10]}",
                })
        if freshness.get("stale_artefacts", 0) > 0:
            issues.append({
                "severity": "WARNING",
                "issue":    f"{freshness['stale_artefacts']} artefacts still stale after run.",
            })
        return issues if issues else [{"severity": "NONE", "issue": "No remaining issues."}]

    def _production_readiness(self, stages, propagation, freshness) -> dict:
        all_success = all(s.status == "SUCCESS" for s in stages)
        all_fresh   = freshness.get("stale_artefacts", 1) == 0
        final_cnt   = next((r["beam_count"] for r in reversed(propagation) if r.get("beam_count", 0) > 0), 0)
        ready       = all_success and final_cnt > 0

        return {
            "ready":             ready,
            "all_stages_pass":   all_success,
            "all_artefacts_fresh": all_fresh,
            "final_beam_count":  final_cnt,
            "verdict": (
                "PRODUCTION READY. All stages completed successfully. "
                f"Fresh artefacts generated for {final_cnt} Benchmark Set 2 beams."
                if ready
                else "NOT PRODUCTION READY. Review remaining issues above."
            ),
        }
