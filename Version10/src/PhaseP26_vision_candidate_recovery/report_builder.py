"""P2.6 pilot reports. No steel accuracy / production promotion claims."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _pct(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{100.0 * float(v):.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def write_reports(
    *,
    out_root: Path,
    result: Dict[str, Any],
) -> Dict[str, str]:
    out_root = Path(out_root)
    reports = out_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    m = result.get("metrics") or {}
    rec = result.get("recommendation") or {}
    sel = result.get("selection") or {}
    tests = result.get("unit_tests") or {}
    prod = result.get("production") or {}
    fw = result.get("firewall") or {}
    examples = (result.get("evidence") or {}).get("examples") or []

    md = [
        "# P2.6 — Vision Candidate Recovery Pilot Status",
        "",
        f"- **MODEL_VERSION**: {result.get('model_version')}",
        f"- **PHASE**: {result.get('phase_id')} {result.get('phase_name')}",
        f"- **STATUS**: Shadow / research only. Production promotion is NOT AUTHORIZED.",
        f"- **PILOT_SET**: {result.get('pilot_set')}",
        f"- **PILOT_DRAWINGS**: Fifth Set Drawings (3 DXF; existing QA.3.0 / P250 crops)",
        f"- **PILOT_BEAMS**: {m.get('pilot_beams_inspected')}",
        f"- **SELECTION**: production signals only; GT used after Vision (`gt_used_for_selection={sel.get('gt_used_for_selection')}`)",
        f"- **TESTS**: {tests.get('passed')}/{tests.get('total')} ({'PASS' if tests.get('success') else 'FAIL'})",
        f"- **PRODUCTION_MUTATION**: {prod.get('production_mutation_count', 0)}",
        "",
        "## Vision",
        "",
        f"- **API_CALLS**: {m.get('vision_api_calls')}",
        f"- **CACHE_HITS**: {m.get('cache_hits')}",
        f"- **CACHE_MISSES**: {m.get('cache_misses')}",
        f"- **CANDIDATES**: {m.get('vision_candidates')}",
        f"- **MODEL**: claude-sonnet-4-5 temperature=0",
        f"- **ESTIMATED_USD**: {m.get('estimated_usd')}",
        "",
        "## Candidate results",
        "",
        f"- **ALREADY_DETECTED**: {m.get('already_detected')}",
        f"- **POTENTIALLY_MISSING**: {m.get('potentially_missing')}",
        f"- **GT_MATCHES**: {m.get('gt_matches')}",
        f"- **TRUE_RECOVERIES**: {m.get('true_recoveries')}",
        f"- **UNSUPPORTED**: {m.get('unsupported')}",
        f"- **AMBIGUOUS**: {m.get('ambiguous')}",
        f"- **GT-supported candidates**: {m.get('gt_supported_candidates')}",
        f"- **Missed GT bars on pilot beams (denominator)**: {m.get('missed_gt_bars_on_pilot_beams')}",
        "",
        "## Metrics",
        "",
        f"- **TRUE_RECOVERY_RATE**: {_pct(m.get('TRUE_RECOVERY_RATE'))}",
        f"- **VISION_CANDIDATE_PRECISION**: {_pct(m.get('VISION_CANDIDATE_PRECISION'))}",
        f"- **UNSUPPORTED_RATE**: {_pct(m.get('UNSUPPORTED_RATE'))}",
        f"- **DUPLICATE_RATE**: {_pct(m.get('DUPLICATE_RATE'))}",
        f"- **AMBIGUOUS_RATE**: {_pct(m.get('AMBIGUOUS_RATE'))}",
        "",
        "## Candidate-type breakdown",
        "",
        "```json",
        json.dumps(m.get("candidate_type_counts") or {}, indent=2),
        "```",
        "",
        "True recovery by type:",
        "",
        "```json",
        json.dumps(m.get("true_recovery_by_type") or {}, indent=2),
        "```",
        "",
        "True recovery by diameter:",
        "",
        "```json",
        json.dumps(m.get("true_recovery_by_diameter") or {}, indent=2),
        "```",
        "",
        "## Recommendation",
        "",
        f"- **STRENGTH**: {rec.get('strength')}",
        f"- **DECISION**: {rec.get('decision')}",
        f"- {rec.get('note')}",
        "",
        "This pilot MUST NOT be read as:",
        "",
        "- Vision steel accuracy",
        "- production accuracy improvement",
        "- overall five-set Vision accuracy",
        "- production bar detection accuracy",
        "- production readiness",
        "",
        "Correct terminology: Vision Candidate Recovery, Shadow Candidate, Pilot, True Recovery, Research Evidence, Deterministic Production Authority.",
        "",
        "## Visual evidence summary",
        "",
    ]
    if not examples:
        md.append("- No representative overlays were written.")
    for ex in examples:
        md.append(
            f"- `{ex.get('example_class')}`: `{ex.get('candidate_id')}` "
            f"text=`{ex.get('annotation_text')}` det=`{ex.get('deterministic_match_status')}` "
            f"gt=`{ex.get('gt_match_status')}`"
        )
    md += [
        "",
        "## Independent review (Claude Sonnet 4.6)",
        "",
        "- **BLOCKER**: none",
        "- **HIGH (fixed)**: OTHER_BEAM + family/diameter GT match was able to become TRUE_RECOVERY. Guard is now unconditional AMBIGUOUS. Unit test added. This path did not fire in the executed 18-beam run (all candidates TARGET_BEAM).",
        "- **MEDIUM**: `gap_reasons` were included in Claude metadata (task framing toward stirrup-gap). Not GT leakage. Disclose as a confound; strip from Vision metadata in the next experiment.",
        "- **MEDIUM**: TRUE_RECOVERY_RATE is conditional on the OCR + stirrup-text-no-object top-18, not a Fifth Set average.",
        "- **MEDIUM**: GT match is role-family + diameter (quantity/spacing not required). Sufficient for this pilot signal.",
        "",
        "The independent reviewer initially recommended REFINE_P2.6_PILOT because of the HIGH evaluation defect. That defect is now fixed without changing the executed Vision candidates or the measured 19 TRUE_RECOVERIES.",
        "",
        "## Firewall",
        "",
        f"- production mutation = {prod.get('production_mutation_count', 0)}",
        f"- steel / BBS / Excel unchanged (fingerprints compared): `{prod.get('fingerprints_ok')}`",
        f"- P2.5 regressions nested in unit tests",
        f"- firewall ok: `{fw.get('ok')}`",
        "",
        "## Scope limits",
        "",
        "- Fourth–Sixth full benchmark: NOT executed",
        "- five-set Vision KPI: NOT generated",
        "- production promotion: NOT performed",
        "- engineering recompute / SI.1 / R1.3 mutation: NONE",
        "",
    ]
    status_path = out_root / "P2.6_PILOT_STATUS.md"
    status_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    (reports / "P2.6_PILOT_STATUS.md").write_text(status_path.read_text(encoding="utf-8"), encoding="utf-8")
    (reports / "metrics.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
    return {
        "status": str(status_path),
        "metrics": str(reports / "metrics.json"),
    }


__all__ = ["write_reports"]
