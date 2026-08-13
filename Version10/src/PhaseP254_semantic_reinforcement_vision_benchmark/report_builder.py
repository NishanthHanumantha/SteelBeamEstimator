"""Status / CSV / markdown reports for P2.5.4."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .config import ENGINEERING_CHANGES, MODEL_VERSION, PHASE_ID, PHASE_NAME, SCHEMA_VERSION
from .config import PRIMARY_EVIDENCE_MODE, PROMPT_VERSION

MODEL_VERSION_LOCAL = MODEL_VERSION


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _fmt(v: Any) -> str:
    if v is None:
        return "N/A (no ground truth)"
    return str(v)


def write_reports(
    *,
    out_root: Path,
    summary: Dict[str, Any],
    results: List[Dict[str, Any]],
) -> Dict[str, str]:
    out_root = Path(out_root)
    reports = out_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    metrics = summary.get("metrics") or {}
    counts = metrics.get("counts") or {}
    dist = summary.get("class_distribution") or {}

    lines = [
        "# P2.5.4 STATUS",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"PHASE_ID: {PHASE_ID}",
        f"PHASE_NAME: {PHASE_NAME}",
        f"PASS / FAIL: {summary.get('pass_fail')}",
        f"SCOPE: {summary.get('scope')}",
        "MODE: SHADOW ONLY — NO PRODUCTION PROMOTION",
        "",
        f"Benchmark size: {metrics.get('CLAUDE_CALL_COUNT')}",
        f"Ground truth coverage: {metrics.get('GROUND_TRUTH_COVERAGE')}",
        "",
        "## Category distribution",
        f"- LONGITUDINAL: {dist.get('LONGITUDINAL', 0)}",
        f"- STIRRUP: {dist.get('STIRRUP', 0)}",
        f"- SIDE_FACE: {dist.get('SIDE_FACE', 0)}",
        f"- SUPPORT_TOP: {dist.get('SUPPORT_TOP', 0)}",
        f"- MULTI_ANNOTATION: {dist.get('MULTI_ANNOTATION', 0)}",
        f"- BEAM_ASSOCIATION: {dist.get('BEAM_ASSOCIATION', 0)}",
        f"- DIFFICULT_VISUAL: {dist.get('DIFFICULT_VISUAL', 0)}",
        f"- OCR_CONTROL: {dist.get('OCR_CONTROL', 0)}",
        f"- tag_distribution: {json.dumps(summary.get('tag_distribution') or {}, default=str)}",
        "",
        f"Claude model: {summary.get('claude_model')}",
        f"Claude call count: {metrics.get('CLAUDE_CALL_COUNT')}",
        f"Evidence mode: {PRIMARY_EVIDENCE_MODE}",
        f"Prompt version: {PROMPT_VERSION}",
        f"Schema version: {SCHEMA_VERSION}",
        f"Temperature: {summary.get('temperature')}",
        "",
        "## Results",
        f"- Resolved: {counts.get('resolved_status')}",
        f"- Partial: {counts.get('partial_status')}",
        f"- Abstained: {counts.get('abstained_status')}",
        f"- Exact: {counts.get('exact')}",
        f"- Partial eval: {counts.get('partial')}",
        f"- Incorrect: {counts.get('incorrect')}",
        f"- Hallucination: {counts.get('hallucination')}",
        f"- Appropriate abstention: {counts.get('appropriate_abstention')}",
        "",
        f"SEMANTIC_INTERPRETATION_ACCURACY: {_fmt(metrics.get('SEMANTIC_INTERPRETATION_ACCURACY'))}",
        f"TYPE_ACCURACY: {_fmt(metrics.get('TYPE_ACCURACY'))}",
        f"ROLE_ACCURACY: {_fmt(metrics.get('ROLE_ACCURACY'))}",
        f"DIAMETER_ACCURACY: {_fmt(metrics.get('DIAMETER_ACCURACY'))}",
        f"QUANTITY_ACCURACY: {_fmt(metrics.get('QUANTITY_ACCURACY'))}",
        f"SPACING_ACCURACY: {_fmt(metrics.get('SPACING_ACCURACY'))}",
        f"BEAM_ASSOCIATION_ACCURACY: {_fmt(metrics.get('BEAM_ASSOCIATION_ACCURACY'))}",
        f"ZONE_ACCURACY: {_fmt(metrics.get('ZONE_ACCURACY'))}",
        f"HALLUCINATION_RATE: {_fmt(metrics.get('HALLUCINATION_RATE'))}",
        f"APPROPRIATE_ABSTENTION_RATE: {_fmt(metrics.get('APPROPRIATE_ABSTENTION_RATE'))}",
        f"VISION_ONLY_RESOLUTION_RATE: {_fmt(metrics.get('VISION_ONLY_RESOLUTION_RATE'))}",
        f"BOTH_AGREE_RATE: {_fmt(metrics.get('BOTH_AGREE_RATE'))}",
        f"VISION_CONFLICT_RATE: {_fmt(metrics.get('VISION_CONFLICT_RATE'))}",
        "",
        "## Category-level metrics",
        json.dumps(metrics.get("category") or {}, indent=2, default=str),
        "",
        f"## Token usage: {json.dumps(metrics.get('token_usage'), default=str)}",
        f"Estimated API cost USD (approx Sonnet list rates): {summary.get('estimated_api_cost_usd')}",
        f"Cost note: {summary.get('estimated_cost_note')}",
        "",
        "## Top successful examples",
    ]
    successes = [r for r in results if (r.get("evaluation") or {}).get("evaluation") == "EXACT"]
    for r in successes[:8]:
        lines.append(
            f"- {r.get('candidate_id')} `{r.get('raw_text')}` class={r.get('semantic_class')} "
            f"cmp={(r.get('comparison') or {}).get('class')}"
        )
    lines += ["", "## Top failed / conflict examples"]
    fails = [
        r
        for r in results
        if (r.get("evaluation") or {}).get("evaluation")
        in ("INCORRECT", "HALLUCINATION", "INVALID_RESPONSE")
        or (r.get("comparison") or {}).get("class") in ("VISION_WRONG", "VISION_CONFLICT")
    ]
    for r in fails[:8]:
        lines.append(
            f"- {r.get('candidate_id')} `{r.get('raw_text')}` eval={(r.get('evaluation') or {}).get('evaluation')} "
            f"cmp={(r.get('comparison') or {}).get('class')} flags={(r.get('conflicts') or {}).get('flags')}"
        )
    lines += ["", "## Abstention examples"]
    abs_ex = [
        r
        for r in results
        if (r.get("evaluation") or {}).get("evaluation") == "APPROPRIATE_ABSTENTION"
        or (r.get("validated_interpretation") or {}).get("interpretation_status")
        == "INSUFFICIENT_EVIDENCE"
    ]
    for r in abs_ex[:8]:
        lines.append(f"- {r.get('candidate_id')} `{r.get('raw_text')}` class={r.get('semantic_class')}")

    lines += [
        "",
        f"## Golden / firewall: {json.dumps(summary.get('firewall'), default=str)}",
        f"## Unit tests: {json.dumps(summary.get('unit_tests'), default=str)}",
        f"## Regression: {'PASS' if (summary.get('regression') or {}).get('unchanged') else 'FAIL'}",
        f"## Determinism / variability: {json.dumps(summary.get('determinism'), default=str)}",
        f"## Engineering changes: {ENGINEERING_CHANGES}",
        "## Production output changes: NONE",
        "",
        f"## Decision: {summary.get('decision')}",
        "",
        "## Candidate-level results",
        "",
    ]
    for r in results:
        vi = r.get("validated_interpretation") or {}
        ev = r.get("evaluation") or {}
        lines.append(f"### {r.get('candidate_id')}")
        lines.append(f"- beam={r.get('beam_id')} class={r.get('semantic_class')} text=`{r.get('raw_text')}`")
        lines.append(
            f"- status={vi.get('interpretation_status')} type={vi.get('semantic_type')} "
            f"role={vi.get('role')} assoc={vi.get('beam_association')} "
            f"qty={vi.get('quantity')} dia={vi.get('diameter_mm')} legs={vi.get('legs')} "
            f"spacing={vi.get('spacing_mm')}"
        )
        lines.append(
            f"- eval={ev.get('evaluation')} cmp={(r.get('comparison') or {}).get('class')} "
            f"valid={(r.get('validation') or {}).get('valid')} api={(r.get('claude_call') or {}).get('success')}"
        )
        lines.append("")

    status_path = out_root / "P2.5.4_STATUS.md"
    status_path.write_text("\n".join(lines), encoding="utf-8")
    _dump(out_root / "benchmark_summary.json", summary)

    acc_lines = [
        "# Semantic accuracy report",
        "",
        f"SEMANTIC_INTERPRETATION_ACCURACY: {_fmt(metrics.get('SEMANTIC_INTERPRETATION_ACCURACY'))}",
        f"TYPE_ACCURACY: {_fmt(metrics.get('TYPE_ACCURACY'))}",
        f"ROLE_ACCURACY: {_fmt(metrics.get('ROLE_ACCURACY'))}",
        f"VISION_ONLY_RESOLUTION_RATE: {_fmt(metrics.get('VISION_ONLY_RESOLUTION_RATE'))}",
        f"HALLUCINATION_RATE: {_fmt(metrics.get('HALLUCINATION_RATE'))}",
        "",
        "Vision-only resolved cases (genuine Vision value):",
    ]
    for r in results:
        if (r.get("comparison") or {}).get("class") == "VISION_ONLY_RESOLVED":
            acc_lines.append(f"- {r.get('candidate_id')} `{r.get('raw_text')}`")
    (reports / "semantic_accuracy_report.md").write_text("\n".join(acc_lines), encoding="utf-8")
    (reports / "category_metrics.md").write_text(
        "# Category metrics\n\n```json\n"
        + json.dumps(metrics.get("category") or {}, indent=2, default=str)
        + "\n```\n",
        encoding="utf-8",
    )
    conflict_lines = ["# Conflict analysis", ""]
    for r in results:
        flags = (r.get("conflicts") or {}).get("flags") or []
        if flags:
            conflict_lines.append(
                f"- {r.get('candidate_id')} flags={flags} details={json.dumps((r.get('conflicts') or {}).get('details'), default=str)}"
            )
    if len(conflict_lines) == 2:
        conflict_lines.append("No engineering consistency conflicts recorded.")
    (reports / "conflict_analysis.md").write_text("\n".join(conflict_lines), encoding="utf-8")

    csv_path = out_root / "benchmark_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "candidate_id",
                "beam_id",
                "raw_text",
                "semantic_class",
                "api_success",
                "valid",
                "interpretation_status",
                "semantic_type",
                "role",
                "beam_association",
                "evaluation",
                "comparison",
            ]
        )
        for r in results:
            vi = r.get("validated_interpretation") or {}
            w.writerow(
                [
                    r.get("candidate_id"),
                    r.get("beam_id"),
                    r.get("raw_text"),
                    r.get("semantic_class"),
                    (r.get("claude_call") or {}).get("success"),
                    (r.get("validation") or {}).get("valid"),
                    vi.get("interpretation_status"),
                    vi.get("semantic_type"),
                    vi.get("role"),
                    vi.get("beam_association"),
                    (r.get("evaluation") or {}).get("evaluation"),
                    (r.get("comparison") or {}).get("class"),
                ]
            )
    return {"status_md": str(status_path), "csv": str(csv_path)}


__all__ = ["write_reports"]
