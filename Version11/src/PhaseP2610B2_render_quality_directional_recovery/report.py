"""P2.6.10-B.2 reports. Shadow validation — not production routing."""
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
    fails = result.get("failures") or []
    six = result.get("six_beam_regression") or {}
    prior = result.get("prior_regression") or {}
    known = result.get("known_visual_cases") or {}
    lines = [
        f"# {result.get('phase_id')} — {result.get('phase_name')}",
        "",
        "Shadow / validation only. Fourth drawing set only. No Claude Vision.",
        "Context is validated before Detail. PNG generated is not treated as Vision-usable.",
        "",
        f"**Phase:** {result.get('phase_id')}",
        f"**Model version:** {result.get('model_version')}",
        f"**Gate version:** {result.get('gate_version')}",
        f"**STATUS:** {result.get('pass_fail')}",
        f"**DECISION:** {result.get('decision')}",
        "",
        "## Population",
        "",
        f"- source DXF: `{pop.get('source_dxf')}`",
        f"- discovered unique beams: {summary.get('discovered_beam_count')}",
        f"- initial context generated: {summary.get('initial_context_generated_count')}",
        f"- context valid before recovery: {summary.get('context_valid_before_recovery_count')}",
        f"- context valid after recovery: {summary.get('final_context_valid_count')}",
        f"- initial detail generated: {summary.get('initial_detail_generated_count')}",
        f"- detail valid after recovery: {summary.get('final_detail_valid_count')}",
        f"- empty renders: {summary.get('empty_render_count')}",
        f"- black renders: {summary.get('black_render_count')}",
        f"- low-information renders: {summary.get('low_information_render_count')}",
        f"- horizontal clipping suspects: {summary.get('horizontal_clipping_suspect_count')}",
        f"- vertical clipping suspects: {summary.get('vertical_clipping_suspect_count')}",
        f"- context recovery attempts / successes: {summary.get('context_recovery_attempt_count')} / {summary.get('context_recovery_success_count')}",
        f"- detail recovery attempts / successes: {summary.get('detail_recovery_attempt_count')} / {summary.get('detail_recovery_success_count')}",
        f"- unresolved context / detail: {summary.get('unresolved_context_failure_count')} / {summary.get('unresolved_detail_failure_count')}",
        f"- final vision-usable: {summary.get('final_vision_usable_count')} / {summary.get('discovered_beam_count')} ({summary.get('final_vision_usable_rate')})",
        f"- skipped / true render failures: {summary.get('skipped_count')} / {summary.get('true_render_failure_count')}",
        "",
        "## Context / detail / population metrics",
        "",
        f"- context: {json.dumps(summary.get('context_metrics') or {})}",
        f"- detail: {json.dumps(summary.get('detail_metrics') or {})}",
        f"- population: {json.dumps(summary.get('population_metrics') or {})}",
        "",
        "## SAFE_STOP_RECORD (pre-optimization)",
        "",
        "Pre-optimization partial run is preserved under `pre_optimization_partial/`.",
        "It is **not** final population validation evidence.",
        "",
        "## PRE_VS_POST_OPTIMIZATION_COMPARISON",
        "",
        f"- pre-optimization partial rate: {(result.get('performance') or {}).get('pre_optimization_partial_rate_s_per_beam')} s/beam (8 beams)",
        f"- post-optimization total runtime: {(result.get('performance') or {}).get('total_runtime_s')} s",
        f"- post-optimization avg: {(result.get('performance') or {}).get('avg_seconds_per_beam')} s/beam",
        f"- context screening: {(result.get('performance') or {}).get('context_screening_runtime_s')} s",
        f"- detail runtime: {(result.get('performance') or {}).get('detail_runtime_s')} s",
        f"- recovery runtime: {(result.get('performance') or {}).get('recovery_runtime_s')} s",
        f"- diagnostic I/O: {(result.get('performance') or {}).get('diagnostic_output_runtime_s')} s",
        f"- cache hits/misses: {(result.get('performance') or {}).get('render_cache_hits')} / {(result.get('performance') or {}).get('render_cache_misses')}",
        f"- parallelism: enabled={(result.get('performance') or {}).get('parallelism_enabled')} workers={(result.get('performance') or {}).get('worker_count')} renderer_parallel_safe={(result.get('performance') or {}).get('renderer_parallel_safe')}",
        "",
        "## Failures",
        "",
    ]
    if not fails:
        lines.append("NONE")
    else:
        for f in fails:
            lines.append(
                f"- {f.get('beam_id')} [{f.get('stage')}]: {f.get('primary_status')} "
                f"flags={', '.join(f.get('failure_flags') or [])} usable={f.get('final_vision_usable')}"
            )
    lines += ["", "## Known visual cases", ""]
    for group, rows in known.items():
        lines.append(f"### {group}")
        for rec in rows or []:
            lines.append(
                f"- {rec.get('beam_id')}: ctx={rec.get('context_status')} det={rec.get('detail_status')} "
                f"usable={rec.get('final_vision_usable')} orient={rec.get('dominant_orientation')} "
                f"ctx_attempts={rec.get('context_recovery_attempt_count')}"
            )
        lines.append("")
    lines += [
        "## Anti-hardcoding",
        "",
        f"- source guard: {_ok(anti.get('source_guard'))}",
        f"- translation invariance: {_ok((anti.get('translation_invariance') or {}).get('synthetic'))}",
        f"- DXF-copy translation: {_ok((anti.get('translation_invariance') or {}).get('dxf_copy'))}",
        f"- spatial-distance robustness: {_ok(anti.get('spatial_distance'))}",
        f"- packed-sheet robustness: {_ok(anti.get('packed_sheet'))}",
        "",
        "## Original six-beam regression",
        "",
    ]
    for rec in six.get("records") or []:
        lines.append(
            f"- {rec.get('set_key')}/{rec.get('beam_id')}: complete={rec.get('complete')} "
            f"b2_usable={rec.get('final_vision_usable')}"
        )
    lines += [
        "",
        "## Prior regressions",
        "",
        f"- P2.6.6: {_ok(prior.get('p266'))}",
        f"- P2.6.10-A: {_ok(prior.get('p2610a'))}",
        f"- P2.6.10-B: {_ok(prior.get('p2610b'))}",
        f"- P2.6.10-B.1: {_ok(prior.get('p2610b1'))}",
        f"- P2.6.10-B.2 unit tests: {tests.get('passed')}/{tests.get('total')} success={tests.get('success')}",
        "",
        "## Production firewall",
        "",
        f"- production mutation count: {prod.get('production_mutation_count')}",
        f"- steel quantity delta: {prod.get('steel_quantity_delta')}",
        f"- BBS delta: {prod.get('bbs_delta')}",
        f"- workbook delta: {prod.get('workbook_delta')}",
        f"- live Claude Vision calls: {prod.get('live_vision_invoked')}",
        "",
        "## Final decision",
        "",
        f"**{result.get('decision')}**",
        "",
        "This phase does not authorize Claude Vision or production promotion.",
        "",
    ]
    status_path = out_root / "validation_report.md"
    status_path.write_text("\n".join(lines), encoding="utf-8")
    _dump(out_root / "validation_summary.json", summary)
    _dump(out_root / "failures.json", fails)
    _dump(out_root / "recovery_diagnostics.json", result.get("recovery_diagnostics") or [])
    _dump(out_root / "beam_diagnostics.json", result.get("beam_diagnostics") or [])
    anti_dir = out_root / "anti_hardcoding"
    anti_dir.mkdir(parents=True, exist_ok=True)
    _dump(anti_dir / "source_guard_report.json", anti.get("source_guard") or {})
    _dump(anti_dir / "metamorphic_results.json", anti)
    slim = {k: v for k, v in result.items() if k not in ("records", "beam_diagnostics")}
    _dump(out_root / "P2.6.10-B.2_RESULTS.json", slim)
    _dump(out_root / "performance_profile.json", result.get("performance") or {})
    _dump(out_root / "recovery_summary.json", result.get("recovery_diagnostics") or [])
    _dump(anti_dir / "anti_hardcoding_results.json", anti)
    _dump(out_root / "anti_hardcoding_results.json", anti)
    return {
        "report": str(status_path),
        "summary": str(out_root / "validation_summary.json"),
        "anti": str(anti_dir / "metamorphic_results.json"),
    }


__all__ = ["write_reports"]
