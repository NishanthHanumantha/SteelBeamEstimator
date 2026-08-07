"""
Write QA.3.4 artefacts.
MODEL_VERSION: 10.0.4
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "10.0.4"
PHASE_ID = "QA.3.4"


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def write_all(
    out_root: Path,
    *,
    registry: Dict[str, Any],
    all_classified: List[Dict[str, Any]],
    beam_summaries: List[Dict[str, Any]],
    global_stats: Dict[str, Any],
    neighbour_matrix: Dict[str, Any],
    regression: Dict[str, Any],
    recommendations: Dict[str, Any],
    visual_paths: Dict[str, str],
    meta: Dict[str, Any],
) -> Dict[str, str]:
    out_root.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    now = datetime.now(timezone.utc).isoformat()

    # Registry — priority-focused view + full counts
    by_id = registry.get("by_identity") or {}
    priority_reg = {
        k: v for k, v in by_id.items() if v.get("TouchesPriority")
    }
    p = out_root / "OwnershipCompetitionRegistry.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": now,
            **meta,
            "entity_count": registry.get("entity_count"),
            "priority_entity_count": registry.get("priority_entity_count"),
            "by_identity": priority_reg,
        },
    )
    paths[p.name] = str(p)

    matrix_all = []
    migrations_all = []
    dropped_all = []
    validations_all = []
    for c in all_classified:
        matrix_all.extend(c.get("competition_matrix") or [])
        migrations_all.extend(c.get("migrations") or [])
        dropped_all.extend(c.get("dropped") or [])
        validations_all.extend(c.get("validations") or [])

    p = out_root / "CompetitionMatrix.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "count": len(matrix_all),
            "entries": matrix_all,
            "neighbour_beam_matrix": neighbour_matrix.get("matrix"),
        },
    )
    paths[p.name] = str(p)

    p = out_root / "OwnershipMigration.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "count": len(migrations_all),
            "migrations": migrations_all,
        },
    )
    paths[p.name] = str(p)

    p = out_root / "DroppedEntities.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "count": len(dropped_all),
            "note": "Rejected AND owned nowhere — engineering failures",
            "entities": dropped_all,
        },
    )
    paths[p.name] = str(p)

    p = out_root / "BeamCompetitionSummary.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "beams": beam_summaries,
        },
    )
    paths[p.name] = str(p)

    p = out_root / "GlobalCompetitionStatistics.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": now,
            "statistics": global_stats,
            "recommendations": recommendations,
        },
    )
    paths[p.name] = str(p)

    # CompetitionValidation — decision validation rows
    fail_n = sum(1 for v in validations_all if v.get("validation") != "PASS")
    p = out_root / "CompetitionValidation.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "overall_pass": fail_n == 0,
            "validation_row_count": len(validations_all),
            "fail_count": fail_n,
            "rows": validations_all,
        },
    )
    paths[p.name] = str(p)

    p = out_root / "RegressionReport.json"
    _dump(p, {"phase_id": PHASE_ID, **regression})
    paths[p.name] = str(p)

    # Markdown summaries
    p = out_root / "ArchitectureSummary.md"
    p.write_text(_architecture_md(meta, global_stats, recommendations), encoding="utf-8")
    paths[p.name] = str(p)

    p = out_root / "ValidationSummary.md"
    p.write_text(
        _validation_md(global_stats, regression, validations_all, recommendations),
        encoding="utf-8",
    )
    paths[p.name] = str(p)

    p = out_root / "DroppedEntities.md"
    p.write_text(_dropped_md(dropped_all), encoding="utf-8")
    paths[p.name] = str(p)

    p = out_root / "EngineeringRecommendations.md"
    p.write_text(_recs_md(recommendations, global_stats), encoding="utf-8")
    paths[p.name] = str(p)

    p = out_root / "README.md"
    p.write_text(_readme_md(meta, global_stats, visual_paths), encoding="utf-8")
    paths[p.name] = str(p)

    return paths


def write_execution_summary(
    out_root: Path,
    global_stats: Dict[str, Any],
    recommendations: Dict[str, Any],
    regression: Dict[str, Any],
    validation: Dict[str, Any],
    elapsed: float,
) -> Path:
    lines = [
        f"# Phase {PHASE_ID} Execution Summary",
        "",
        f"- MODEL_VERSION: `{MODEL_VERSION}`",
        f"- Elapsed: `{elapsed}s`",
        f"- Total rejected: `{global_stats.get('total_rejected')}`",
        f"- Owned elsewhere: `{global_stats.get('owned_elsewhere')}`",
        f"- Dropped: `{global_stats.get('dropped')}`",
        f"- Leader failures: `{global_stats.get('leader_failures')}`",
        f"- Geometry failures: `{global_stats.get('geometry_failures')}`",
        f"- Envelope failures: `{global_stats.get('envelope_failures')}`",
        f"- Conflict failures: `{global_stats.get('conflict_failures')}`",
        f"- Unknown: `{global_stats.get('unknown')}`",
        f"- Avg ownership margin: `{global_stats.get('average_ownership_margin')}`",
        f"- Median margin: `{global_stats.get('median_ownership_margin')}`",
        f"- Dropped fraction: `{global_stats.get('dropped_fraction_of_rejects')}`",
        f"- Regression overall_pass: `{regression.get('overall_pass')}`",
        f"- Ownership decisions changed: `{regression.get('ownership_decisions_changed')}`",
        f"- QA validation overall_pass: `{validation.get('overall_pass')}`",
        f"- Dominant QA.4.0 target: `{recommendations.get('dominant_qa40_target')}`",
        "",
        "## Priorities",
    ]
    for pr in recommendations.get("priorities") or []:
        lines.append(f"### Priority {pr.get('priority')}: {pr.get('title')}")
        lines.append("")
        lines.append(pr.get("recommendation") or "")
        lines.append("")
    path = out_root / "ExecutionSummary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _architecture_md(meta, stats, recs) -> str:
    return "\n".join(
        [
            f"# {PHASE_ID} Engineering Architecture Summary",
            "",
            f"MODEL_VERSION: `{MODEL_VERSION}`",
            "",
            "## Principle",
            "Read-only competition validation over QA.3.3 + T18 artefacts.",
            "No ownership scores, registries, or engineering rules are modified.",
            "",
            "## Pipeline",
            "```",
            "QA.3.3 traces/scores + T18 BeamOwnership",
            "        ↓",
            "Identity keys (id / leader handle / annotation text)",
            "        ↓",
            "OwnershipCompetitionRegistry",
            "        ↓",
            "Per-reject classification:",
            "  OWNED_ELSEWHERE | LEADER_FAILURE | GEOMETRY_FAILURE |",
            "  SEARCH_ENVELOPE_FAILURE | CONFLICT_FAILURE | UNKNOWN",
            "        ↓",
            "FinalState: OwnedElsewhere OR Dropped",
            "        ↓",
            "Regression gate vs QA.3.3 / T18 fingerprints",
            "```",
            "",
            f"## Run context",
            f"- Drawing set: `{meta.get('drawing_set')}`",
            f"- Run root: `{meta.get('run_root')}`",
            f"- QA.3.3 root: `{meta.get('qa33_root')}`",
            "",
            f"## Headline",
            f"- Rejected: `{stats.get('total_rejected')}`",
            f"- Owned elsewhere: `{stats.get('owned_elsewhere')}`",
            f"- Dropped: `{stats.get('dropped')}`",
            f"- Dominant QA.4.0 target: `{recs.get('dominant_qa40_target')}`",
            "",
        ]
    )


def _validation_md(stats, regression, validations, recs) -> str:
    fail = [v for v in validations if v.get("validation") != "PASS"]
    lines = [
        f"# {PHASE_ID} Validation Summary",
        "",
        f"- Decision validation rows: `{len(validations)}`",
        f"- Decision validation fails: `{len(fail)}`",
        f"- Regression pass: `{regression.get('overall_pass')}`",
        f"- Every reject OwnedElsewhere or Dropped: "
        f"`{(stats.get('owned_elsewhere') or 0) + (stats.get('dropped') or 0) == (stats.get('total_rejected') or -1)}`",
        "",
        "## Statistics",
        f"```",
        json.dumps(stats, indent=2),
        f"```",
        "",
        f"## Dominant target: `{recs.get('dominant_qa40_target')}`",
        "",
    ]
    return "\n".join(lines)


def _dropped_md(dropped: List[Dict[str, Any]]) -> str:
    lines = [
        f"# {PHASE_ID} Disappearing Entities",
        "",
        f"Count: `{len(dropped)}`",
        "",
        "| Beam | Type | Entity / Text | Reason | Category |",
        "|---|---|---|---|---|",
    ]
    for d in dropped[:200]:
        lines.append(
            f"| {d.get('beam_id')} | {d.get('entity_type')} | "
            f"{str(d.get('text') or d.get('entity_id'))[:40]} | "
            f"{str(d.get('reason'))[:40]} | {d.get('category')} |"
        )
    lines.append("")
    return "\n".join(lines)


def _recs_md(recs, stats) -> str:
    lines = [
        f"# {PHASE_ID} Engineering Recommendations",
        "",
        "Based ONLY on competition validation evidence.",
        "",
        f"Summary: {recs.get('summary')}",
        "",
    ]
    for pr in recs.get("priorities") or []:
        lines.append(f"## Priority {pr.get('priority')}: {pr.get('title')}")
        lines.append("")
        lines.append(pr.get("recommendation") or "")
        lines.append("")
        lines.append(f"- QA.4.0 target: `{pr.get('qa40_target')}`")
        lines.append(f"- Impact: {pr.get('engineering_impact')}")
        lines.append(f"- Expected: {pr.get('expected_benchmark_improvement')}")
        lines.append("")
    return "\n".join(lines)


def _readme_md(meta, stats, visuals) -> str:
    return "\n".join(
        [
            f"# Phase {PHASE_ID} — Ownership Competition Validation",
            "",
            f"MODEL_VERSION: `{MODEL_VERSION}`",
            "",
            "Answers: when an entity is rejected, did another beam win it, or did it disappear?",
            "",
            "## Key outputs",
            "- `OwnershipCompetitionRegistry.json`",
            "- `DroppedEntities.json` (most important)",
            "- `OwnershipMigration.json`",
            "- `CompetitionMatrix.json`",
            "- `RegressionReport.json`",
            "- `Visualisations/`",
            "",
            f"## Stats",
            f"- Rejected: {stats.get('total_rejected')}",
            f"- Owned elsewhere: {stats.get('owned_elsewhere')}",
            f"- Dropped: {stats.get('dropped')}",
            "",
            f"## Visuals",
            *[f"- {k}: `{v}`" for k, v in (visuals or {}).items() if k != "error"],
            "",
        ]
    )
