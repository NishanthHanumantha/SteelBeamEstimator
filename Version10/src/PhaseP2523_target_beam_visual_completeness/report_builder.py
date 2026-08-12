"""Status reports for P2.5.2.3."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import (
    ENGINEERING_CHANGES,
    KNOWN_PROBLEM_BEAMS,
    MODEL_VERSION,
    PHASE_ID,
    PHASE_NAME,
    TARGET_BEAM_EDGE_MARGIN_PX,
)

MODEL_VERSION_LOCAL = MODEL_VERSION


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def write_reports(
    *, out_root: Path, summary: Dict[str, Any], refined: List[Dict[str, Any]]
) -> Dict[str, str]:
    out_root = Path(out_root)
    m = summary.get("metrics") or {}
    lines = [
        "# P2.5.2.3 STATUS",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"PHASE_ID: {PHASE_ID}",
        f"PHASE_NAME: {PHASE_NAME}",
        f"PASS / FAIL / REVIEW: {summary.get('pass_fail')}",
        "",
        f"Candidate count: {m.get('TOTAL_ACTIVE')}",
        f"PASS: {m.get('PASS')}",
        f"PARTIAL: {m.get('PARTIAL')}",
        f"FAIL: {m.get('FAIL')}",
        f"REVIEW: {m.get('REVIEW')}",
        "",
        f"Target beam completeness rate: {m.get('TARGET_BEAM_COMPLETENESS_RATE')}%",
        f"Annotation visibility: {m.get('ANNOTATION_VISIBILITY_RATE')}%",
        f"Leader visibility: {m.get('LEADER_VISIBILITY_RATE')}%",
        f"Relevant reinforcement visibility: {m.get('REINFORCEMENT_VISIBILITY_RATE')}%",
        "",
        f"Rejected evidence excluded: {m.get('REJECTED_EVIDENCE_EXCLUDED')}",
        f"Synthetic geometry: {m.get('SYNTHETIC_GEOMETRY')}",
        f"Extreme crops: {m.get('EXTREME_CROPS')}",
        f"Beam edge margin px: {TARGET_BEAM_EDGE_MARGIN_PX}",
        f"Expanded candidates: {m.get('EXPANDED_COUNT')}",
        f"Max side expansion mm: {m.get('MAX_SIDE_EXPANSION_MM')}",
        "",
        f"Determinism: {(summary.get('determinism') or {}).get('determinism_status')}",
        f"Claude calls: {summary.get('claude_calls', 0)}",
        f"Engineering changes: {ENGINEERING_CHANGES}",
        f"Regression: {'PASS' if (summary.get('regression') or {}).get('unchanged') else 'FAIL'}",
        "",
        "## Known problem beams",
    ]
    for bid in KNOWN_PROBLEM_BEAMS:
        kb = (summary.get("known_beams") or {}).get(bid) or {}
        lines.append(f"- {bid}: {json.dumps(kb, default=str)}")

    lines += ["", "## Per-candidate", ""]
    for r in refined:
        loc = r.get("local_target_complete") or {}
        lines.append(f"### {r.get('candidate_id')}")
        lines.append(f"- beam={r.get('beam_id')} text=`{r.get('raw_text')}`")
        lines.append(f"- overall={r.get('overall_completeness')}")
        lines.append(
            f"- local={loc.get('target_beam_visual_completeness')} "
            f"unsafe={loc.get('unsafe_sides')} "
            f"expand={loc.get('expansion_mm')} "
            f"reasons={loc.get('completeness_reason_codes')}"
        )
        lines.append(
            f"- before={loc.get('previous_crop_bbox')} after={loc.get('final_crop_bbox')}"
        )
        lines.append("")

    lines += [
        "## Decision",
        str(summary.get("decision")),
        "",
        "Human visual inspection still required before Claude Vision (P2.5.3).",
    ]
    status_path = out_root / "P2.5.2.3_STATUS.md"
    status_path.write_text("\n".join(lines), encoding="utf-8")
    _dump(out_root / "manifest.json", {"summary": summary, "candidates": refined})
    _dump(out_root / "diagnostics" / "summary.json", summary)
    return {"status_md": str(status_path)}


__all__ = ["write_reports"]
