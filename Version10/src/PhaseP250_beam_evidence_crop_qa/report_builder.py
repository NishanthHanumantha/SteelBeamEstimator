"""
Markdown / JSON reports for P2.5.0.
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def write_reports(
    out_root: Path,
    *,
    metrics: Dict[str, Any],
    beam_rows: List[Dict[str, Any]],
    determinism: Dict[str, Any],
    regression: Dict[str, Any],
    meta: Dict[str, Any],
    architecture: Dict[str, Any],
) -> None:
    out_root = Path(out_root)
    (out_root / "summary").mkdir(parents=True, exist_ok=True)
    (out_root / "metrics").mkdir(parents=True, exist_ok=True)
    (out_root / "diagnostics").mkdir(parents=True, exist_ok=True)
    (out_root / "reports").mkdir(parents=True, exist_ok=True)

    _dump(out_root / "metrics" / "P250_metrics.json", metrics)
    _dump(out_root / "summary" / "BeamMatrix.json", {"beams": beam_rows})
    _dump(out_root / "diagnostics" / "P250_determinism.json", determinism)
    _dump(out_root / "diagnostics" / "RegressionReport.json", regression)
    _dump(out_root / "summary" / "P250_run_meta.json", meta)
    _dump(out_root / "reports" / "ArchitectureReuse.json", architecture)

    # CSV matrix
    cols = [
        "beam_id",
        "beam_present",
        "reinforcement_present",
        "annotation_present",
        "leader_present",
        "leader_chain_complete",
        "evidence_clipped",
        "neighbour_ambiguity",
        "crop_qa_overall",
        "expanded",
        "pipeline_annotation_coverage_pct",
        "pipeline_leader_coverage_pct",
        "pipeline_reinforcement_coverage_pct",
        "gt_bar_count",
        "gt_reinforcement_evidence_present",
        "engineering_crop",
        "evidence_overlay",
    ]
    with (out_root / "summary" / "BeamMatrix.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in beam_rows:
            w.writerow({k: r.get(k) for k in cols})

    # Summary MD
    lines = [
        "# P2.5.0 Beam Evidence Rendering & Crop QA",
        "",
        f"- MODEL_VERSION: `{meta.get('model_version')}`",
        f"- SCOPE: `{meta.get('scope')}`",
        f"- MODE: `{meta.get('mode')}`",
        f"- ENGINEERING_CHANGES: `{meta.get('engineering_changes')}`",
        "",
        "## Summary metrics",
        "",
        f"1. MODEL_VERSION: `{meta.get('model_version')}`",
        f"2. Fourth Set beams processed: **{metrics.get('beams_processed')}**",
        f"3. Successful renders: **{metrics.get('successful_renders')}**",
        f"4. Failed renders: **{metrics.get('failed_renders')}**",
        f"5. Crop QA pass %: **{metrics.get('crop_qa_pass_pct')}%**",
        f"6. Beam presence %: **{metrics.get('beam_presence_pct')}%**",
        f"7. Reinforcement evidence coverage: **{metrics.get('reinforcement_evidence_coverage_pct')}%**",
        f"8. Annotation evidence coverage: **{metrics.get('annotation_evidence_coverage_pct')}%**",
        f"9. Leader evidence coverage: **{metrics.get('leader_evidence_coverage_pct')}%**",
        f"10. Leader-chain completeness: **{metrics.get('leader_chain_completeness_pct')}%**",
        f"11. Evidence recall (GT-supported reinforcement presence): "
        f"**{(metrics.get('gt_verified') or {}).get('gt_reinforcement_presence_pct')}%** "
        f"— {(metrics.get('gt_verified') or {}).get('note')}",
        f"12. Beams requiring crop expansion: **{metrics.get('beams_requiring_crop_expansion')}**",
        f"13. Clipped evidence cases: **{metrics.get('clipped_evidence_cases')}**",
        f"14. Neighboring-beam ambiguity cases: **{metrics.get('neighbor_ambiguity_cases')}**",
        f"15. Rendering failures: **{metrics.get('rendering_failures')}**",
        f"16. Top crop/evidence failure causes: "
        f"`{metrics.get('top_crop_evidence_failure_causes')}`",
        "",
        f"- Determinism: **{determinism.get('determinism_status')}**",
        f"- Regression unchanged: **{regression.get('unchanged')}**",
        "",
    ]
    (out_root / "reports" / "P250_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")

    # Visual QA index — prioritize fails / partials
    fails = [r for r in beam_rows if r.get("crop_qa_overall") in ("FAIL", "PARTIAL")]
    fails.sort(key=lambda r: (0 if r.get("crop_qa_overall") == "FAIL" else 1, r.get("beam_id") or ""))
    idx = [
        "# P2.5.0 Visual QA Index",
        "",
        "Prioritized review list (FAIL / PARTIAL first).",
        "",
        "| Beam | QA | Reinf | Ann | Leader | Chain | Clipped | Eng crop | Overlay |",
        "|------|----|:-----:|:---:|:------:|:-----:|:-------:|----------|---------|",
    ]
    ordered = fails + [
        r for r in beam_rows if r.get("crop_qa_overall") == "PASS"
    ]
    for r in ordered:
        idx.append(
            f"| {r.get('beam_id')} | {r.get('crop_qa_overall')} | "
            f"{'Y' if r.get('reinforcement_present') else 'N'} | "
            f"{'Y' if r.get('annotation_present') else 'N'} | "
            f"{'Y' if r.get('leader_present') else 'N'} | "
            f"{'Y' if r.get('leader_chain_complete') else 'N'} | "
            f"{'Y' if r.get('evidence_clipped') else 'N'} | "
            f"`{r.get('engineering_crop')}` | `{r.get('evidence_overlay')}` |"
        )
    (out_root / "reports" / "VisualQAIndex.md").write_text("\n".join(idx), encoding="utf-8")

    readme = [
        "# Phase P2.5.0 — Beam Evidence Rendering & Crop QA",
        "",
        "Diagnostic-only. No Claude. No engineering changes.",
        "",
        "## Runner",
        "",
        "```",
        "python Run_PY/run_phase_p250_beam_evidence_crop_qa.py",
        "```",
        "",
        "## Outputs",
        "",
        "- `beams/<BEAM_ID>/engineering_crop.png`",
        "- `beams/<BEAM_ID>/evidence_overlay.png`",
        "- `beams/<BEAM_ID>/evidence.json`",
        "- `beams/<BEAM_ID>/crop_qa.json`",
        "- `reports/P250_SUMMARY.md`",
        "- `reports/VisualQAIndex.md`",
        "",
    ]
    (out_root / "README.md").write_text("\n".join(readme), encoding="utf-8")
