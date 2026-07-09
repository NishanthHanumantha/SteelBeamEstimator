"""Phase QA.2 — Engineering Object Trace & Matching Engine runner."""

import _bootstrap  # noqa: F401

import sys
from pathlib import Path

from src.estimator_validation.object_trace.trace_engine import TraceEngine
from src.estimator_validation.object_trace.trace_exporter import TraceExporter
from src.estimator_validation.object_trace.trace_reporting import TraceReporting
from src.estimator_validation.object_trace.trace_summary import TraceSummary
from src.estimator_validation.object_trace.trace_types import default_paths
from src.estimator_validation.object_trace.trace_validator import TraceValidator


def run() -> int:
    project_root = Path.cwd()
    engine = TraceEngine(project_root)
    result = engine.run()
    result["engineering_code_modified"] = False
    result["engineering_pipeline_frozen"] = True
    result["positional_matching_used"] = False

    summary = TraceSummary.build(result)
    result["trace_summary"] = summary
    validation = TraceValidator().validate(result)
    result["trace_validation"] = validation
    result["trace_report"] = TraceReporting.build(result, summary)

    output_dir = default_paths(project_root)["output_dir"]
    TraceExporter.export_all(output_dir, result)

    stats = result.get("trace_statistics", {})
    qa1 = result.get("qa1_validation", {})
    matrix = result.get("root_cause_matrix", {})

    print("\n" + "=" * 60)
    print("PHASE QA.2")
    print("Engineering Object Trace & Matching Engine")
    print("=" * 60)
    print(f"Generated Workbook: {result['generated_workbook']}")
    print(f"Estimator Workbook: {result['estimator_workbook']}")
    print(f"Trace Validation: {validation['status']} ({validation['summary']['total_checks']} checks)")
    print(f"Rows Traced: {stats.get('total_estimator_rows_traced', 0)}")
    print(f"Trace Pass/Fail: {stats.get('trace_pass_count', 0)}/{stats.get('trace_fail_count', 0)}")
    print(f"Identity Excel Pass Rows: {qa1.get('identity_excel_pass_rows', 0)}")
    print(f"QA.1 matching_rows=0 Validated: {qa1.get('qa1_matching_rows_zero')}")
    print(f"Unknown Root Cause %: {matrix.get('unknown_pct', 0)}")
    print(f"Output Directory: {output_dir}")
    print("=" * 60 + "\n")
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(run())
