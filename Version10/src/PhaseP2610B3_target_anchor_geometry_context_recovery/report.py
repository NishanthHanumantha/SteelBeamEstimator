"""P2.6.10-B.3 reports. Shadow validation — not production routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _ok(info: Any) -> str:
    if isinstance(info, dict):
        return "PASS" if info.get("ok") else "FAIL"
    return str(info)


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    pop = result.get("population") or {}
    summary = result.get("validation_summary") or {}
    anti = result.get("anti_hardcoding") or {}
    tests = result.get("unit_tests") or {}
    prod = result.get("production") or {}
    perf = result.get("performance") or {}
    known = result.get("known_visual_cases") or {}
    lines = [
        f"# {result.get('phase_id')} — {result.get('phase_name')}",
        "",
        "Shadow / validation only. Overlay recovery. Known-good B.1 renders are frozen.",
        "No Claude Vision. No production mutation.",
        "",
        f"**STATUS:** {result.get('pass_fail')}",
        f"**DECISION:** {result.get('decision')}",
        f"**Model:** {result.get('model_version')}  **Gate:** {result.get('gate_version')}",
        "",
        "## Population",
        "",
        f"- unique beams: {pop.get('unique_beam_ids')}",
        f"- frozen-good: {summary.get('frozen_good_count')}",
        f"- target-recovery: {summary.get('target_recovery_count')}",
        f"- review-only: {summary.get('review_only_count')}",
        f"- known-good regression: {summary.get('known_good_regression_count')}",
        f"- B.1 reused / B.2 retained / B.3 improved / fallback: "
        f"{summary.get('b1_reused_count')} / {summary.get('b2_retained_count')} / "
        f"{summary.get('b3_improved_count')} / {summary.get('fallback_count')}",
        "",
        "## Performance",
        "",
        f"- total runtime s: {perf.get('total_runtime_s')}",
        f"- targeted beams: {perf.get('targeted_beam_count')}",
        f"- avg recovery s/targeted: {perf.get('avg_recovery_s_per_targeted')}",
        f"- parallelism: {perf.get('parallelism_enabled')} workers={perf.get('worker_count')}",
        "",
        "## Known visual cases",
        "",
    ]
    for group, rows in known.items():
        lines.append(f"### {group}")
        for rec in rows or []:
            lines.append(
                f"- {rec.get('beam_id')}: class={rec.get('baseline_classification')} "
                f"action={rec.get('b3_action')} ctx={rec.get('final_context_status')} "
                f"src={rec.get('selected_context_source')}"
            )
        lines.append("")
    lines += [
        "## Anti-hardcoding / regression / production",
        "",
        f"- anti-hardcoding: {_ok(anti)}",
        f"- unit tests: {tests.get('passed')}/{tests.get('total')} success={tests.get('success')}",
        f"- production mutation count: {prod.get('production_mutation_count')}",
        f"- live Claude Vision: {prod.get('live_vision_invoked')}",
        "",
        "## Recommendation",
        "",
        f"{result.get('recommendation')}",
        "",
        f"**{result.get('decision')}**",
        "",
        "This phase does not authorize Claude Vision or production promotion.",
        "",
    ]
    (out_root / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")
    _dump(out_root / "validation_summary.json", summary)
    _dump(out_root / "failure_report.json", result.get("failures") or [])
    _dump(out_root / "beam_selection_manifest.json", result.get("beam_selection_manifest") or [])
    _dump(out_root / "target_anchor_manifest.json", result.get("target_anchor_manifest") or [])
    _dump(out_root / "context_recovery_summary.json", result.get("context_recovery_summary") or {})
    _dump(out_root / "candidate_evaluation.json", result.get("candidate_evaluations") or [])
    _dump(out_root / "baseline_preservation_report.json", result.get("baseline_preservation") or {})
    _dump(out_root / "known_good_regression_report.json", result.get("known_good_regression") or {})
    _dump(out_root / "performance_profile.json", perf)
    _dump(out_root / "anti_hardcoding_results.json", anti)
    slim = {k: v for k, v in result.items() if k not in ("records", "beam_diagnostics")}
    _dump(out_root / "P2.6.10-B.3_RESULTS.json", slim)
    return {"report": str(out_root / "validation_report.md")}


__all__ = ["write_reports"]
