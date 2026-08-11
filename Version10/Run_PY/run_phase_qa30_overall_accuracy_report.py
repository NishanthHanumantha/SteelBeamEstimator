#!/usr/bin/env python3
"""
run_phase_qa30_overall_accuracy_report.py
Build Overall Accuracy Word report for all six drawing sets
(First–Third from QA.2B.1 + Fourth–Sixth from QA.3.0).

MODEL_VERSION: 10.0.0

Usage (from Version10/):
  python Run_PY/run_phase_qa30_overall_accuracy_report.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_V10 = Path(__file__).resolve().parents[1]
_SRC = _V10 / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_V10) not in sys.path:
    sys.path.insert(0, str(_V10))


def main() -> int:
    import importlib.util

    # Import module file directly to avoid PhaseQA30 package __init__ side-effects.
    mod_path = _SRC / "PhaseQA30_unseen_benchmark" / "overall_accuracy_docx.py"
    spec = importlib.util.spec_from_file_location("overall_accuracy_docx", mod_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    build_report = mod.build_report

    repo = _V10.parent
    template = (
        repo
        / "Version8"
        / "data"
        / "output"
        / "QA2A_GroundTruthBenchmark"
        / "Overall_Accuruacy_Report.docx"
    )
    qa2b1_json = (
        repo
        / "Version9"
        / "data"
        / "output"
        / "PhaseQA2B1_production_regeneration"
        / "GroundTruth_Benchmark_Report.json"
    )
    qa30_root = _V10 / "data" / "output" / "PhaseQA30_unseen_benchmark"
    qa30_json = qa30_root / "Generalization_Benchmark_Report.json"
    out_docx = qa30_root / "Overall_Accuracy_Report_All_Six_Sets_V10.docx"

    if not template.exists():
        print(f"[ERROR] Template missing: {template}", file=sys.stderr)
        return 1
    if not qa2b1_json.exists():
        print(f"[ERROR] QA.2B.1 report missing: {qa2b1_json}", file=sys.stderr)
        return 1
    if not qa30_json.exists():
        print(f"[ERROR] QA.3.0 report missing: {qa30_json}", file=sys.stderr)
        return 1

    print("[QA.3.0] building six-set Overall Accuracy Word report...", flush=True)
    meta = build_report(
        template_path=template,
        qa2b1_json=qa2b1_json,
        qa30_json=qa30_json,
        qa30_root=qa30_root,
        output_docx=out_docx,
    )
    c = meta["combined_all_six"]
    print(f"[QA.3.0] wrote {meta['output']}")
    print(f"[QA.3.0] all_six_overall={c['overall_accuracy_pct']:.2f}%")
    print(f"[QA.3.0] beam={c['beam_detection_pct']:.2f}% bar_det={c['bar_detection_pct']:.2f}%")
    print(f"[QA.3.0] bar_match={c['bar_accuracy_pct']:.2f}% steel={c['steel_accuracy_pct']:.2f}%")
    print(f"[QA.3.0] known_overall={meta['known_first_third']['overall_accuracy_pct']:.2f}%")
    print(f"[QA.3.0] unseen_overall={meta['unseen_fourth_sixth']['overall_accuracy_pct']:.2f}%")

    # PDF conversion is optional and can hang if Word COM is unavailable.
    # Generate Word/.md/.meta only by default.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
