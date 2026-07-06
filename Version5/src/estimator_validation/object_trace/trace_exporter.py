"""Engineering trace exporter — Phase QA.2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TraceExporter:
    @staticmethod
    def export_all(output_dir: Path, trace_result: dict[str, Any]) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        mapping = {
            "engineering_trace.json": {
                "phase": trace_result.get("phase"),
                "trace_version": trace_result.get("trace_version"),
                "traces": trace_result.get("engineering_traces", []),
                "trace_count": len(trace_result.get("engineering_traces", [])),
            },
            "engineering_trace_registry.json": trace_result.get("trace_registry"),
            "identity_matching.json": trace_result.get("identity_matching"),
            "geometry_comparison.json": trace_result.get("geometry_comparison"),
            "qa1_validation_report.json": trace_result.get("qa1_validation"),
            "trace_statistics.json": trace_result.get("trace_statistics"),
            "trace_summary.json": trace_result.get("trace_summary"),
            "trace_validation.json": trace_result.get("trace_validation"),
            "trace_report.json": trace_result.get("trace_report"),
            "root_cause_matrix.json": trace_result.get("root_cause_matrix"),
        }
        for filename, payload in mapping.items():
            if payload is not None:
                path = output_dir / filename
                path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
