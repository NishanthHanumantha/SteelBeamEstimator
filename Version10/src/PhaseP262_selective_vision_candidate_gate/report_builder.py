"""P2.6.2 status report. Gated replay — not a new Vision benchmark."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def _pct(v: Any) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, str):
        return v
    try:
        return f"{100.0 * float(v):.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    reports = out_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    m = result.get("metrics") or {}
    rec = result.get("recommendation") or {}
    sample = result.get("sample") or {}
    tests = result.get("unit_tests") or {}
    prod = result.get("production") or {}
    fw = result.get("firewall") or {}
    review = result.get("independent_review") or {}
    by_s = m.get("by_stratum") or {}
    by_t = m.get("by_candidate_type") or {}
    false_skips = result.get("false_skips") or []
    false_calls = result.get("false_calls") or []
    examples = (result.get("evidence") or {}).get("examples") or []

    md = [
        "# P2.6.2 — Selective Vision Candidate Gate Status",
        "",
        "Gated replay using frozen P2.6.1 Vision responses. This is not a new Vision benchmark.",
        "",
        "------------------------------------------------------------",
        "IDENTITY",
        "------------------------------------------------------------",
        "",
        f"- **MODEL_VERSION**: {result.get('model_version')}",
        f"- **PHASE**: {result.get('phase_id')} {result.get('phase_name')}",
        f"- **GATE_VERSION**: P262_SELECTIVE_GATE_V1_1",
        f"- **STATUS**: Shadow / research only. Production promotion is NOT AUTHORIZED.",
        f"- **EXECUTION_MODE**: {result.get('mode')}",
        f"- **PRODUCTION_MUTATION**: {prod.get('production_mutation_count', 0)}",
        f"- **TESTS**: {tests.get('passed')}/{tests.get('total')} ({'PASS' if tests.get('success') else 'FAIL'})",
        "",
        "------------------------------------------------------------",
        "DATASET",
        "------------------------------------------------------------",
        "",
        "- **source**: frozen P2.6.1 stratified sample (not resampled)",
        f"- **beams**: {m.get('TOTAL_BEAMS')}",
        f"- **drawing sets**: {sample.get('drawing_sets')}",
        f"- **strata**: {json.dumps(sample.get('selected_by_stratum') or {})}",
        f"- **seed**: {sample.get('seed')}",
        f"- **GT_USED_FOR_GATE = FALSE**",
        "",
        "------------------------------------------------------------",
        "GATE",
        "------------------------------------------------------------",
        "",
        f"- **total beams**: {m.get('TOTAL_BEAMS')}",
        f"- **CALL**: {m.get('CALL_BEAMS')}",
        f"- **SKIP**: {m.get('SKIP_BEAMS')}",
        f"- **HOLD**: {m.get('HOLD_BEAMS')}",
        f"- **call rate**: {_pct(m.get('CALL_RATE'))}",
        f"- **call reduction**: {_pct(m.get('CALL_REDUCTION'))}",
        "",
        "------------------------------------------------------------",
        "CANDIDATE RESULTS",
        "------------------------------------------------------------",
        "",
        f"- **baseline candidates**: {m.get('TOTAL_BASELINE_VISION_CANDIDATES')}",
        f"- **gated candidates**: {m.get('GATED_VISION_CANDIDATES')}",
        f"- **baseline duplicate rate**: {_pct(m.get('DUPLICATE_RATE_BASELINE'))}",
        f"- **gated duplicate rate**: {_pct(m.get('DUPLICATE_RATE_GATED'))}",
        f"- **baseline precision**: {_pct(m.get('BASELINE_PRECISION'))}",
        f"- **gated precision**: {_pct(m.get('GATED_PRECISION'))}",
        f"- **baseline unsupported**: {_pct(m.get('BASELINE_UNSUPPORTED_RATE'))}",
        f"- **gated unsupported**: {_pct(m.get('GATED_UNSUPPORTED_RATE'))}",
        f"- **baseline ambiguous**: {_pct(m.get('BASELINE_AMBIGUOUS_RATE'))}",
        f"- **gated ambiguous**: {_pct(m.get('GATED_AMBIGUOUS_RATE'))}",
        "",
        "------------------------------------------------------------",
        "RECOVERY",
        "------------------------------------------------------------",
        "",
        f"- **baseline TRUE_RECOVERIES**: {m.get('BASELINE_TRUE_RECOVERIES')}",
        f"- **gated TRUE_RECOVERIES**: {m.get('GATED_TRUE_RECOVERIES')}",
        f"- **retained**: {m.get('RECOVERIES_RETAINED')}",
        f"- **lost**: {m.get('RECOVERIES_LOST')}",
        f"- **recovery retention**: {_pct(m.get('RECOVERY_RETENTION_RATE'))}",
        f"- **false skips**: {m.get('FALSE_SKIPS')}",
        f"- **false calls**: {m.get('FALSE_CALLS')} (rate {_pct(m.get('FALSE_CALL_RATE'))})",
        f"- **TRUE_RECOVERIES per 100 calls (baseline)**: {m.get('TRUE_RECOVERIES_PER_100_VISION_CALLS_BASELINE')}",
        f"- **TRUE_RECOVERIES per 100 calls (gated)**: {m.get('TRUE_RECOVERIES_PER_100_VISION_CALLS_GATED')}",
        "",
        "------------------------------------------------------------",
        "STRATUM",
        "------------------------------------------------------------",
        "",
        "Stratum is evaluation-only. The gate does not decide CALL/SKIP from DIFFICULT/NORMAL/EASY.",
        "",
    ]
    for name in ("DIFFICULT", "NORMAL", "EASY"):
        b = by_s.get(name) or {}
        md.append(
            f"- **{name}**: beams={b.get('beams')} call={b.get('call')} "
            f"call_rate={_pct(b.get('call_rate'))} saved={b.get('calls_saved')} "
            f"retained={b.get('recoveries_retained')} lost={b.get('recoveries_lost')} "
            f"gated_dup={_pct((b.get('gated') or {}).get('duplicate_rate'))} "
            f"gated_prec={_pct((b.get('gated') or {}).get('precision'))}"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "CANDIDATE TYPE",
        "------------------------------------------------------------",
        "",
    ]
    for name in ("STIRRUP", "LONGITUDINAL_REINFORCEMENT", "SIDE_FACE_REINFORCEMENT", "OTHER"):
        b = by_t.get(name) or {}
        md.append(
            f"- **{name}**: baseline={b.get('baseline_candidates')} gated={b.get('gated_candidates')} "
            f"dup {b.get('baseline_duplicates')}→{b.get('gated_duplicates')} "
            f"recoveries {b.get('baseline_true_recoveries')}→{b.get('gated_true_recoveries')} "
            f"lost={b.get('lost_recoveries')}"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "GATE REASONS",
        "------------------------------------------------------------",
        "",
        f"- **CALL**: `{json.dumps(m.get('call_reason_counts') or {})}`",
        f"- **SKIP**: `{json.dumps(m.get('skip_reason_counts') or {})}`",
        "",
        "------------------------------------------------------------",
        "FALSE SKIPS",
        "------------------------------------------------------------",
        "",
    ]
    if not false_skips:
        md.append("- none")
    for fs in false_skips[:12]:
        md.append(
            f"- `{fs.get('set_key')}/{fs.get('beam_id')}` text=`{fs.get('annotation')}` "
            f"class=`{fs.get('candidate_class')}` skip_reasons=`{fs.get('why_gate_skipped')}`"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "FALSE CALLS",
        "------------------------------------------------------------",
        "",
    ]
    if not false_calls:
        md.append("- none")
    for fc in false_calls[:12]:
        md.append(
            f"- `{fc.get('set_key')}/{fc.get('beam_id')}` reasons=`{fc.get('reason_codes')}` "
            f"cands={fc.get('candidate_count')} statuses=`{fc.get('gt_status_counts')}`"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "VISUAL EVIDENCE",
        "------------------------------------------------------------",
        "",
    ]
    if not examples:
        md.append("- No representative overlays were written.")
    for ex in examples:
        md.append(
            f"- `{ex.get('example_class')}`: `{ex.get('set_key')}/{ex.get('beam_id')}` "
            f"gate=`{ex.get('gate_decision')}` text=`{ex.get('annotation_text')}`"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "COST",
        "------------------------------------------------------------",
        "",
        f"- **baseline hypothetical calls**: {m.get('hypothetical_baseline_calls')}",
        f"- **gated calls**: {m.get('gated_calls')}",
        f"- **calls saved**: {m.get('calls_saved')}",
        f"- **replay cost**: ${m.get('replay_cost_usd')}",
        f"- **optional live cost**: {result.get('live_cost_usd', 'not run')}",
        "",
        "------------------------------------------------------------",
        "FIREWALL",
        "------------------------------------------------------------",
        "",
        f"- production mutation = {prod.get('production_mutation_count', 0)}",
        f"- steel / BBS / Excel unchanged: `{prod.get('fingerprints_ok')}`",
        f"- firewall ok: `{fw.get('ok')}`",
        "",
        "------------------------------------------------------------",
        "REVIEW",
        "------------------------------------------------------------",
        "",
        f"- **status**: {review.get('status') or 'PENDING'}",
        f"- **BLOCKER**: {json.dumps(review.get('blocker') or [])}",
        f"- **HIGH**: {json.dumps(review.get('high') or [])}",
        f"- **MEDIUM**: {json.dumps(review.get('medium') or [])}",
        f"- **LOW**: {json.dumps(review.get('low') or [])}",
        f"- **recommended_decision**: {review.get('recommended_decision') or rec.get('decision')}",
        f"- **notes**: {review.get('notes') or 'none recorded yet'}",
        "",
        "------------------------------------------------------------",
        "DECISION",
        "------------------------------------------------------------",
        "",
        f"- **STRENGTH**: {rec.get('strength')}",
        f"- **DECISION**: {rec.get('decision')}",
        f"- {rec.get('note')}",
        "",
        "Allowed: PROCEED_TO_ENGINEERING_RECOMPUTE_PILOT | REFINE_SELECTIVE_GATE | STOP_NEGATIVE.",
        "NEVER: PRODUCTION_READY.",
        "",
        "P2.6.2 ends at a selective shadow candidate set. Engineering recompute is not authorized.",
        "",
    ]
    status_path = out_root / "P2.6.2_STATUS.md"
    text = "\n".join(md) + "\n"
    status_path.write_text(text, encoding="utf-8")
    (reports / "P2.6.2_STATUS.md").write_text(text, encoding="utf-8")
    (reports / "metrics.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
    return {"status": str(status_path), "metrics": str(reports / "metrics.json")}


__all__ = ["write_reports"]
