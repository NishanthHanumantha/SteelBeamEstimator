"""
Write P2.4 audit artefacts and markdown reports.
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def write_matrix_csv(path: Path, matrix: List[Dict[str, Any]]) -> None:
    cols = [
        "beam_id",
        "gt_bar_id",
        "gt_description",
        "dxf_entity_found",
        "dxf_entity_handle",
        "dxf_entity_type",
        "physical_bar_detected",
        "physical_bar_id",
        "owned_by_correct_beam",
        "owner_beam_id",
        "annotation_found",
        "annotation_id",
        "leader_found",
        "leader_id",
        "leader_chain_valid",
        "role_correct",
        "gt_role",
        "model_role",
        "diameter_correct",
        "gt_diameter",
        "model_diameter",
        "quantity_correct",
        "gt_quantity",
        "model_quantity",
        "engineering_object_found",
        "engineering_object_id",
        "vb1_consumed",
        "steel_contribution_correct",
        "first_failure_stage",
        "failure_reason",
        "confidence",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in matrix:
            w.writerow({k: r.get(k) for k in cols})


def write_beam_summary_xlsx(path: Path, beams: List[Dict[str, Any]]) -> None:
    try:
        from openpyxl import Workbook
    except Exception:
        # fallback CSV
        alt = path.with_suffix(".csv")
        with alt.open("w", newline="", encoding="utf-8") as f:
            if not beams:
                return
            cols = list(beams[0].keys())
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(beams)
        return
    wb = Workbook()
    ws = wb.active
    ws.title = "BeamBarFailureSummary"
    if not beams:
        wb.save(path)
        return
    cols = list(beams[0].keys())
    ws.append(cols)
    for b in beams:
        ws.append([b.get(c) for c in cols])
    wb.save(path)


def write_all(
    out_dir: Path,
    *,
    matrix: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    beams: List[Dict[str, Any]],
    diagnostics: Dict[str, Any],
    special: Dict[str, Any],
    gt_registry: List[Dict[str, Any]],
    model_registry: List[Dict[str, Any]],
    determinism: Dict[str, Any],
    regression: Dict[str, Any],
    visual_manifest: Dict[str, Any],
    meta: Dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    write_matrix_csv(out_dir / "GT_BAR_FAILURE_MATRIX.csv", matrix)
    _dump(out_dir / "GT_BAR_FAILURE_MATRIX.json", {"rows": matrix, "count": len(matrix)})
    _dump(out_dir / "BeamBarFailureSummary.json", {"beams": beams})
    write_beam_summary_xlsx(out_dir / "BeamBarFailureSummary.xlsx", beams)

    _dump(
        out_dir / "FirstFailureDistribution.json",
        {
            "counts": metrics.get("first_failure_counts"),
            "pct_of_failures": metrics.get("first_failure_distribution_pct"),
        },
    )
    _dump(
        out_dir / "FailureFrequency.json",
        {
            "excel_status": _count(matrix, "excel_status"),
            "match_status": _count(matrix, "match_status"),
            "first_failure_stage": metrics.get("first_failure_counts"),
            "failure_reason": _count(matrix, "failure_reason"),
        },
    )

    _dump(out_dir / "DetectionDiagnostics.json", diagnostics["detection"])
    _dump(out_dir / "OwnershipDiagnostics.json", diagnostics["ownership"])
    _dump(out_dir / "AnnotationDiagnostics.json", diagnostics["annotation"])
    _dump(out_dir / "LeaderDiagnostics.json", diagnostics["leader"])
    _dump(out_dir / "RoleDiagnostics.json", diagnostics["role"])
    _dump(out_dir / "DiameterDiagnostics.json", diagnostics["diameter"])
    _dump(out_dir / "QuantityDiagnostics.json", diagnostics["quantity"])
    _dump(
        out_dir / "EngineeringPropagationDiagnostics.json",
        diagnostics["engineering"],
    )
    _dump(out_dir / "ExtraBarDiagnostics.json", diagnostics["extra_bars"])
    _dump(out_dir / "GT_Bar_Registry.json", {"bars": gt_registry, "count": len(gt_registry)})
    _dump(
        out_dir / "Model_Bar_Registry.json",
        {"bars": model_registry, "count": len(model_registry)},
    )
    _dump(out_dir / "SpecialAnalyses.json", special)
    _dump(out_dir / "Metrics.json", metrics)
    _dump(out_dir / "P24_determinism.json", determinism)
    _dump(out_dir / "RegressionReport.json", regression)
    _dump(out_dir / "VisualManifest.json", visual_manifest)
    _dump(out_dir / "P24_run_meta.json", meta)

    _write_markdown_reports(out_dir, metrics, beams, special, determinism, regression, meta)


def _count(rows: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    from collections import Counter

    return dict(Counter(r.get(key) for r in rows))


def _write_markdown_reports(
    out_dir: Path,
    metrics: Dict[str, Any],
    beams: List[Dict[str, Any]],
    special: Dict[str, Any],
    determinism: Dict[str, Any],
    regression: Dict[str, Any],
    meta: Dict[str, Any],
) -> None:
    q = metrics.get("questions") or {}
    top3 = metrics.get("top3_root_causes") or []
    top = special.get("top_reinforcement") or {}
    problem = special.get("problem_beams_b10_b12_b13") or {}
    shared = special.get("shared_beams_b8_b9_b10") or {}

    root = [
        "# Fourth Set Root Cause Summary (P2.4)",
        "",
        f"- MODEL_VERSION: `{meta.get('model_version')}`",
        f"- SCOPE: `{meta.get('scope')}`",
        f"- MODE: `{meta.get('mode')}`",
        f"- ENGINEERING_CHANGES: `{meta.get('engineering_changes')}`",
        "",
        "## Headline metrics",
        "",
        f"- GT bars: **{metrics.get('gt_total_bars')}**",
        f"- Matched: **{metrics.get('matched_bars')}**",
        f"- Partially matched: **{metrics.get('partially_matched_bars')}**",
        f"- Unmatched: **{metrics.get('unmatched_gt_bars')}**",
        f"- Extra model bars: **{metrics.get('extra_model_bars')}**",
        "",
        "## Stage rates (over all GT bars)",
        "",
        f"- Physical detection: {metrics.get('physical_bar_detection_pct')}%",
        f"- Ownership: {metrics.get('correct_beam_ownership_pct')}%",
        f"- Annotation association (CORRECT): {metrics.get('annotation_association_pct')}%",
        f"- Leader-chain valid: {metrics.get('leader_chain_success_pct')}%",
        f"- Role accuracy: {metrics.get('role_accuracy_pct')}%",
        f"- Diameter accuracy: {metrics.get('diameter_accuracy_pct')}%",
        f"- Quantity accuracy: {metrics.get('quantity_accuracy_pct')}%",
        f"- Engineering propagation: {metrics.get('engineering_object_propagation_pct')}%",
        f"- VB1 consumption: {metrics.get('vb1_consumption_pct')}%",
        "",
        "## First-failure distribution (% of failing GT bars)",
        "",
    ]
    for k, v in (metrics.get("first_failure_distribution_pct") or {}).items():
        root.append(f"- `{k}`: {v}% ({(metrics.get('first_failure_counts') or {}).get(k, 0)})")
    root += [
        "",
        "## Answers to mandatory questions",
        "",
        f"1. Missing at PhysicalBar detection: **{q.get('Q1_missing_at_physical_detection')}**",
        f"2. Wrong-beam ownership first-fail: **{q.get('Q2_wrong_beam_ownership')}**",
        f"3. Annotation association first-fail: **{q.get('Q3_annotation_association_fail')}**",
        f"4. Role/diameter/quantity first-fail: **{q.get('Q4_role_diameter_quantity_fail')}**",
        f"5. Engineering/VB1 first-fail: **{q.get('Q5_engineering_or_vb1_fail')}**",
        f"6. Largest first-fail category: **{q.get('Q6_largest_first_fail')}**",
        f"7. Second largest: **{q.get('Q7_second_largest_first_fail')}**",
        f"8. B10/B12/B13: see SpecialAnalyses — "
        f"{problem.get('B10', {}).get('conclusion')}",
        f"9. Top reinforcement dominant failure: **{top.get('dominant_failure')}** — {top.get('conclusion')}",
        f"10. Shared B8/B9/B10: {shared.get('conclusion')}",
        "",
        "## Recommended next engineering phase",
        "",
        f"**{metrics.get('recommended_next_phase')}**",
        "",
        "Chosen strictly from the measured first-failure distribution.",
        "",
    ]
    (out_dir / "FourthSetRootCauseSummary.md").write_text(
        "\n".join(root), encoding="utf-8"
    )

    fail_lines = [
        "# Fourth Set Failure Analysis (P2.4)",
        "",
        "## Top 3 root causes",
        "",
    ]
    for t in top3:
        fail_lines.append(
            f"- `{t.get('stage')}`: count={t.get('count')} ({t.get('pct_of_failures')}% of failures)"
        )
    fail_lines += ["", "## Beam summary (priority + meaningful failures)", ""]
    fail_lines.append(
        "| Beam | GT | Det | Match | Miss | Extra | Det% | Match% | FirstFail | Reason |"
    )
    fail_lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for b in beams:
        if not b.get("in_required_list") and b.get("missing", 0) == 0 and b.get("gt_bars", 0) > 0:
            # still show required; for others show if missing
            if b.get("first_failure") == "NO_FAILURE":
                continue
        fail_lines.append(
            f"| {b['beam_id']} | {b['gt_bars']} | {b['detected']} | {b['matched']} | "
            f"{b['missing']} | {b['extra']} | {b['detection_pct']} | {b['matching_pct']} | "
            f"{b['first_failure']} | {b['main_failure_reason']} |"
        )
    fail_lines += [
        "",
        "## Top reinforcement",
        "",
        f"- GT top bars: {top.get('gt_top_bars')}",
        f"- Matched: {top.get('matched')}",
        f"- Unmatched: {top.get('unmatched')}",
        f"- Dominant failure: `{top.get('dominant_failure')}`",
        f"- {top.get('conclusion')}",
        "",
        "## Problem beams B10/B12/B13",
        "",
    ]
    for bid, rec in problem.items():
        fail_lines.append(
            f"- **{bid}**: present={rec.get('present_in_fourth_set_gt')} — {rec.get('conclusion')}"
        )
    fail_lines += ["", "## Shared beams B8/B9/B10", "", shared.get("conclusion") or "", ""]
    (out_dir / "FourthSetFailureAnalysis.md").write_text(
        "\n".join(fail_lines), encoding="utf-8"
    )

    rec = [
        "# Engineering Recommendations (P2.4)",
        "",
        "Diagnostic only — no recovery implemented in this phase.",
        "",
        f"## Measured dominant first-fail: `{q.get('Q6_largest_first_fail')}`",
        "",
        f"## Recommended next phase: **{metrics.get('recommended_next_phase')}**",
        "",
        "### Decision framework applied",
        "",
        "Recommendation is taken from `RECOMMENDATION_MAP` using the largest",
        "first-failure category among failing GT bars (NO_FAILURE excluded).",
        "",
        "### Supporting evidence",
        "",
    ]
    for t in top3:
        rec.append(f"- {t.get('stage')}: {t.get('count')} ({t.get('pct_of_failures')}%)")
    rec += [
        "",
        "### Explicit non-recommendations",
        "",
        "- Do not choose ownership solely because prior phases studied it.",
        "- Do not implement Ownership→Engineering Bridge unless ENGINEERING_OBJECT/VB1 dominates.",
        "",
    ]
    (out_dir / "EngineeringRecommendations.md").write_text(
        "\n".join(rec), encoding="utf-8"
    )

    arch = [
        "# P2.4 Architecture Summary",
        "",
        "## Purpose",
        "Attribute every Fourth Set GT reinforcement bar to the earliest pipeline stage",
        "where expected information is lost or becomes incorrect.",
        "",
        "## Inputs (read-only)",
        "- Estimator Excel (GT only, post-processing comparison)",
        "- Model Estimation_Output.xlsx (VB1)",
        "- R3.1 PhysicalBars, T16 ownership, T17 AnnotationGraph",
        "- T18 BeamOwnership, T18.3.1 shared scopes",
        "- R1.3 beam_reinforcement_models_production",
        "",
        "## Pipeline stages audited",
        "GT → DXF → PhysicalBar → Ownership → Annotation → Leader → Role → Diameter → Quantity → Engineering → VB1 → Steel",
        "",
        "## Matching",
        "Reuses QA.2A BarMatcher deterministically (role/diameter/quantity).",
        "GT Excel never influences detection/ownership/association.",
        "",
        "## Constraints",
        "- Fourth Set only",
        "- No production mutations",
        "- Determinism: audit executed twice",
        "",
    ]
    (out_dir / "P24_ARCHITECTURE_SUMMARY.md").write_text(
        "\n".join(arch), encoding="utf-8"
    )

    exe = [
        "# P2.4 Execution Summary",
        "",
        f"- success: `{meta.get('success')}`",
        f"- model_version: `{meta.get('model_version')}`",
        f"- scope: `{meta.get('scope')}`",
        f"- mode: `{meta.get('mode')}`",
        f"- engineering_changes: `{meta.get('engineering_changes')}`",
        f"- elapsed_s: `{meta.get('elapsed_s')}`",
        f"- determinism: `{determinism.get('determinism_status')}`",
        f"- regression_unchanged: `{regression.get('unchanged')}`",
        f"- recommended_next_phase: `{metrics.get('recommended_next_phase')}`",
        "",
        "## Counts",
        "",
        f"- GT: {metrics.get('gt_total_bars')}",
        f"- matched: {metrics.get('matched_bars')}",
        f"- unmatched: {metrics.get('unmatched_gt_bars')}",
        f"- extra: {metrics.get('extra_model_bars')}",
        "",
    ]
    (out_dir / "P24_EXECUTION_SUMMARY.md").write_text("\n".join(exe), encoding="utf-8")

    readme = [
        "# Phase P2.4 — Fourth Set Bar Failure Attribution Audit",
        "",
        "Diagnostic-only audit. No engineering recovery.",
        "",
        "## Runner",
        "",
        "```",
        "python Run_PY/run_phase_p24_fourth_set_bar_failure_audit.py",
        "```",
        "",
        "## Key outputs",
        "",
        "- `GT_BAR_FAILURE_MATRIX.csv` / `.json`",
        "- `BeamBarFailureSummary.json` / `.xlsx`",
        "- `FirstFailureDistribution.json`",
        "- `FourthSetRootCauseSummary.md`",
        "- `EngineeringRecommendations.md`",
        "",
    ]
    (out_dir / "README.md").write_text("\n".join(readme), encoding="utf-8")
