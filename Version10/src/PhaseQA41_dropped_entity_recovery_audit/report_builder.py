"""
Write QA.4.1 audit artefacts.
MODEL_VERSION: 10.5.0
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "10.5.0"
PHASE_ID = "QA.4.1"


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def write_all(
    out_root: Path,
    *,
    baseline_validation: Dict[str, Any],
    audits: List[Dict[str, Any]],
    envelope_audits: List[Dict[str, Any]],
    leader_audits: List[Dict[str, Any]],
    geometry_audits: List[Dict[str, Any]],
    evidence_rows: List[Dict[str, Any]],
    patterns: Dict[str, Any],
    representatives: Dict[str, Any],
    matrix: Dict[str, Any],
    recommendations: Dict[str, Any],
    regression: Dict[str, Any],
    category_counts: Dict[str, Any],
    potential_counts: Dict[str, Any],
    visual_paths: Dict[str, str],
    meta: Dict[str, Any],
) -> Dict[str, str]:
    out_root.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    now = datetime.now(timezone.utc).isoformat()

    p = out_root / "QA41BaselineValidation.json"
    _dump(p, baseline_validation)
    paths[p.name] = str(p)

    p = out_root / "DroppedEntityAudit.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": now,
            **meta,
            "entity_count": len(audits),
            "category_counts": category_counts,
            "potential_counts": potential_counts,
            "entities": audits,
        },
    )
    paths[p.name] = str(p)

    # xlsx
    xp = out_root / "DroppedEntityAudit.xlsx"
    _write_xlsx(xp, audits)
    paths[xp.name] = str(xp)

    p = out_root / "EnvelopeAudit.json"
    _dump(p, {"phase_id": PHASE_ID, "count": len(envelope_audits), "entities": envelope_audits})
    paths[p.name] = str(p)

    p = out_root / "LeaderChainAudit.json"
    _dump(p, {"phase_id": PHASE_ID, "count": len(leader_audits), "entities": leader_audits})
    paths[p.name] = str(p)

    p = out_root / "GeometryAudit.json"
    _dump(p, {"phase_id": PHASE_ID, "count": len(geometry_audits), "entities": geometry_audits})
    paths[p.name] = str(p)

    p = out_root / "RecoveryEvidence.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "note": "Diagnostic evidence only — NOT an ownership score",
            "count": len(evidence_rows),
            "rows": evidence_rows,
        },
    )
    paths[p.name] = str(p)

    p = out_root / "RecoveryPatternClusters.json"
    _dump(p, {"phase_id": PHASE_ID, "patterns": patterns.get("patterns") or []})
    paths[p.name] = str(p)

    p = out_root / "RecoveryPriorityMatrix.json"
    _dump(p, {"phase_id": PHASE_ID, **matrix})
    paths[p.name] = str(p)

    p = out_root / "RepresentativeCases.json"
    _dump(p, {"phase_id": PHASE_ID, **representatives})
    paths[p.name] = str(p)

    p = out_root / "RegressionReport.json"
    _dump(p, regression)
    paths[p.name] = str(p)

    p = out_root / "EngineeringRecommendations.md"
    p.write_text(_recs_md(recommendations, category_counts, potential_counts), encoding="utf-8")
    paths[p.name] = str(p)

    p = out_root / "README.md"
    p.write_text(_readme_md(meta, category_counts, visual_paths), encoding="utf-8")
    paths[p.name] = str(p)

    return paths


def write_execution_summary(
    out_root: Path,
    *,
    baseline_validation: Dict[str, Any],
    category_counts: Dict[str, Any],
    potential_counts: Dict[str, Any],
    matrix: Dict[str, Any],
    recommendations: Dict[str, Any],
    regression: Dict[str, Any],
    validation: Dict[str, Any],
    elapsed: float,
) -> Path:
    answers = recommendations.get("answers") or {}
    lines = [
        f"# Phase {PHASE_ID} Execution Summary",
        "",
        f"- MODEL_VERSION: `{MODEL_VERSION}`",
        f"- Elapsed: `{elapsed}s`",
        "",
        "QA.4.1 is a Fourth Set controlled audit-only phase.",
        "It audits the 104 dropped entities from the 11 Fourth Set priority",
        "beams. No dropped entity was recovered, no ownership decision was",
        "changed, and no production engineering logic was modified.",
        "",
        "Fifth and Sixth Set drawings were not included in the QA.4.1",
        "baseline and will be used only for later generalization validation.",
        "",
        "## Baseline",
        f"- Status: `{baseline_validation.get('status')}`",
        f"- Fourth Set entities in scope: `{baseline_validation.get('fourth_set_entities_in_scope')}`",
        f"- Fifth excluded: `{baseline_validation.get('fifth_set_entities_excluded')}`",
        f"- Sixth excluded: `{baseline_validation.get('sixth_set_entities_excluded')}`",
        "",
        "## Category counts",
        f"`{category_counts}`",
        "",
        "## Recovery potential",
        f"`{potential_counts}`",
        "",
        "## Key answers",
        f"1. Envelope problems: `{answers.get('1_envelope_problems')}`",
        f"2. Leader-chain problems: `{answers.get('2_leader_chain_problems')}`",
        f"3. Geometry problems: `{answers.get('3_geometry_problems')}`",
        f"4. Envelope distances: `{answers.get('4_envelope_distance_stats')}`",
        f"5. Envelope HIGH potential: `{answers.get('5_envelope_high_potential')}`",
        f"6. Leader HIGH potential: `{answers.get('6_leader_high_potential')}`",
        f"8. First recovery mechanism: `{answers.get('8_first_recovery_mechanism')}`",
        "",
        "## Evidence-driven P1",
        f"`{matrix.get('evidence_driven_p1')}`",
        "",
        "## Recommended next implementation sequence",
    ]
    for step in recommendations.get("next_implementation_sequence") or []:
        lines.append(f"- {step}")
    lines += [
        "",
        f"- Regression: `{regression.get('regression_status')}`",
        f"- QA validation: `{validation.get('overall_pass')}`",
        f"- STATUS: `{'PASS' if validation.get('overall_pass') else 'FAIL'}`",
        "",
    ]
    path = out_root / "ExecutionSummary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_xlsx(path: Path, audits: List[Dict[str, Any]]) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "DroppedAudit"
    headers = [
        "beam_id",
        "entity_id",
        "entity_type",
        "text",
        "primary_audit_category",
        "qa34_category",
        "original_rejection_reason",
        "rejected_rule",
        "recovery_potential",
        "spatial_relationship",
        "min_distance_to_production_envelope",
        "leader_failure_class",
        "geometry_class",
        "graph_node_found",
    ]
    ws.append(headers)
    for a in audits:
        env = a.get("envelope_audit") or {}
        ws.append(
            [
                a.get("beam_id"),
                a.get("entity_id"),
                a.get("entity_type"),
                a.get("text"),
                a.get("primary_audit_category"),
                a.get("qa34_category"),
                a.get("original_rejection_reason"),
                a.get("rejected_rule"),
                a.get("recovery_potential"),
                env.get("spatial_relationship"),
                env.get("min_distance_to_production_envelope"),
                (a.get("leader_audit") or {}).get("failure_class"),
                (a.get("geometry_audit") or {}).get("geometry_class"),
                a.get("graph_node_found"),
            ]
        )
    wb.save(path)


def _recs_md(recs, cats, pots) -> str:
    lines = [
        f"# {PHASE_ID} Engineering Recommendations",
        "",
        "Based ONLY on the Fourth Set 104-entity audit evidence.",
        "",
        f"Principle: **{recs.get('principle')}**",
        "",
        f"Categories: `{cats}`",
        f"Potentials: `{pots}`",
        "",
    ]
    for pr in recs.get("priorities") or []:
        lines.append(f"## Priority {pr.get('priority')}: {pr.get('title')}")
        lines.append("")
        lines.append(pr.get("recommendation") or "")
        lines.append("")
    lines.append("## Next implementation sequence")
    for s in recs.get("next_implementation_sequence") or []:
        lines.append(f"- {s}")
    lines.append("")
    return "\n".join(lines)


def _readme_md(meta, cats, visuals) -> str:
    return "\n".join(
        [
            f"# Phase {PHASE_ID} — Dropped Entity Recovery Audit",
            "",
            f"MODEL_VERSION: `{MODEL_VERSION}`",
            "",
            "Fourth Set controlled diagnostic audit of 104 dropped entities.",
            "No recovery. No ownership changes.",
            "",
            f"Drawing set: `{meta.get('drawing_set')}`",
            f"Categories: `{cats}`",
            "",
            "## Visuals",
            *[f"- {k}: `{v}`" for k, v in (visuals or {}).items() if k != "error"],
            "",
        ]
    )
