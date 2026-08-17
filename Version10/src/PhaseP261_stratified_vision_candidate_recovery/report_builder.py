"""P2.6.1 stratified benchmark reports. No steel accuracy / production promotion."""
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


def _stratum_block(name: str, block: Dict[str, Any]) -> list:
    return [
        f"### {name}",
        "",
        f"- **candidates**: {block.get('candidates')}",
        f"- **true recoveries**: {block.get('true_recoveries')}",
        f"- **strict true recoveries**: {block.get('strict_true_recoveries')}",
        f"- **precision**: {_pct(block.get('VISION_CANDIDATE_PRECISION'))}",
        f"- **unsupported**: {block.get('unsupported')} ({_pct(block.get('UNSUPPORTED_RATE'))})",
        f"- **duplicate**: {block.get('already_detected')} ({_pct(block.get('DUPLICATE_RATE'))})",
        f"- **ambiguous**: {block.get('ambiguous')} ({_pct(block.get('AMBIGUOUS_RATE'))})",
        f"- **TRUE_RECOVERY_RATE**: {_pct(block.get('TRUE_RECOVERY_RATE'))}",
        f"- **missed GT bars (denominator)**: {block.get('missed_gt_bars')}",
        "",
    ]


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> Dict[str, str]:
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
    review = result.get("independent_review") or {}
    by_stratum = m.get("by_stratum") or {}
    by_type = m.get("by_candidate_type") or {}
    by_set = m.get("by_drawing_set") or {}
    known = m.get("known_vs_unseen") or {}

    md = [
        "# P2.6.1 — Stratified Vision Candidate Recovery Status",
        "",
        "This is a stratified sample, not a full drawing-set benchmark.",
        "",
        "------------------------------------------------------------",
        "IDENTITY",
        "------------------------------------------------------------",
        "",
        f"- **MODEL_VERSION**: {result.get('model_version')}",
        f"- **PHASE**: {result.get('phase_id')} {result.get('phase_name')}",
        f"- **STATUS**: Shadow / research only. Production promotion is NOT AUTHORIZED.",
        f"- **PILOT_SCOPE**: {result.get('scope')} — Fourth / Fifth / Sixth stratified sample",
        f"- **DRAWING_SETS**: {', '.join((sel.get('drawing_sets') or []))}",
        f"- **BEAMS**: {m.get('BEAMS_INSPECTED')} (target ~75)",
        f"- **TESTS**: {tests.get('passed')}/{tests.get('total')} ({'PASS' if tests.get('success') else 'FAIL'})",
        f"- **PRODUCTION_MUTATION**: {prod.get('production_mutation_count', 0)}",
        f"- **PARTIAL_EXECUTION**: {result.get('partial_execution', False)}",
        "",
        "------------------------------------------------------------",
        "SAMPLING",
        "------------------------------------------------------------",
        "",
        f"- **selection seed**: {sel.get('seed')}",
        f"- **universe scored**: {sel.get('universe_scored')}",
        f"- **eligible with crop**: {sel.get('eligible_with_crop')}",
        f"- **available by stratum**: `{json.dumps(sel.get('available_by_stratum') or {})}`",
        f"- **selected by stratum**: `{json.dumps(sel.get('selected_by_stratum') or {})}`",
        f"- **selected by drawing set**: `{json.dumps(sel.get('selected_by_set') or {})}`",
        f"- **P2.6 Fifth-pilot overlap in sample**: {sel.get('p26_overlap_in_sample')}",
        f"- **drawing visibility**: {sel.get('drawing_visibility')}",
        f"- **GT_USED_FOR_SELECTION = FALSE** (`{sel.get('gt_used_for_selection')}`)",
        f"- **estimator_used_for_selection**: `{sel.get('estimator_used_for_selection')}`",
        "",
        "Selection features (production signals only): OCR_CORRUPTION_SIGNAL, "
        "STIRRUP_TEXT_NO_OBJECT, INCOMPLETE_PARSE_SIGNAL, SPARSE_REINFORCEMENT_SIGNAL, "
        "UNASSOCIATED_REINFORCEMENT_TEXT, MULTI_ANNOTATION_SIGNAL, DIFFICULT_NOTATION_SIGNAL, "
        "COMPLETE_PARSE_SIGNAL, REINFORCEMENT_DENSITY, NUMBER_OF_DETERMINISTIC_OBJECTS, "
        "NUMBER_OF_UNASSOCIATED_ANNOTATIONS.",
        "",
        "Stratum assignment does not use GT, estimator steel, or benchmark answers.",
        "",
        "------------------------------------------------------------",
        "VISION",
        "------------------------------------------------------------",
        "",
        f"- **live calls**: {m.get('live_calls')}",
        f"- **cache hits**: {m.get('cache_hits')}",
        f"- **cache misses**: {m.get('cache_misses')}",
        f"- **budget stops**: {m.get('budget_stops')}",
        f"- **model**: claude-sonnet-4-5",
        f"- **temperature**: 0",
        f"- **tokens**: input={m.get('input_tokens')} output={m.get('output_tokens')}",
        f"- **estimated cost**: ${m.get('estimated_usd')}",
        f"- **cost per TRUE_RECOVERY**: {m.get('cost_per_true_recovery')}",
        f"- **prompt**: P261_NEUTRAL_VISION_CANDIDATE_PROMPT_V1 (no gap_reasons / stratum / selection_reason)",
        "",
        "------------------------------------------------------------",
        "OVERALL RESULTS",
        "------------------------------------------------------------",
        "",
        f"- **candidates**: {m.get('VISION_CANDIDATES')}",
        f"- **duplicates (ALREADY_DETECTED)**: {m.get('ALREADY_DETECTED')}",
        f"- **potentially missing**: {m.get('POTENTIALLY_MISSING')}",
        f"- **GT supported**: {m.get('GT_SUPPORTED')}",
        f"- **true recoveries (P2.6-compatible family+diameter)**: {m.get('TRUE_RECOVERIES')}",
        f"- **strict true recoveries (family+diameter+quantity)**: {m.get('STRICT_TRUE_RECOVERIES')}",
        f"- **unsupported**: {m.get('UNSUPPORTED')}",
        f"- **ambiguous**: {m.get('AMBIGUOUS')}",
        f"- **missed GT bars on sampled beams**: {m.get('missed_gt_bars_on_sampled_beams')}",
        "",
        f"- **TRUE_RECOVERY_RATE**: {_pct(m.get('TRUE_RECOVERY_RATE'))}",
        f"- **STRICT_TRUE_RECOVERY_RATE**: {_pct(m.get('STRICT_TRUE_RECOVERY_RATE'))}",
        f"- **VISION_CANDIDATE_PRECISION**: {_pct(m.get('VISION_CANDIDATE_PRECISION'))}",
        f"- **UNSUPPORTED_RATE**: {_pct(m.get('UNSUPPORTED_RATE'))}",
        f"- **DUPLICATE_RATE**: {_pct(m.get('DUPLICATE_RATE'))}",
        f"- **AMBIGUOUS_RATE**: {_pct(m.get('AMBIGUOUS_RATE'))}",
        "",
        "Primary TRUE_RECOVERY definition is P2.6-compatible (role family + diameter). "
        "The stricter metric is reported separately and was not used to retune selection.",
        "",
        "------------------------------------------------------------",
        "STRATUM RESULTS",
        "------------------------------------------------------------",
        "",
    ]
    for name in ("DIFFICULT", "NORMAL", "EASY"):
        md.extend(_stratum_block(name, by_stratum.get(name) or {}))

    md += [
        "------------------------------------------------------------",
        "CANDIDATE TYPE",
        "------------------------------------------------------------",
        "",
    ]
    for tname in (
        "STIRRUP",
        "LONGITUDINAL_REINFORCEMENT",
        "SIDE_FACE_REINFORCEMENT",
        "SPACER",
        "OTHER",
        "UNKNOWN",
    ):
        block = by_type.get(tname) or {}
        md.append(
            f"- **{tname}**: candidates={block.get('candidates')} "
            f"duplicates={block.get('already_detected')} "
            f"true_recoveries={block.get('true_recoveries')} "
            f"unsupported={block.get('unsupported')} "
            f"precision={_pct(block.get('VISION_CANDIDATE_PRECISION'))}"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "DRAWING SET",
        "------------------------------------------------------------",
        "",
        "This is a stratified sample, not a full drawing-set benchmark.",
        "",
    ]
    if not by_set:
        md.append("- No drawing-set slices (no candidates).")
    for name, block in by_set.items():
        md.append(
            f"- **{name}**: candidates={block.get('candidates')} "
            f"true_recoveries={block.get('true_recoveries')} "
            f"precision={_pct(block.get('VISION_CANDIDATE_PRECISION'))} "
            f"TRUE_RECOVERY_RATE={_pct(block.get('TRUE_RECOVERY_RATE'))}"
        )
    md += [
        "",
        "------------------------------------------------------------",
        "KNOWN VS UNSEEN",
        "------------------------------------------------------------",
        "",
        f"- **KNOWN_RECOVERY_RATE**: {known.get('KNOWN_RECOVERY_RATE') or 'N/A — insufficient sample'}",
        f"- **UNSEEN_RECOVERY_RATE**: {_pct(known.get('UNSEEN_RECOVERY_RATE') if known.get('UNSEEN_RECOVERY_RATE') is not None else m.get('TRUE_RECOVERY_RATE'))} (all sampled beams are QA.3.0 unseen)",
        f"- {known.get('note')}",
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
            f"- `{ex.get('example_class')}`: `{ex.get('candidate_id')}` "
            f"set=`{ex.get('source_set')}` stratum=`{ex.get('stratum')}` "
            f"text=`{ex.get('annotation_text')}` det=`{ex.get('deterministic_match_status')}` "
            f"gt=`{ex.get('gt_match_status')}`"
        )
    missing = (result.get("evidence") or {}).get("missing_classes") or []
    if missing:
        md.append(f"- Missing example classes: {', '.join(missing)}")
    md += [
        "",
        "------------------------------------------------------------",
        "INDEPENDENT REVIEW (Claude Sonnet 4.6)",
        "------------------------------------------------------------",
        "",
        f"- **status**: {review.get('status') or 'PENDING_AT_REPORT_WRITE'}",
        f"- **BLOCKER**: {review.get('blocker') or 'none recorded yet'}",
        f"- **HIGH**: {review.get('high') or 'none recorded yet'}",
        f"- **MEDIUM**: {review.get('medium') or 'none recorded yet'}",
        f"- **LOW**: {review.get('low') or 'none recorded yet'}",
        "",
        "------------------------------------------------------------",
        "FIREWALL",
        "------------------------------------------------------------",
        "",
        f"- production mutation = {prod.get('production_mutation_count', 0)}",
        f"- steel / BBS / Excel unchanged: `{prod.get('fingerprints_ok')}`",
        f"- P2.6 nested regression in unit tests",
        f"- firewall ok: `{fw.get('ok')}`",
        "",
        "------------------------------------------------------------",
        "LIMITATIONS",
        "------------------------------------------------------------",
        "",
        "- This is a stratified sample, not a full drawing-set benchmark.",
        "- This is not production accuracy and not a five-set Vision KPI.",
        "- No steel recompute. No SI.1. No Vision BBS / Excel.",
        "- No R1.3 mutation. Deterministic production remains sole authority.",
        "- Primary GT match is family + diameter (P2.6-compatible). Quantity/spacing are stricter extras.",
        "- OTHER_BEAM and UNCERTAIN associations cannot become TRUE_RECOVERY.",
        "- Easy/control duplicate rate is a deployment signal, not a production metric.",
        "",
        "------------------------------------------------------------",
        "DECISION",
        "------------------------------------------------------------",
        "",
        f"- **STRENGTH**: {rec.get('strength')}",
        f"- **DECISION**: {rec.get('decision')}",
        f"- {rec.get('note')}",
        "",
        "Allowed decisions: PROCEED_TO_ENGINEERING_RECOMPUTE_PILOT | REFINE_CANDIDATE_RECOVERY | STOP_NEGATIVE.",
        "NEVER: PRODUCTION_READY.",
        "",
        "If proceeding, the next experiment is a controlled engineering recompute using a strict "
        "subset of high-confidence TRUE-like Vision candidate classes — still with no production mutation.",
        "",
    ]
    status_path = out_root / "P2.6.1_STATUS.md"
    status_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    (reports / "P2.6.1_STATUS.md").write_text(status_path.read_text(encoding="utf-8"), encoding="utf-8")
    (reports / "metrics.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
    return {
        "status": str(status_path),
        "metrics": str(reports / "metrics.json"),
    }


__all__ = ["write_reports"]
