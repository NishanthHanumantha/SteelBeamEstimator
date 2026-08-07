"""
Write QA.3.3 explainability artefacts.
MODEL_VERSION: 10.0.3
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "10.0.3"
PHASE_ID = "QA.3.3"


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _try_xlsx(path: Path, rows: List[Dict[str, Any]]) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "CandidateDiscovery"
    if rows:
        headers = list(rows[0].keys())
        ws.append(headers)
        for r in rows:
            ws.append([r.get(h) for h in headers])
    else:
        ws.append(["beam_id"])
    wb.save(path)


def write_all(
    out_root: Path,
    records: List[Dict[str, Any]],
    aggregate: Dict[str, Any],
    recommendations: Dict[str, Any],
    competition_index: Dict[str, Any],
    visual_paths: Dict[str, Any],
    meta: Dict[str, Any],
) -> Dict[str, str]:
    out_root.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    now = datetime.now(timezone.utc).isoformat()

    # CandidateDiscovery
    cand = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "generated_at": now,
        "beams": [r.get("stage1_candidate_discovery") for r in records],
    }
    p = out_root / "CandidateDiscovery.json"
    _dump(p, cand)
    paths[p.name] = str(p)

    xrows = []
    for r in records:
        d = r.get("stage1_candidate_discovery") or {}
        xrows.append(
            {
                "beam_id": r.get("beam_id"),
                "nearby_count": d.get("nearby_count"),
                "candidate_count": d.get("candidate_count"),
                "search_method": d.get("search_method"),
                "side_of_mark": d.get("side_of_mark"),
                "status": d.get("status"),
                "envelope_w": (d.get("envelope_dimensions") or [None, None])[0],
                "envelope_h": (d.get("envelope_dimensions") or [None, None])[1],
            }
        )
    xp = out_root / "CandidateDiscovery.xlsx"
    _try_xlsx(xp, xrows)
    paths[xp.name] = str(xp)

    p = out_root / "OwnershipScores.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "beams": [r.get("stage2_ownership_scoring") for r in records],
        },
    )
    paths[p.name] = str(p)

    p = out_root / "ConflictResolution.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "global_index_summary": {
                k: competition_index.get(k)
                for k in (
                    "entity_count",
                    "multi_beam_entity_count",
                    "average_competing_beams",
                )
            },
            "beams": [r.get("stage3_competing_beams") for r in records],
            # Keep full multi-beam entities that touch priority set (truncated payloads via filter)
            "priority_multi_beam_entities": {
                eid: c
                for eid, c in (competition_index.get("by_entity") or {}).items()
                if c.get("in_priority_set") and len(c.get("competing_beams") or []) >= 2
            },
            "multi_beam_annotation_texts": competition_index.get("by_annotation_text")
            or {},
            "multi_beam_annotation_text_count": competition_index.get(
                "multi_beam_annotation_text_count"
            ),
        },
    )
    paths[p.name] = str(p)

    p = out_root / "EntityDecisionTrace.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "beams": [r.get("stage4_decision_traces") for r in records],
        },
    )
    paths[p.name] = str(p)

    p = out_root / "OwnershipCoverage.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "beams": [r.get("stage5_coverage") for r in records],
        },
    )
    paths[p.name] = str(p)

    p = out_root / "OwnershipFailureClassification.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "beams": [r.get("stage6_failure_classification") for r in records],
            "frequency": aggregate.get("failure_frequency_by_category"),
        },
    )
    paths[p.name] = str(p)

    p = out_root / "OwnershipStatistics.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": now,
            **meta,
            "aggregate": aggregate,
            "recommendations": recommendations,
        },
    )
    paths[p.name] = str(p)

    # Markdown
    p = out_root / "BeamOwnershipCards.md"
    p.write_text(_cards_md(records), encoding="utf-8")
    paths[p.name] = str(p)

    p = out_root / "OwnershipDecisionTrees.md"
    p.write_text(_trees_md(records, visual_paths), encoding="utf-8")
    paths[p.name] = str(p)

    p = out_root / "OwnershipHeatmaps.md"
    p.write_text(_heatmaps_md(records, aggregate, visual_paths), encoding="utf-8")
    paths[p.name] = str(p)

    p = out_root / "EngineeringRecommendations.md"
    p.write_text(_recs_md(recommendations, aggregate), encoding="utf-8")
    paths[p.name] = str(p)

    p = out_root / "README.md"
    p.write_text(_readme_md(meta, aggregate), encoding="utf-8")
    paths[p.name] = str(p)

    return paths


def write_execution_summary(
    out_root: Path,
    aggregate: Dict[str, Any],
    recommendations: Dict[str, Any],
    validation: Dict[str, Any],
    elapsed: float,
) -> Path:
    lines = [
        f"# Phase {PHASE_ID} Execution Summary",
        "",
        f"- MODEL_VERSION: `{MODEL_VERSION}`",
        f"- Elapsed: `{elapsed}s`",
        f"- Beams analysed: `{aggregate.get('beams_analysed')}`",
        f"- Candidate discovery rate: `{aggregate.get('candidate_discovery_rate')}`",
        f"- Ownership acceptance rate: `{aggregate.get('ownership_acceptance_rate')}`",
        f"- Candidate rejection rate: `{aggregate.get('candidate_rejection_rate')}`",
        f"- Conflict frequency: `{aggregate.get('conflict_frequency')}`",
        f"- Avg competing beams/entity: `{aggregate.get('average_competing_beams_per_entity')}`",
        f"- Avg ownership score: `{aggregate.get('average_ownership_score')}`",
        f"- Avg rejection score: `{aggregate.get('average_rejection_score')}`",
        f"- Avg score margin: `{aggregate.get('average_score_margin')}`",
        f"- Most common rejection reason: `{aggregate.get('most_common_rejection_reason')}`",
        f"- Most common filtering rule: `{aggregate.get('most_common_filtering_rule')}`",
        f"- Most common competing scenario: `{aggregate.get('most_common_competing_beam_scenario')}`",
        f"- Failure frequency: `{aggregate.get('failure_frequency_by_category')}`",
        f"- Validation overall_pass: `{validation.get('overall_pass')}`",
        "",
        "## Priorities",
    ]
    for pr in recommendations.get("priorities") or []:
        lines.append(f"### Priority {pr.get('priority')}: {pr.get('title')}")
        lines.append("")
        lines.append(pr.get("recommendation") or "")
        lines.append("")
        lines.append(f"- Impact: {pr.get('engineering_impact')}")
        lines.append(f"- Expected benchmark: {pr.get('expected_benchmark_improvement')}")
        lines.append("")
    path = out_root / "ExecutionSummary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _cards_md(records: List[Dict[str, Any]]) -> str:
    lines = [f"# {PHASE_ID} Beam Ownership Cards", "", f"MODEL_VERSION: {MODEL_VERSION}", ""]
    for r in records:
        d = r.get("stage1_candidate_discovery") or {}
        s = r.get("stage2_ownership_scoring") or {}
        c = r.get("stage5_coverage") or {}
        f = r.get("stage6_failure_classification") or {}
        lines += [
            f"## {r.get('beam_id')}",
            "",
            f"- Has ownership: `{r.get('has_ownership')}`",
            f"- Search method: {d.get('search_method')}",
            f"- Side of mark: `{d.get('side_of_mark')}` body_reason=`{d.get('body_reason')}`",
            f"- Nearby / Candidates: `{d.get('nearby_count')}` / `{d.get('candidate_count')}`",
            f"- T18 scored: `{s.get('t18_score_count')}` avg_score=`{s.get('average_t18_score')}`",
            f"- Coverage%: `{c.get('coverage_pct')}` Ownership%: `{c.get('ownership_pct')}` Conflict%: `{c.get('conflict_pct')}`",
            f"- Owned / Rejected / Elsewhere: `{c.get('entities_owned')}` / `{c.get('entities_rejected')}` / `{c.get('entities_owned_elsewhere')}`",
            f"- Primary failure cause: **{f.get('primary_cause')}** ({f.get('confidence')})",
            f"- Detail: {f.get('detail')}",
            f"- T18 stats: `{r.get('t18_stats')}`",
            "",
        ]
        # Top rejects
        rej = [
            t
            for t in ((r.get("stage4_decision_traces") or {}).get("traces") or [])
            if t.get("outcome") == "REJECTED"
        ][:5]
        if rej:
            lines.append("Rejected entities:")
            for t in rej:
                reason = None
                for step in t.get("decision_path") or []:
                    if str(step.get("step", "")).startswith("rule_reject"):
                        reason = step.get("ownership_reason") or step.get("step")
                lines.append(
                    f"  - `{t.get('entity_id')}` {t.get('text') or ''} -> {reason}"
                )
            lines.append("")
    return "\n".join(lines)


def _trees_md(records: List[Dict[str, Any]], visual_paths: Dict[str, Any]) -> str:
    lines = [f"# {PHASE_ID} Ownership Decision Trees", ""]
    for r in records:
        vp = visual_paths.get(r["beam_id"]) or {}
        if vp.get("decision_tree_summary_md"):
            lines.append(vp["decision_tree_summary_md"])
            lines.append("")
        else:
            lines.append(f"### {r['beam_id']}")
            lines.append("_No tree summary_")
            lines.append("")
    return "\n".join(lines)


def _heatmaps_md(
    records: List[Dict[str, Any]],
    aggregate: Dict[str, Any],
    visual_paths: Dict[str, Any],
) -> str:
    lines = [
        f"# {PHASE_ID} Ownership Heatmaps",
        "",
        "| Beam | Primary Cause | Owned | Rejected | Coverage% | Ownership% | Conflict% | Avg Score |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in records:
        f = r.get("stage6_failure_classification") or {}
        c = r.get("stage5_coverage") or {}
        s = r.get("stage2_ownership_scoring") or {}
        lines.append(
            f"| {r.get('beam_id')} | {f.get('primary_cause')} | {c.get('entities_owned')} | "
            f"{c.get('entities_rejected')} | {c.get('coverage_pct')} | {c.get('ownership_pct')} | "
            f"{c.get('conflict_pct')} | {s.get('average_t18_score')} |"
        )
    lines += [
        "",
        "## Global",
        f"- Failure frequency: `{aggregate.get('failure_frequency_by_category')}`",
        f"- Most common rejection: `{aggregate.get('most_common_rejection_reason')}`",
        "",
        "## Visual paths",
    ]
    for bid, vp in visual_paths.items():
        lines.append(f"- **{bid}**: heatmap=`{(vp or {}).get('ownership_score_heatmap')}`")
    lines.append("")
    return "\n".join(lines)


def _recs_md(recs: Dict[str, Any], agg: Dict[str, Any]) -> str:
    lines = [
        f"# {PHASE_ID} Engineering Recommendations",
        "",
        "Based ONLY on collected evidence. NO ownership code changes in this phase.",
        "",
        f"Summary: {recs.get('summary')}",
        "",
    ]
    for pr in recs.get("priorities") or []:
        lines.append(f"## Priority {pr.get('priority')}: {pr.get('title')}")
        lines.append("")
        lines.append(pr.get("recommendation") or "")
        lines.append("")
        lines.append(f"- Engineering impact: **{pr.get('engineering_impact')}**")
        lines.append(
            f"- Expected benchmark improvement: {pr.get('expected_benchmark_improvement')}"
        )
        lines.append(f"- Evidence: `{pr.get('evidence')}`")
        lines.append("")
    return "\n".join(lines)


def _readme_md(meta: Dict[str, Any], agg: Dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Phase {PHASE_ID} — Ownership Explainability & Decision Trace Engine",
            "",
            f"MODEL_VERSION: `{MODEL_VERSION}`",
            "",
            "Diagnostic-only instrumentation of Ownership decisions.",
            "Does **not** modify discovery, scoring, conflict resolution, or rendering.",
            "",
            "## Outputs",
            "- `CandidateDiscovery.json` / `.xlsx`",
            "- `OwnershipScores.json`",
            "- `ConflictResolution.json`",
            "- `EntityDecisionTrace.json`",
            "- `OwnershipCoverage.json`",
            "- `OwnershipFailureClassification.json`",
            "- `OwnershipStatistics.json`",
            "- Visual folders: `CandidateEnvelopeOverlays/`, `CompetingBeamOverlays/`, `DecisionFlowCharts/`",
            "",
            f"## Run",
            f"- Drawing set: `{meta.get('drawing_set')}`",
            f"- Run root: `{meta.get('run_root')}`",
            f"- Dominant failure: `{agg.get('failure_frequency_by_category')}`",
            "",
            "See `ExecutionSummary.md`.",
            "",
        ]
    )
