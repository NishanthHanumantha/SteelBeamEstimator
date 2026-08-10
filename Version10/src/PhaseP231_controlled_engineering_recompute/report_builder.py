"""
Write P2.3.1 artefacts.
MODEL_VERSION: 10.5.6
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .config import MODEL_VERSION, PHASE_ID, REFERENCE_POSITIVE_KEY


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def write_all(out_root: Path, artefacts: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}

    mapping = {
        "benchmark_baseline.json": artefacts.get("baseline_bench"),
        "benchmark_controlled.json": artefacts.get("controlled_bench"),
        "baseline_vs_controlled.json": artefacts.get("comparison"),
        "B16_engineering_comparison.json": artefacts.get("b16_trace"),
        "ownership_comparison.json": artefacts.get("ownership_comparison"),
        "migration_provenance.json": artefacts.get("migration_provenance"),
        "phase_p23_1_summary.json": artefacts.get("summary"),
        "P231_unit_tests.json": artefacts.get("unit_tests"),
        "P231_determinism.json": artefacts.get("determinism"),
        "P231_gates.json": artefacts.get("gates"),
        "RegressionReport.json": artefacts.get("regression"),
    }
    for name, obj in mapping.items():
        p = out_root / name
        _dump(p, obj)
        paths[name] = str(p)

    report = _final_report(artefacts)
    (out_root / "P231_CONTROLLED_ENGINEERING_REPORT.md").write_text(report, encoding="utf-8")
    paths["P231_CONTROLLED_ENGINEERING_REPORT.md"] = str(
        out_root / "P231_CONTROLLED_ENGINEERING_REPORT.md"
    )
    (out_root / "README.md").write_text(_readme(), encoding="utf-8")
    paths["README.md"] = str(out_root / "README.md")
    return paths


def _final_report(a: Dict[str, Any]) -> str:
    g = a.get("gates") or {}
    c = a.get("comparison") or {}
    wb = c.get("workbook") or {}
    q = c.get("qa30_fourth") or {}
    b16 = a.get("b16_trace") or {}
    return "\n".join(
        [
            f"# PHASE {PHASE_ID}",
            f"MODEL_VERSION: {MODEL_VERSION}",
            "",
            f"Status: {g.get('status')}",
            f"Decision: {g.get('decision')}",
            "",
            "## Baseline",
            f"- ownership: `{c.get('ownership', {}).get('baseline')}`",
            f"- steel quantity: `{wb.get('steel_kg', {}).get('baseline')} kg`",
            f"- steel accuracy: `{q.get('Steel Accuracy', {}).get('baseline')}%`",
            f"- overall accuracy: `{q.get('Overall Accuracy', {}).get('baseline')}%`",
            "",
            "## Controlled",
            f"- ownership: `{c.get('ownership', {}).get('controlled')}`",
            f"- steel quantity: `{wb.get('steel_kg', {}).get('controlled')} kg`",
            f"- steel accuracy: `{q.get('Steel Accuracy', {}).get('controlled')}%`",
            f"- overall accuracy: `{q.get('Overall Accuracy', {}).get('controlled')}%`",
            "",
            "## Delta",
            f"- steel quantity: `{wb.get('steel_kg', {}).get('delta')} kg`",
            f"- steel accuracy: `{q.get('Steel Accuracy', {}).get('delta_pp')} pp`",
            f"- overall accuracy: `{q.get('Overall Accuracy', {}).get('delta_pp')} pp`",
            "",
            f"## B16 ({REFERENCE_POSITIVE_KEY})",
            f"- effect: `{b16.get('effect_class')}`",
            f"- meaning: {b16.get('effect_meaning')}",
            "",
            f"Unexpected migrations: `{(a.get('migration_provenance') or {}).get('unexpected_count', 0)}`",
            f"Contamination: `{'FOUND' if a.get('contamination_found') else 'NONE'}`",
            f"Regression: `{(a.get('regression') or {}).get('status')}`",
            f"Determinism: `{(a.get('determinism') or {}).get('determinism_status')}`",
            f"QA.3.0: `{'PASS' if (a.get('baseline_bench') or {}).get('compared') and (a.get('controlled_bench') or {}).get('compared') else 'FAIL'}`",
            f"Broader E validation: `{g.get('broader_e_validation')}`",
            "",
            "## Recommendation",
            "",
            g.get("recommendation") or "",
            "",
            "## Architectural note",
            "",
            b16.get("architectural_note") or "",
            "",
        ]
    )


def _readme() -> str:
    return "\n".join(
        [
            "# PhaseP231_controlled_engineering_recompute",
            "",
            f"MODEL_VERSION: `{MODEL_VERSION}`",
            "",
            "Controlled engineering recompute / steel re-benchmark for P2.3 E candidate.",
            "",
            "```",
            "python Run_PY/run_phase_p23_1_controlled_engineering_recompute.py --mode controlled",
            "```",
            "",
        ]
    )
