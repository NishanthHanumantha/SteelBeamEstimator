"""Markdown / CSV reports for P2.5.0.1."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _csv(path: Path, rows: List[Dict[str, Any]], cols: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in cols})


def write_reports(
    out_root: Path,
    *,
    meta: Dict[str, Any],
    executive: Dict[str, Any],
    root_causes: Dict[str, Any],
    spatial_rows: List[Dict[str, Any]],
    known_good: Dict[str, Any],
    crop_sanity_rows: List[Dict[str, Any]],
    diagnostic_rows: List[Dict[str, Any]],
    traces: Dict[str, Any],
    expansions: Dict[str, Any],
    determinism: Dict[str, Any],
    regression: Dict[str, Any],
    fix_summary: Dict[str, Any],
) -> None:
    out_root = Path(out_root)
    for d in ("reports", "traces", "metrics", "diagnostics", "visuals"):
        (out_root / d).mkdir(parents=True, exist_ok=True)

    _dump(out_root / "diagnostics" / "meta.json", meta)
    _dump(out_root / "diagnostics" / "P2501_determinism.json", determinism)
    _dump(out_root / "diagnostics" / "RegressionReport.json", regression)
    _dump(out_root / "diagnostics" / "fixSummary.json", fix_summary)
    _dump(out_root / "diagnostics" / "RootCauses.json", root_causes)

    for bid, tr in traces.items():
        _dump(out_root / "traces" / f"{bid}_trace.json", tr)
    for bid, ex in expansions.items():
        _dump(out_root / "traces" / f"{bid}_expansion.json", ex)

    # Required named outputs
    _dump(out_root / "B97A_trace.json", traces.get("B97A") or {})
    _dump(out_root / "B98A_trace.json", traces.get("B98A") or {})

    spat_cols = [
        "beam_id",
        "cohort",
        "crop_height_mm",
        "crop_width_mm",
        "beam_height_mm",
        "beam_width_mm",
        "crop_height_to_beam_height_ratio",
        "crop_width_to_beam_width_ratio",
        "crop_area_to_beam_area_ratio",
        "max_y_gap_mm",
        "max_spatial_distance_mm",
        "dominant_expander_id",
        "dominant_expander_kind",
        "dominant_y_gap_mm",
    ]
    _csv(out_root / "SpatialMetrics.csv", spatial_rows, spat_cols)
    _csv(out_root / "metrics" / "SpatialMetrics.csv", spatial_rows, spat_cols)

    kg_rows = known_good.get("rows") or []
    _csv(
        out_root / "KnownGoodComparison.csv",
        kg_rows,
        list(spat_cols) + ["height_ratio_vs_known_good_mean", "reinforcement_count"],
    )

    diag_cols = [
        "beam_id",
        "root_cause",
        "confidence",
        "vision_crop_status",
        "crop_height_mm",
        "dominant_expander_id",
        "t18_rejected_bars_included_before",
        "fix_applied",
    ]
    _csv(out_root / "DiagnosticMatrix.csv", diagnostic_rows, diag_cols)

    # Crop sanity MD
    cs_lines = [
        "# Crop Sanity Report (Diagnostic Only)",
        "",
        "Statuses are measurements only — not Claude hard gates.",
        "",
        "| Beam | Status | Height ratio | Area ratio | Max Y gap (mm) | Dominant expander |",
        "|------|--------|-------------:|-----------:|---------------:|-------------------|",
    ]
    for r in crop_sanity_rows:
        dom = r.get("dominant_expander") or {}
        cs_lines.append(
            f"| {r.get('beam_id')} | {r.get('vision_crop_status')} | "
            f"{r.get('crop_height_to_beam_height_ratio')} | "
            f"{r.get('crop_area_to_beam_area_ratio')} | {r.get('max_y_gap_mm')} | "
            f"{dom.get('object_id')} |"
        )
    (out_root / "CropSanityReport.md").write_text("\n".join(cs_lines), encoding="utf-8")
    (out_root / "reports" / "CropSanityReport.md").write_text("\n".join(cs_lines), encoding="utf-8")

    # Root cause MD
    rc_lines = ["# Root Cause Report — P2.5.0.1", ""]
    for bid, rc in root_causes.items():
        rc_lines += [
            f"## {bid}",
            "",
            f"- **Root cause:** `{rc.get('label')}`",
            f"- **Confidence:** {rc.get('confidence')}",
            f"- **Basis:** `{json.dumps(rc.get('basis'), default=str)[:1200]}`",
            "",
        ]
    (out_root / "RootCauseReport.md").write_text("\n".join(rc_lines), encoding="utf-8")
    (out_root / "reports" / "RootCauseReport.md").write_text("\n".join(rc_lines), encoding="utf-8")

    # Regression MD
    reg_md = [
        "# Regression Report — P2.5.0.1",
        "",
        f"- Unchanged: **{regression.get('unchanged')}**",
        f"- Changed keys: `{regression.get('changed_keys')}`",
        f"- Determinism: **{determinism.get('determinism_status')}**",
        f"- Engineering changes: **NONE** (ownership/R3.1/P2.4 untouched)",
        f"- P2.5.0 fix: `{fix_summary.get('description')}`",
        "",
    ]
    (out_root / "RegressionReport.md").write_text("\n".join(reg_md), encoding="utf-8")

    # Executive summary — answers the 12 required questions
    q = executive.get("answers") or {}
    ex_lines = [
        "# P2.5.0.1 Executive Summary — Evidence Spatial Sanity",
        "",
        f"- MODEL_VERSION: `{meta.get('model_version')}`",
        f"- MODE: `{meta.get('mode')}`",
        f"- ENGINEERING_CHANGES: `{meta.get('engineering_changes')}`",
        f"- Determinism: **{determinism.get('determinism_status')}**",
        f"- Regression unchanged: **{regression.get('unchanged')}**",
        f"- Fix applied: **{fix_summary.get('applied')}**",
        "",
        "## Required answers",
        "",
        f"1. Why is B97A's crop ~47 m tall?  \n   {q.get('q1')}",
        "",
        f"2. Why is B98A's crop ~76 m tall?  \n   {q.get('q2')}",
        "",
        f"3. Which exact evidence object caused each expansion?  \n   {q.get('q3')}",
        "",
        f"4. Are BAR::2B7B3233 / BAR::5B1BFCC2 genuinely spatially associated with B97A?  \n   {q.get('q4')}",
        "",
        f"5. Are BAR::E6591903 / BAR::4D469A4E genuinely spatially associated with B98A?  \n   {q.get('q5')}",
        "",
        f"6. Coordinate-space / unit / transform problem?  \n   {q.get('q6')}",
        "",
        f"7. Ownership problem?  \n   {q.get('q7')}",
        "",
        f"8. Evidence-expansion problem?  \n   {q.get('q8')}",
        "",
        f"9. Upstream of P2.5.0 or inside P2.5.0?  \n   {q.get('q9')}",
        "",
        f"10. Does P2.5.0 need a code correction?  \n   {q.get('q10')}",
        "",
        f"11. Are current crops suitable for Claude Vision?  \n   {q.get('q11')}",
        "",
        f"12. Exact recommendation before P2.5.1?  \n   {q.get('q12')}",
        "",
        "## After-fix crop metrics (B97A / B98A)",
        "",
        f"{json.dumps(executive.get('after_fix_metrics'), indent=2, default=str)}",
        "",
    ]
    (out_root / "ExecutiveSummary.md").write_text("\n".join(ex_lines), encoding="utf-8")
    (out_root / "reports" / "ExecutiveSummary.md").write_text("\n".join(ex_lines), encoding="utf-8")
