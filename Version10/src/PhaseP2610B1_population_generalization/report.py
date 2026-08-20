"""P2.6.10-B.1 reports. Shadow validation — not production routing."""
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
    lines = [
        f"# {result.get('phase_id')} — {result.get('phase_name')}",
        "",
        "Shadow / validation only. Fourth drawing set only. No Claude Vision.",
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
        f"- title hits: {pop.get('title_hits')}",
        f"- unique discovered beams: {pop.get('unique_beam_ids')}",
        f"- collapsed duplicate titles: {len(pop.get('collapsed_duplicates') or [])}",
        f"- context crops: {summary.get('context_crop_success_count')}",
        f"- detail crops: {summary.get('detail_crop_success_count')}",
        f"- fully complete: {summary.get('fully_complete_count')}",
        f"- incomplete: {summary.get('incomplete_count')}",
        f"- skipped: {summary.get('skip_count')}",
        f"- render failures: {summary.get('render_failure_count')}",
        f"- completeness rate: {summary.get('completeness_rate')}",
        "",
        "## Failures",
        "",
    ]
    if not fails:
        lines.append("NONE")
    else:
        for f in fails:
            lines.append(
                f"- {f.get('beam_id')}: {', '.join(f.get('failure_categories') or [])}"
            )
    lines += [
        "",
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
        lines.append(f"- {rec.get('set_key')}/{rec.get('beam_id')}: complete={rec.get('complete')}")
    lines += [
        "",
        "## Prior regressions",
        "",
        f"- P2.6.6: {_ok(prior.get('p266'))}",
        f"- P2.6.10-A: {_ok(prior.get('p2610a'))}",
        f"- P2.6.10-B: {_ok(prior.get('p2610b'))}",
        f"- P2.6.10-B.1 unit tests: {tests.get('passed')}/{tests.get('total')} success={tests.get('success')}",
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
    _dump(out_root / "population_manifest.json", result.get("population_manifest") or {})
    anti_dir = out_root / "anti_hardcoding"
    anti_dir.mkdir(parents=True, exist_ok=True)
    _dump(anti_dir / "source_guard_report.json", anti.get("source_guard") or {})
    _dump(anti_dir / "metamorphic_results.json", anti)
    slim = {k: v for k, v in result.items() if k not in ("records", "population_manifest")}
    _dump(out_root / "P2.6.10-B.1_RESULTS.json", slim)
    return {
        "report": str(status_path),
        "summary": str(out_root / "validation_summary.json"),
        "manifest": str(out_root / "population_manifest.json"),
        "anti": str(anti_dir / "metamorphic_results.json"),
    }


__all__ = ["write_reports"]
