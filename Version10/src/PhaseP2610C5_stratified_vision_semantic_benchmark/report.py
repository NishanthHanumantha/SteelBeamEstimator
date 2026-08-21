"""C.5 reports and per-beam review packages. No production writes."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from .config import ENGINEERING_CHANGES, MODEL_VERSION, PHASE_ID, PHASE_NAME, PRODUCTION_WRITE
from .length_evidence import summarize_length_vs_role


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _copy_side(src: str, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    if not src:
        return
    p = Path(src)
    if p.exists():
        shutil.copy2(p, dest_dir / "selected.png")


def write_beam_review(*, out_root: Path, rec: Dict[str, Any]) -> None:
    bid = rec.get("beam_id")
    base = Path(out_root) / "review" / str(bid)
    _copy_side(rec.get("context_selected_path"), base / "context")
    _copy_side(rec.get("detail_selected_path"), base / "detail")
    _dump(base / "vision_result.json", rec.get("vision") or {})
    _dump(
        base / "deterministic_result.json",
        {"detected_groups": rec.get("detected_groups") or [], "expected_groups": rec.get("expected_groups") or []},
    )
    _dump(base / "semantic_comparison.json", rec.get("comparison") or {})
    parsed = ((rec.get("vision") or {}).get("parsed")) or {}
    cmp = rec.get("comparison") or {}
    lines = [
        f"# Review {bid}",
        "",
        f"- Fourth Set provenance: {rec.get('set_key')}",
        f"- Context source: {rec.get('context_selected_source')} `{rec.get('context_selected_path')}`",
        f"- Detail source: {rec.get('detail_selected_source')} `{rec.get('detail_selected_path')}`",
        f"- Visual gate: {rec.get('c3_visual_gate_status')}",
        f"- Gate limitations: {rec.get('c3_gate_reasons')}",
        f"- Mixed source: {rec.get('mixed_source')}",
        f"- Why selected: {json.dumps(rec.get('selection_reason') or {}, default=str)}",
        "",
        "## Vision",
        "",
        f"- target identified: {parsed.get('target_identified')} confidence={parsed.get('association_confidence')}",
        f"- neighbour evidence: {parsed.get('neighbour_evidence_detected')}",
        f"- usable: {parsed.get('usable')} status={parsed.get('call_status')}",
        "",
    ]
    for g in parsed.get("groups") or []:
        lines.append(
            f"- {g.get('physical_group_id')} {g.get('layer')} / {g.get('spec')} / count {g.get('bar_count')} / "
            f"role {g.get('role_hypothesis')} / length {g.get('relative_length_evidence')} / span {g.get('span_relationship')}"
        )
    lines += ["", "Stirrups:", ""]
    for s in parsed.get("stirrups") or []:
        lines.append(f"- {s.get('spec')} conf={s.get('confidence')}")
    lines += ["", "## Deterministic (detected / R.1)", ""]
    for g in rec.get("detected_groups") or []:
        lines.append(
            f"- {g.get('physical_layer')} / {g.get('specification')} / count {g.get('count')} / role {g.get('reinforcement_role')}"
        )
    lines += ["", "## Automated comparison (not ground truth)", "", f"- taxonomy: {cmp.get('taxonomy')}", ""]
    for p in cmp.get("pairs") or []:
        lines += [
            "VISION:",
            f"  {p.get('layer')} / {p.get('spec')} / count {p.get('vision_count')} / role {p.get('vision_role')}",
            "DETERMINISTIC:",
            f"  {p.get('layer')} / {p.get('spec')} / count {p.get('deterministic_count')} / role {p.get('deterministic_role')}",
            "RESULT:",
            f"  LAYER {'MATCH' if p.get('layer_match') else 'DISAGREE'}",
            f"  SPEC {'MATCH' if p.get('spec_match') else 'DISAGREE'}",
            f"  PHYSICAL_GROUP {'MATCH' if p.get('physical_group_match') else 'DISAGREE'}",
            f"  ROLE {'MATCH' if p.get('role_match') else 'DISAGREE'}",
            f"  COUNT {p.get('count_comparison')}",
            "",
        ]
    for g in cmp.get("vision_only_groups") or []:
        lines.append(f"VISION ONLY: {g.get('layer')} / {g.get('spec')} / role {g.get('role')}")
    for g in cmp.get("deterministic_only_groups") or []:
        lines.append(f"DETERMINISTIC ONLY: {g.get('layer')} / {g.get('spec')} / role {g.get('role')}")
    (base / "review_summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_manual_template(*, out_root: Path, records: List[Dict[str, Any]]) -> None:
    lines = [
        "# C.5 sample manual verification template",
        "",
        "Do not pre-fill a winner. Complete after visual inspection.",
        "",
    ]
    for rec in records:
        lines += [
            f"## {rec.get('beam_id')}",
            "",
            "Manual verification:",
            "- Vision interpretation accuracy:",
            "- Deterministic interpretation accuracy:",
            "- Correct target:",
            "- Correct layers:",
            "- Correct physical groups:",
            "- Correct specifications:",
            "- Correct counts:",
            "- Correct MAIN/EXTRA:",
            "- Correct stirrups:",
            "- Notes:",
            "",
        ]
    (Path(out_root) / "sample_manual_verification_template.md").write_text("\n".join(lines), encoding="utf-8")


def write_benchmark_report(*, out_root: Path, result: Dict[str, Any]) -> None:
    metrics = result.get("metrics") or {}
    sample = result.get("sample") or {}
    records = result.get("records") or []
    fourth = result.get("fourth_set") or {}
    lines = [
        f"# {PHASE_ID} — {PHASE_NAME}",
        "",
        f"1. Gate: {result.get('gate_version')}",
        f"2. MODEL_VERSION: {MODEL_VERSION}",
        f"3. Fourth Set discovery: ok={fourth.get('ok')} set_key={fourth.get('set_key')} method={fourth.get('discovery_method')}",
        f"4. Candidate population size: {result.get('candidate_count')}",
        f"5. Selected sample size: {sample.get('size')}",
        f"6. Stratification coverage: {sample.get('strata_coverage')} uncovered={sample.get('uncovered_strata')}",
        "",
        "7. Selected beam table",
        "",
        "| beam_id | gate | context | detail | mixed | strata | taxonomy |",
        "|---|---|---|---|---|---|---|",
    ]
    for rec in records:
        lines.append(
            f"| {rec.get('beam_id')} | {rec.get('c3_visual_gate_status')} | "
            f"{rec.get('context_selected_source')} | {rec.get('detail_selected_source')} | "
            f"{rec.get('mixed_source')} | {','.join(rec.get('strata') or [])} | "
            f"{','.join((rec.get('comparison') or {}).get('taxonomy') or [])} |"
        )
    lines += ["", "8. Why each beam was selected", ""]
    for item in sample.get("why") or []:
        lines.append(f"- {item.get('beam_id')}: strata={item.get('strata')} new={item.get('new_strata')} gate={item.get('gate_status')} groups={item.get('deterministic_group_count')}")
    lines += [
        "",
        f"9. Visual gate status distribution: {metrics.get('gate_distribution')}",
        f"10. Claude call status: attempted={metrics.get('attempted')} skipped={metrics.get('skipped')}",
        f"11. API success/failure: success={metrics.get('api_success')} failed={metrics.get('api_failed')}",
        f"12. Schema validity: valid={metrics.get('schema_valid')} invalid={metrics.get('schema_invalid')} unusable={metrics.get('unusable')}",
        f"13. Target identification: match={metrics.get('target_match')} disagree={metrics.get('target_disagree')} unknown={metrics.get('target_unknown')}",
        f"14. Physical group comparison: {metrics.get('physical_groups')}",
        f"15. Layer comparison: {metrics.get('layers')}",
        f"16. Specification comparison: {metrics.get('specs')}",
        f"17. Count disagreement: {metrics.get('counts')}",
        f"18. MAIN/EXTRA disagreement: role_mismatch_pairs={metrics.get('role_mismatches')}",
        f"19. Same-spec distinct-group preservation / collapse: {metrics.get('same_spec_collapse')}",
        f"20. Stirrup comparison: {metrics.get('stirrups')}",
        f"21. Neighbour association flags: {metrics.get('neighbour_flags')}",
        f"22. Relative bar-length/span evidence: {metrics.get('length_evidence')}",
        "",
        "23. Per-beam semantic comparison",
        "",
    ]
    for rec in records:
        cmp = rec.get("comparison") or {}
        lines.append(f"- {rec.get('beam_id')}: {cmp.get('taxonomy')} target={cmp.get('target_association')} vis_n={(cmp.get('physical_group_count') or {}).get('vision')} det_n={(cmp.get('physical_group_count') or {}).get('deterministic')}")
    lines += [
        "",
        "24. Manual verification placeholders: see sample_manual_verification_template.md",
        "",
        "25. Limitations",
        "",
        "- Automated comparison is not ground truth.",
        "- VISION_DISAGREEMENT is an observation, not a Vision failure.",
        "- Role-only MAIN/EXTRA mismatch is not a complete physical-group failure.",
        "- PNG pixels are copied for review; sources are not mutated.",
        "- Fourth Set only. Sample capped at 10. Not the 121 LIMITED population.",
        "",
        "26. NO PRODUCTION INTERPRETATION CHANGE",
        "",
        f"- PRODUCTION_WRITE = {PRODUCTION_WRITE}",
        f"- ENGINEERING_CHANGES = {ENGINEERING_CHANGES}",
        "",
        "27. Recommended handoff",
        "",
        "MANUAL VERIFICATION OF THE 10-BEAM FINAL VISION BENCHMARK",
        "Do not automatically start hybrid production integration.",
        "",
        "AUTOMATED COMPARISON above is distinct from MANUAL TRUTH / USER VERIFICATION.",
        "",
    ]
    (Path(out_root) / "stratified_vision_benchmark_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_selection_report(*, out_root: Path, fourth: Dict[str, Any], sample: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
    lines = [
        "# C.5 sample selection report",
        "",
        f"- Fourth Set ok={fourth.get('ok')} count={len(fourth.get('beam_ids') or [])}",
        f"- candidate records={len(candidates)}",
        f"- selected={sample.get('selected_ids')}",
        f"- notes={sample.get('notes')}",
        f"- strata coverage={sample.get('strata_coverage')}",
        "",
        "## Why each beam was selected",
        "",
    ]
    for item in sample.get("why") or []:
        lines += [
            f"### {item.get('beam_id')}",
            "",
            f"- strata: {item.get('strata')}",
            f"- newly covered: {item.get('new_strata')}",
            f"- gate: {item.get('gate_status')}",
            f"- mixed_source: {item.get('mixed_source')}",
            f"- deterministic_group_count: {item.get('deterministic_group_count')}",
            "",
        ]
    (Path(out_root) / "sample_selection_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> None:
    out_root = Path(out_root)
    records = result.get("records") or []
    sample = result.get("sample") or {}
    _dump(out_root / "stratification_population.json", result.get("population_records") or [])
    _dump(
        out_root / "selected_sample.json",
        {
            "ids": sample.get("selected_ids"),
            "size": sample.get("size"),
            "why": sample.get("why"),
            "notes": sample.get("notes"),
            "strata_coverage": sample.get("strata_coverage"),
        },
    )
    _dump(out_root / "benchmark_manifest.json", records)
    write_selection_report(
        out_root=out_root,
        fourth=result.get("fourth_set") or {},
        sample=sample,
        candidates=result.get("population_records") or [],
    )
    write_manual_template(out_root=out_root, records=records)
    write_benchmark_report(out_root=out_root, result=result)
    for rec in records:
        write_beam_review(out_root=out_root, rec=rec)
    slim = {k: result.get(k) for k in ("phase_id", "phase_name", "model_version", "gate_version", "decision", "pass_fail", "metrics", "production", "fingerprints", "unit_tests", "live_claude_call", "handoff")}
    if isinstance(slim.get("unit_tests"), dict):
        slim["unit_tests"] = {k: slim["unit_tests"].get(k) for k in ("success", "passed", "total")}
    _dump(out_root / "P2.6.10-C.5_RESULTS.json", slim)
    _dump(out_root / "run_metadata.json", result.get("run_metadata") or {})


__all__ = ["summarize_length_vs_role", "write_reports"]
