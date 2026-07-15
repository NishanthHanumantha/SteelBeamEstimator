"""
runtime_statistics.py — Aggregates all runtime verification statistics.
MODEL_VERSION: 7.1.3  |  READ-ONLY
"""

from __future__ import annotations
from typing import Dict, List
from .runtime_models import RuntimeFile


class RuntimeStatisticsEngine:

    def compute(
        self,
        files:            Dict[str, RuntimeFile],
        adapter_results:  List[dict],
        load_events:      List[dict],
        filter_analysis:  dict,
        cache_report:     dict,
        dependency_report: dict,
    ) -> dict:
        loaded  = sum(1 for f in files.values() if f.load_status == "LOADED")
        missing = sum(1 for f in files.values() if f.load_status == "MISSING")
        total   = len(files)

        versions = {}
        for f in files.values():
            v = f.version or "UNKNOWN"
            versions[v] = versions.get(v, 0) + 1

        bench = {}
        for f in files.values():
            b = f.benchmark_id or "UNKNOWN"
            bench[b] = bench.get(b, 0) + 1

        adapter_pass = sum(1 for r in adapter_results if r.get("status") == "PASS")

        input_count  = filter_analysis.get("input_count", 0)
        output_count = filter_analysis.get("output_count", 0)
        loss_pct     = round((input_count - output_count) / input_count * 100, 1) if input_count else 0.0

        return {
            "files_total":           total,
            "files_loaded":          loaded,
            "files_missing":         missing,
            "unique_json_files":     len(load_events),
            "version_distribution":  versions,
            "benchmark_distribution": bench,
            "adapter_checks_pass":   adapter_pass,
            "adapter_checks_total":  len(adapter_results),
            "input_beam_count":      input_count,
            "output_beam_count":     output_count,
            "beam_loss_count":       input_count - output_count,
            "beam_loss_pct":         loss_pct,
            "stale_files":           cache_report.get("stale_files", 0),
            "stale_stages":          cache_report.get("stale_stages", []),
            "critical_dependencies": dependency_report.get("critical_findings", 0),
        }
