"""P2.6.10-C.1+C.2 reports. Shadow evidence consolidation — not production routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _ok(info: Any) -> str:
    if isinstance(info, dict):
        return "PASS" if info.get("ok") else "FAIL"
    return str(info)


def write_selection_report(*, out_root: Path, result: Dict[str, Any]) -> str:
    out_root = Path(out_root)
    summary = result.get("selection_summary") or {}
    anti = result.get("anti_hardcoding") or {}
    tests = result.get("unit_tests") or {}
    prod = result.get("production") or {}
    perf = result.get("performance") or {}
    thresh = result.get("thresholds") or {}
    replacements = result.get("b1_replacements") or []
    unresolved = result.get("unresolved_beams") or []
    cohorts = result.get("known_reporting_cohorts") or {}
    lines: List[str] = [
        f"# {result.get('phase_id')} — {result.get('phase_name')}",
        "",
        "Shadow / read-only evidence inventory and preference-preserving candidate selection.",
        "No DXF rerender. No recovery. No Claude Vision. No production mutation.",
        "",
        f"**STATUS:** {result.get('pass_fail')}",
        f"**DECISION:** {result.get('decision')}",
        f"**Model:** {result.get('model_version')}  **Gate:** {result.get('gate_version')}",
        "",
        "## Phase purpose",
        "",
        "Consolidate existing B.1 / B.2 / B.3 render candidates and select the best available",
        "context and detail independently. Latest candidate is not automatically best.",
        "",
        "## Source phase hierarchy",
        "",
        "1. B.1 is the preferred baseline and is retained by default.",
        "2. B.2 / B.3 may replace B.1 only with explicit critical-failure clearance or material improvement.",
        "3. Ambiguous evidence retains B.1.",
        "4. Context and detail are selected independently (mixed source is expected).",
        "",
        "## Inventory population",
        "",
        f"- unique beams: {summary.get('total_unique_beams')}",
        f"- B.1 context available: {summary.get('beams_with_b1_context')}",
        f"- B.1 detail available: {summary.get('beams_with_b1_detail')}",
        f"- beams with B.2 candidates: {summary.get('beams_with_b2_candidates')}",
        f"- beams with B.3 candidates: {summary.get('beams_with_b3_candidates')}",
        "",
        "## Selection policy / thresholds",
        "",
        f"- MATERIAL_SCORE_MARGIN: {thresh.get('MATERIAL_SCORE_MARGIN')}",
        f"- MIN_FOREGROUND_GAIN: {thresh.get('MIN_FOREGROUND_GAIN')}",
        f"- MAX_COVERAGE_REGRESSION: {thresh.get('MAX_COVERAGE_REGRESSION')}",
        f"- CRITICAL_STATUSES: {', '.join(thresh.get('CRITICAL_STATUSES') or [])}",
        "",
        "CLIP / BORDER_CLIPPING_SUSPECT is not a critical failure.",
        "",
        "## Aggregate selection results",
        "",
        f"- context selected B.1 / B.2 / B.3 / unresolved: "
        f"{summary.get('context_selected_b1')} / {summary.get('context_selected_b2')} / "
        f"{summary.get('context_selected_b3')} / {summary.get('context_unresolved_missing')}",
        f"- detail selected B.1 / B.2 / B.3 / unresolved: "
        f"{summary.get('detail_selected_b1')} / {summary.get('detail_selected_b2')} / "
        f"{summary.get('detail_selected_b3')} / {summary.get('detail_unresolved_missing')}",
        f"- mixed-source selections: {summary.get('mixed_source_selections')}",
        f"- B.1 retained by preference: {summary.get('b1_retained_by_preference')}",
        f"- B.1 replaced due to critical failure: {summary.get('b1_replaced_critical_failure')}",
        f"- B.1 replaced due to material improvement: {summary.get('b1_replaced_material_improvement')}",
        f"- ambiguous / no-replacement: {summary.get('ambiguous_no_replacement')}",
        "",
        "## Replacements of B.1",
        "",
    ]
    if not replacements:
        lines.append("None. B.1 was retained for every render type that had a valid preferred baseline.")
        lines.append("")
    else:
        for rec in replacements:
            lines.append(
                f"- {rec.get('beam_id')} {rec.get('render_type')}: {rec.get('baseline')} → {rec.get('challenger')} "
                f"reasons={rec.get('reason_codes')} status={rec.get('selection_status')}"
            )
        lines.append("")
    lines += ["## Known reporting cohorts", ""]
    for group, rows in cohorts.items():
        lines.append(f"### {group}")
        for rec in rows or []:
            lines.append(
                f"- {rec.get('beam_id')}: ctx {rec.get('b1_context_status')}/{rec.get('b2_context_status')}/{rec.get('b3_context_status')} "
                f"→ {rec.get('selected_context_source')} ({rec.get('context_decision')}); "
                f"det {rec.get('b1_detail_status')}/{rec.get('b2_detail_status')}/{rec.get('b3_detail_status')} "
                f"→ {rec.get('selected_detail_source')} ({rec.get('detail_decision')}); "
                f"unresolved={rec.get('unresolved')}"
            )
        lines.append("")
    lines += [
        "## Unresolved cases",
        "",
        f"- count: {len(unresolved)}",
    ]
    for rec in unresolved[:40]:
        lines.append(f"- {rec.get('beam_id')} {rec.get('render_type')}: {rec.get('selection_status')} {rec.get('reason_codes')}")
    if len(unresolved) > 40:
        lines.append(f"- ... {len(unresolved) - 40} more")
    lines += [
        "",
        "## Runtime profile",
        "",
        f"- total_s: {perf.get('total_runtime_s')}",
        f"- inventory_discovery_s: {perf.get('inventory_discovery_s')}",
        f"- file_inspection_hashing_s: {perf.get('file_inspection_hashing_s')}",
        f"- evidence_loading_s: {perf.get('evidence_loading_s')}",
        f"- selection_s: {perf.get('selection_s')}",
        f"- report_generation_s: {perf.get('report_generation_s')}",
        "",
        "## Anti-hardcoding / tests / production",
        "",
        f"- anti-hardcoding: {_ok(anti)}",
        f"- unit tests: {tests.get('passed')}/{tests.get('total')} success={tests.get('success')}",
        f"- fingerprints unchanged: {(result.get('fingerprints') or {}).get('unchanged')}",
        f"- production mutation count: {prod.get('production_mutation_count')}",
        f"- live Claude Vision: {prod.get('live_vision_invoked')}",
        "",
        "## Limitations",
        "",
        "This phase does not repair blank, crushed, or long-horizontal renders.",
        "It only inventories existing candidates and selects among them.",
        "B69A is not a unique discovered beam ID; repository truth is B69.",
        "",
        "## Explicit next-phase handoff",
        "",
        "READY_FOR_P2.6.10-C.3 Visual Completeness Gate + Claude Vision Shadow Benchmark",
        "Consume `selection_manifest.json` (`selected_path`, provenance, SHA-256, evidence, reasoning).",
        "Do not reimplement B.1/B.2/B.3 selection in C.3.",
        "",
        f"**{result.get('decision')}**",
        "",
        "LIVE_CLAUDE_VISION = NOT_CALLED",
        "This phase does not authorize Claude Vision or production promotion.",
        "",
    ]
    path = out_root / "selection_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    _dump(out_root / "evidence_inventory.json", result.get("evidence_inventory") or [])
    _dump(out_root / "selection_manifest.json", result.get("selection_manifest") or [])
    _dump(out_root / "selection_summary.json", result.get("selection_summary") or {})
    _dump(out_root / "candidate_decisions.json", result.get("candidate_decisions") or [])
    _dump(out_root / "rejection_report.json", result.get("rejection_report") or [])
    _dump(out_root / "validation_summary.json", result.get("validation_summary") or {})
    _dump(out_root / "performance_profile.json", result.get("performance") or {})
    _dump(out_root / "anti_hardcoding_results.json", result.get("anti_hardcoding") or {})
    _dump(out_root / "known_reporting_cohorts.json", result.get("known_reporting_cohorts") or {})
    report = write_selection_report(out_root=out_root, result=result)
    slim_keys = {
        "phase_id",
        "phase_name",
        "model_version",
        "gate_version",
        "pass_fail",
        "decision",
        "recommendation",
        "selection_summary",
        "validation_summary",
        "performance",
        "anti_hardcoding",
        "unit_tests",
        "production",
        "fingerprints",
        "b1_replacements",
        "unresolved_beams",
        "handoff",
        "thresholds",
        "live_claude_vision",
    }
    slim = {k: result.get(k) for k in slim_keys}
    slim["unit_tests"] = {
        "success": (result.get("unit_tests") or {}).get("success"),
        "passed": (result.get("unit_tests") or {}).get("passed"),
        "total": (result.get("unit_tests") or {}).get("total"),
    }
    _dump(out_root / "P2.6.10-C.1C2_RESULTS.json", slim)
    return {"report": report}


__all__ = ["write_reports"]
