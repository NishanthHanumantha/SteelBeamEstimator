"""Phase QA.3 — Drawing vs Estimator Engineering Interpretation Audit runner."""

import _bootstrap  # noqa: F401

import sys
from pathlib import Path

from src.estimator_validation.drawing_interpretation.interpretation_builder import InterpretationAuditBuilder
from src.estimator_validation.drawing_interpretation.interpretation_exporter import InterpretationExporter
from src.estimator_validation.drawing_interpretation.interpretation_reporting import InterpretationReporting
from src.estimator_validation.drawing_interpretation.interpretation_summary import InterpretationSummary
from src.estimator_validation.drawing_interpretation.interpretation_types import default_paths
from src.estimator_validation.drawing_interpretation.interpretation_validator import InterpretationValidator


def run() -> int:
    project_root = Path.cwd()
    builder = InterpretationAuditBuilder(project_root)
    result = builder.build()
    result["engineering_code_modified"] = False
    result["engineering_pipeline_frozen"] = True
    result["parser_executed"] = False
    result["read_only_verification"] = True
    result["validates_engineering_interpretation"] = True
    result["validates_worksheet_structure"] = False

    summary = InterpretationSummary.build(result)
    result["interpretation_summary"] = summary
    validation = InterpretationValidator().validate(result)
    result["interpretation_validation"] = validation
    result["interpretation_report"] = InterpretationReporting.build(result, summary)

    output_dir = default_paths(project_root)["output_dir"]
    InterpretationExporter.export_all(output_dir, result)

    stats = result.get("interpretation_statistics", {})
    matrix = result.get("root_cause_matrix", {})

    print("\n" + "=" * 60)
    print("PHASE QA.3")
    print("Drawing vs Estimator Engineering Interpretation Audit")
    print("=" * 60)
    print(f"Estimator Workbook: {result['estimator_workbook']}")
    print(f"Interpretation Validation: {validation['status']} ({validation['summary']['total_checks']} checks)")
    print(f"Beams Analysed: {len(result.get('beam_marks', []))}")
    print(f"Concepts Compared: {stats.get('concept_count', 0)}")
    print(f"Interpretation Differences: {stats.get('interpretation_difference_count', 0)}")
    print(f"Engineering Decisions: {stats.get('engineering_decision_count', 0)}")
    print(f"Unknown Root Cause %: {matrix.get('unknown_pct', 0)}")
    print(f"Output Directory: {output_dir}")
    print("=" * 60 + "\n")
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(run())
