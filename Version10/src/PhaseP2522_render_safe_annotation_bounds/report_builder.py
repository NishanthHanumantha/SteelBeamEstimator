"""Status / summary reports for P2.5.2.2."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import (
    CLAUDE,
    ENGINEERING_CHANGES,
    MAX_RENDER_SAFETY_ITERATIONS,
    MIN_RENDER_SAFE_MARGIN_PX,
    MODEL_VERSION,
    PHASE_ID,
    PHASE_NAME,
)

MODEL_VERSION_LOCAL = MODEL_VERSION


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def write_reports(*, out_root: Path, summary: Dict[str, Any], refined: List[Dict[str, Any]]) -> Dict[str, str]:
    out_root = Path(out_root)
    metrics = summary.get("metrics") or {}
    lines = [
        f"# P2.5.2.2 STATUS",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"PHASE_ID: {PHASE_ID}",
        f"PHASE_NAME: {PHASE_NAME}",
        f"SCOPE: {summary.get('scope')}",
        f"PASS / FAIL: {summary.get('pass_fail')}",
        f"DECISION: {summary.get('decision')}",
        "",
        "## Input",
        f"- source: P2.5.2.1 refined active Vision candidates",
        f"- active candidates: {metrics.get('TOTAL_ACTIVE_CANDIDATES')}",
        f"- pixel safety threshold: {MIN_RENDER_SAFE_MARGIN_PX} px",
        f"- max iterations: {MAX_RENDER_SAFETY_ITERATIONS}",
        "",
        "## QA metrics",
    ]
    for k in [
        "TOTAL_ACTIVE_CANDIDATES",
        "GEOMETRIC_CONTAINMENT_PASS",
        "RENDER_SAFE_PASS",
        "ANNOTATION_CLIPPING_COUNT",
        "ANNOTATION_EDGE_RISK_COUNT",
        "LEADER_EDGE_RISK_COUNT",
        "TOP_ANNOTATION_EDGE_RISK_COUNT",
        "BOTTOM_ANNOTATION_EDGE_RISK_COUNT",
        "RENDER_SAFETY_REFINEMENT_COUNT",
        "MAX_ITERATION_HITS",
        "READABILITY_PASS",
        "READABILITY_PARTIAL",
        "READABILITY_REVIEW",
        "READABILITY_FAIL",
        "EXTREME_CROP_COUNT",
        "MISSING_TARGET_BEAM_COUNT",
        "MISSING_ANNOTATION_COUNT",
        "REJECTED_EVIDENCE_INCLUDED_COUNT",
        "DETERMINISM_PASS",
        "CLAUDE_CALLS",
        "ENGINEERING_CHANGES",
        "MAX_SIDE_EXPANSION_MM",
    ]:
        lines.append(f"- {k}: {metrics.get(k)}")

    lines += [
        "",
        "## Golden / invariants",
        f"- candidate set frozen (14): {summary.get('invariants_ok')}",
        f"- golden: {json.dumps(summary.get('golden'), default=str)}",
        "",
        "## Determinism",
        f"- status: {(summary.get('determinism') or {}).get('determinism_status')}",
        f"- fingerprint: `{(summary.get('determinism') or {}).get('fingerprint')}`",
        "",
        "## Regression",
        f"- upstream unchanged: {(summary.get('regression') or {}).get('unchanged')}",
        f"- changed_keys: {(summary.get('regression') or {}).get('changed_keys')}",
        "",
        f"## Claude: {summary.get('claude_calls', 0)}",
        f"## Engineering: {ENGINEERING_CHANGES}",
        "",
        "## Visual inspection",
        f"- contact sheets: {json.dumps(summary.get('visual_inspection'), default=str)}",
        "",
        "## Per-candidate results",
        "",
    ]

    for m in refined:
        loc = m.get("local_render_safe") or {}
        ctx = m.get("beam_context_render_safe") or {}
        lines.append(f"### {m.get('candidate_id')}")
        lines.append(f"- beam: {m.get('beam_id')} ann: {m.get('annotation_id')}")
        lines.append(f"- raw_text: `{m.get('raw_text')}`")
        lines.append(f"- reasons: {m.get('candidate_reason_codes')}")
        lines.append(f"- overall: {m.get('overall_readability')}")
        lines.append(
            f"- local: status={loc.get('readability_status')} "
            f"iters={loc.get('iterations_used')} "
            f"refined={loc.get('render_safety_refined')} "
            f"margins={loc.get('margins_px')} "
            f"flags={loc.get('flags')} "
            f"before={loc.get('initial_crop_bbox')} after={loc.get('crop_bbox')} "
            f"expand={loc.get('total_expansion_mm')}"
        )
        lines.append(
            f"- context: status={ctx.get('readability_status')} "
            f"iters={ctx.get('iterations_used')} "
            f"refined={ctx.get('render_safety_refined')} "
            f"margins={ctx.get('margins_px')} "
            f"flags={ctx.get('flags')}"
        )
        lines.append("")

    lines += [
        "## Final decision",
        str(summary.get("decision")),
        "",
        "Do NOT auto-mark READY_FOR_P2.5.3 — human visual inspection required.",
    ]

    status_path = out_root / "P2.5.2.2_STATUS.md"
    status_path.write_text("\n".join(lines), encoding="utf-8")
    _dump(out_root / "render_safety_summary.json", summary)
    _dump(out_root / "determinism_report.json", summary.get("determinism") or {})
    return {"status_md": str(status_path), "summary_json": str(out_root / "render_safety_summary.json")}


__all__ = ["write_reports"]
