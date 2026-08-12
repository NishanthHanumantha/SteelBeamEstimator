"""Status / CSV reports for P2.5.3."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .config import (
    ENGINEERING_CHANGES,
    MODEL_VERSION,
    PHASE_ID,
    PHASE_NAME,
    PRIMARY_EVIDENCE_MODE,
    PROMPT_VERSION,
    SCHEMA_VERSION,
)

MODEL_VERSION_LOCAL = MODEL_VERSION


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def write_reports(
    *,
    out_root: Path,
    summary: Dict[str, Any],
    results: List[Dict[str, Any]],
) -> Dict[str, str]:
    out_root = Path(out_root)
    metrics = summary.get("metrics") or {}
    counts = metrics.get("counts") or {}

    lines = [
        "# P2.5.3 STATUS",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"PHASE_ID: {PHASE_ID}",
        f"PHASE_NAME: {PHASE_NAME}",
        f"PASS / FAIL: {summary.get('pass_fail')}",
        f"SCOPE: {summary.get('scope')}",
        f"MODE: PILOT ONLY — NO PRODUCTION PROMOTION",
        "",
        f"Candidate count: {metrics.get('CLAUDE_CALL_COUNT')}",
        f"Claude model: {summary.get('claude_model')}",
        f"Claude call count: {metrics.get('CLAUDE_CALL_COUNT')}",
        f"Evidence mode: {PRIMARY_EVIDENCE_MODE}",
        f"Prompt version: {PROMPT_VERSION}",
        f"Schema version: {SCHEMA_VERSION}",
        "",
        "## Results",
        f"- Resolved status: {counts.get('resolved_status')}",
        f"- Partial status: {counts.get('partial_status')}",
        f"- Exact interpretation: {counts.get('exact')}",
        f"- Partial interpretation: {counts.get('partial')}",
        f"- Incorrect: {counts.get('incorrect')}",
        f"- Hallucination: {counts.get('hallucination')}",
        f"- Appropriate abstention: {counts.get('appropriate_abstention')}",
        f"- Conflict detected: {counts.get('conflict')}",
        "",
        f"VISION_RESOLUTION_RATE: {metrics.get('VISION_RESOLUTION_RATE')}",
        f"VISION_EXACT_INTERPRETATION_RATE: {metrics.get('VISION_EXACT_INTERPRETATION_RATE')}",
        f"VISION_PARTIAL_INTERPRETATION_RATE: {metrics.get('VISION_PARTIAL_INTERPRETATION_RATE')}",
        f"VISION_INCORRECT_RATE: {metrics.get('VISION_INCORRECT_RATE')}",
        f"VISION_HALLUCINATION_RATE: {metrics.get('VISION_HALLUCINATION_RATE')}",
        f"VISION_APPROPRIATE_ABSTENTION_RATE: {metrics.get('VISION_APPROPRIATE_ABSTENTION_RATE')}",
        f"CLAUDE_SUCCESS_RATE: {metrics.get('CLAUDE_SUCCESS_RATE')}",
        f"CLAUDE_VALID_RESPONSE_RATE: {metrics.get('CLAUDE_VALID_RESPONSE_RATE')}",
        f"GROUND_TRUTH_COVERAGE: {metrics.get('GROUND_TRUTH_COVERAGE')}",
        "",
        "## Category metrics",
        f"- OCR: {json.dumps((metrics.get('category') or {}).get('ocr_corruption'), default=str)}",
        f"- Stirrup: {json.dumps((metrics.get('category') or {}).get('stirrup'), default=str)}",
        f"- Semantic: {json.dumps((metrics.get('category') or {}).get('semantic_context'), default=str)}",
        f"- Difficult visual: {json.dumps((metrics.get('category') or {}).get('visually_difficult'), default=str)}",
        "",
        f"## Token usage: {json.dumps(metrics.get('token_usage'), default=str)}",
        f"Estimated API cost USD (approx Sonnet list rates): {summary.get('estimated_api_cost_usd')}",
        f"Cost note: {summary.get('estimated_cost_note')}",
        "",
        f"## Golden cases: {json.dumps(summary.get('golden'), default=str)}",
        f"## Unit tests: {json.dumps(summary.get('unit_tests'), default=str)}",
        f"## Firewall: {json.dumps(summary.get('firewall'), default=str)}",
        "",
        f"## Regression: {'PASS' if (summary.get('regression') or {}).get('unchanged') else 'FAIL'}",
        f"## Determinism / variability: {json.dumps(summary.get('determinism'), default=str)}",
        f"## Engineering changes: {ENGINEERING_CHANGES}",
        f"## Production output changes: NONE",
        "",
        f"## Decision: {summary.get('decision')}",
        f"## P2.5.4 recommendation: {summary.get('decision')}",
        "",
        "## Candidate-level results",
        "",
    ]
    for r in results:
        vi = r.get("validated_interpretation") or {}
        ev = r.get("evaluation") or {}
        lines.append(f"### {r.get('candidate_id')}")
        lines.append(f"- beam={r.get('beam_id')} text=`{r.get('raw_text')}`")
        lines.append(
            f"- status={vi.get('interpretation_status')} type={vi.get('reinforcement_type')} "
            f"legs={vi.get('legs')} dia={vi.get('diameter_mm')} spacing={vi.get('spacing_mm')}"
        )
        lines.append(
            f"- eval={ev.get('evaluation')} valid={(r.get('validation') or {}).get('valid')} "
            f"api={(r.get('claude_call') or {}).get('success')}"
        )
        lines.append(f"- normalized=`{vi.get('normalized_notation')}`")
        lines.append("")

    status_path = out_root / "P2.5.3_STATUS.md"
    status_path.write_text("\n".join(lines), encoding="utf-8")
    _dump(out_root / "pilot_summary.json", summary)

    csv_path = out_root / "pilot_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "candidate_id",
                "beam_id",
                "raw_text",
                "api_success",
                "valid",
                "interpretation_status",
                "reinforcement_type",
                "legs",
                "diameter_mm",
                "spacing_mm",
                "evaluation",
                "exact_match",
            ]
        )
        for r in results:
            vi = r.get("validated_interpretation") or {}
            ev = r.get("evaluation") or {}
            w.writerow(
                [
                    r.get("candidate_id"),
                    r.get("beam_id"),
                    r.get("raw_text"),
                    (r.get("claude_call") or {}).get("success"),
                    (r.get("validation") or {}).get("valid"),
                    vi.get("interpretation_status"),
                    vi.get("reinforcement_type"),
                    vi.get("legs"),
                    vi.get("diameter_mm"),
                    vi.get("spacing_mm"),
                    ev.get("evaluation"),
                    ev.get("exact_match"),
                ]
            )

    return {"status_md": str(status_path), "csv": str(csv_path)}


__all__ = ["write_reports"]
