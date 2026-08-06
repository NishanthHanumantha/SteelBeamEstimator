#!/usr/bin/env python3
"""
run_phase_qa2b2_accuracy_report.py
Phase QA.2B.2 — Overall Accuracy Improvement Report
MODEL_VERSION: 9.6.2
"""
from __future__ import annotations

import sys
from pathlib import Path

_V9 = Path(__file__).resolve().parents[1]
_SRC = _V9 / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> int:
    from PhaseQA2B2_accuracy_report.report_builder import build_report

    template = (
        _V9.parent
        / "Version8"
        / "data"
        / "output"
        / "QA2A_GroundTruthBenchmark"
        / "Overall_Accuruacy_Report.docx"
    )
    qa2b1 = _V9 / "data" / "output" / "PhaseQA2B1_production_regeneration"
    out_dir = _V9 / "data" / "output" / "PhaseQA2B2_accuracy_report"
    out_docx = out_dir / "Overall_Accuracy_Report_V9.6.1.docx"

    if not template.exists():
        print(f"[ERROR] Template missing: {template}", file=sys.stderr)
        return 1
    if not (qa2b1 / "GroundTruth_Benchmark_Report.json").exists():
        print(f"[ERROR] QA.2B.1 benchmark missing under {qa2b1}", file=sys.stderr)
        return 1

    meta = build_report(
        template_path=template, qa2b1_dir=qa2b1, output_docx=out_docx
    )
    print(f"[QA.2B.2] wrote {meta['output']}")
    print(f"[QA.2B.2] improvement={meta['improvement']}")

    # Optional PDF if Word / docx2pdf available
    try:
        from docx2pdf import convert

        pdf = out_docx.with_suffix(".pdf")
        convert(str(out_docx), str(pdf))
        print(f"[QA.2B.2] wrote {pdf}")
    except Exception as exc:
        print(f"[QA.2B.2] PDF skipped ({exc})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
