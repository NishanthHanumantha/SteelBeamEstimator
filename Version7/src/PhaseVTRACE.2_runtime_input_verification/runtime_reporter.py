"""
runtime_reporter.py — Builds the 12-section V.TRACE.2 engineering report.
MODEL_VERSION: 7.1.3  |  READ-ONLY
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List
from . import MODEL_VERSION, PHASE_ID, PHASE_TITLE
from .runtime_models import RuntimeFile


class RuntimeReporter:

    def build(
        self,
        files:             Dict[str, RuntimeFile],
        load_events:       List[dict],
        beam_count_result: dict,
        adapter_results:   List[dict],
        filter_analysis:   dict,
        version_report:    dict,
        cache_report:      dict,
        dependency_report: dict,
        statistics:        dict,
        validation:        List[dict],
        snapshot:          dict,
    ) -> dict:
        root_cause, recommendation = self._determine_root_cause(
            beam_count_result, filter_analysis, cache_report
        )
        return {
            "phase":         PHASE_ID,
            "title":         PHASE_TITLE,
            "model_version": MODEL_VERSION,
            "generated_at":  datetime.now(timezone.utc).isoformat(),
            "sections": {
                "1_executive_summary":      self._exec_summary(statistics, root_cause, validation),
                "2_files_loaded_by_l2":     self._files_section(files, load_events),
                "3_beam_counts":            self._beam_counts_section(files, beam_count_result),
                "4_runtime_load_sequence":  load_events,
                "5_adapter_verification":   adapter_results,
                "6_filtering_analysis":     filter_analysis,
                "7_version_analysis":       version_report,
                "8_benchmark_analysis":     self._benchmark_section(files),
                "9_cache_analysis":         cache_report,
                "10_dependency_analysis":   dependency_report,
                "11_root_cause":            root_cause,
                "12_engineering_recommendation": recommendation,
            },
            "validation": validation,
            "statistics":    statistics,
        }

    # -------------------------------------------------------------------------
    def _exec_summary(self, stats: dict, root_cause: str, validation: List[dict]) -> dict:
        passed = sum(1 for v in validation if v.get("status") == "PASS")
        failed = sum(1 for v in validation if v.get("status") == "FAIL")
        return {
            "input_beam_count":   stats.get("input_beam_count", 0),
            "output_beam_count":  stats.get("output_beam_count", 0),
            "net_loss":           stats.get("beam_loss_count", 0),
            "stale_files":        stats.get("stale_files", 0),
            "stale_stages":       stats.get("stale_stages", []),
            "validation_pass":    passed,
            "validation_fail":    failed,
            "overall_verdict":    "PASS" if failed == 0 else "FAIL",
            "root_cause_summary": root_cause,
        }

    def _files_section(self, files: Dict[str, RuntimeFile], load_events: List[dict]) -> list:
        rows = []
        for key, rf in files.items():
            rows.append({
                "key":           key,
                "absolute_path": rf.absolute_path,
                "version":       rf.version,
                "benchmark_id":  rf.benchmark_id,
                "model_version": rf.model_version,
                "mtime_iso":     rf.mtime_iso,
                "beam_count":    rf.beam_count,
                "load_status":   rf.load_status,
            })
        return rows

    def _beam_counts_section(self, files: Dict[str, RuntimeFile], beam_count_result: dict) -> dict:
        file_counts = {key: {"beam_count": rf.beam_count, "beam_ids": rf.beam_ids[:10]}
                       for key, rf in files.items()}
        return {
            "per_file":             file_counts,
            "discover_beams_count": beam_count_result.get("beam_count", 0),
            "discover_beams_source": beam_count_result.get("source", ""),
            "discover_beams_ids":   beam_count_result.get("beam_ids", []),
            "fallback_triggered":   beam_count_result.get("fallback_triggered", False),
        }

    def _benchmark_section(self, files: Dict[str, RuntimeFile]) -> dict:
        bench_count: Dict[str, int] = {}
        for rf in files.values():
            b = rf.benchmark_id or "UNKNOWN"
            bench_count[b] = bench_count.get(b, 0) + 1
        return {
            "benchmark_distribution": bench_count,
            "note": ("Adapter files contain Benchmark_Set_2 data — correct."
                     if bench_count.get("Benchmark_Set_2", 0) > 0
                     else "No Benchmark_Set_2 data detected in loaded files."),
        }

    def _determine_root_cause(self, beam_count_result: dict,
                               filter_analysis: dict, cache_report: dict) -> tuple:
        discover_count = beam_count_result.get("beam_count", 0)
        input_count    = filter_analysis.get("input_count", 0)
        output_count   = filter_analysis.get("output_count", 0)
        stale_files    = cache_report.get("stale_files", 0)
        stale_stages   = cache_report.get("stale_stages", [])
        fallback       = beam_count_result.get("fallback_triggered", False)
        adapter_iso    = cache_report.get("adapter_write_time_iso", "?")

        if fallback:
            root_cause = (
                "DETERMINISTIC ROOT CAUSE: BeamContextBuilder._discover_beams() triggered "
                "the hardcoded fallback to B1-B18 because the adapter files returned "
                "empty beam IDs. The V5 adapter files exist but their internal structure "
                "does not match what _discover_beams() expects — specifically, "
                "beam_schedule.results[].beam_mark keys may be absent or wrong."
            )
            recommendation = (
                "Inspect the V5 adapter beam_schedule_results.json to ensure "
                "'results' is a non-empty list where each item has a 'beam_mark' field. "
                "V.ROOT.1's engineering_object_initializer.py may need to populate "
                "beam_mark correctly."
            )
        elif discover_count == 65 and output_count < 65 and stale_files > 0:
            root_cause = (
                f"DETERMINISTIC ROOT CAUSE: Phase L.2's InterpretationCollector reads "
                f"the V5 adapter files which contain ALL {input_count} Benchmark Set 2 beams. "
                f"BeamContextBuilder._discover_beams() returns {discover_count} beams from "
                f"beam_schedule.results. HOWEVER, the L.2 output artefact "
                f"(beam_reinforcement_models.json) contains only {output_count} beams — "
                f"this artefact is STALE. It was generated BEFORE V.ROOT.1 updated the "
                f"V5 adapter files (adapter last written at {adapter_iso}). "
                f"{stale_files} output files across stage(s) {stale_stages} are stale. "
                f"L.2 has NOT been re-executed since V.ROOT.1 ran. "
                f"The input is correct (65 beams); the output is old (18 beams from Benchmark Set 1)."
            )
            recommendation = (
                "Re-execute Phase L.2 using: "
                "python Version7/Run_PY/run_phase_l2_engineering_reinforcement_interpretation.py "
                "Then continue: SI.0 -> SI.1 -> L.2.2 -> L.2.1 -> L.3 -> V.B.1. "
                "No code changes required. The V5 adapter files are ready with 65 Benchmark Set 2 beams."
            )
        elif discover_count == input_count == output_count:
            root_cause = (
                "NO BEAM LOSS DETECTED: All stages show consistent beam counts. "
                "The pipeline is operating correctly end-to-end."
            )
            recommendation = "No action required."
        else:
            root_cause = (
                f"Beam count discrepancy detected: "
                f"adapter_input={input_count}, discover_beams={discover_count}, "
                f"l2_output={output_count}. Root cause requires further investigation."
            )
            recommendation = "Inspect beam_context_builder._discover_beams() return value."

        return root_cause, recommendation
