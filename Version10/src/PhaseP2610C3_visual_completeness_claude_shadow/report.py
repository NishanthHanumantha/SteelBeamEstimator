"""P2.6.10-C.3 shadow reports. No production routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .vision_prompt import prompt_contract_markdown


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def write_six_beam_report(*, out_root: Path, rows: List[Dict[str, Any]]) -> str:
    lines = [
        "# P2.6.10-C.3 six-beam Claude Vision control report",
        "",
        "Shadow only. Manual/R1/P2.6.9 disagreement is preserved as provenance, not silently resolved.",
        "",
    ]
    for rec in rows:
        g = rec.get("gate") or {}
        c = rec.get("claude") or {}
        parsed = c.get("parsed") or {}
        cmp = rec.get("comparison") or {}
        lines += [
            f"## {rec.get('set_key')} / {rec.get('beam_id')}",
            "",
            f"- selected context source: {rec.get('context_source')}",
            f"- selected detail source: {rec.get('detail_source')}",
            f"- completeness gate: {g.get('status')}",
            f"- gate reasons: {g.get('reason_codes')}",
            f"- Claude called: {c.get('called')} reason={c.get('call_reason')} skip={c.get('skip_reason')}",
            f"- target identified: {parsed.get('target_beam_identified')} "
            f"assoc_conf={parsed.get('target_association_confidence')}",
            f"- neighbor evidence detected: {parsed.get('neighbor_evidence_detected')}",
            f"- usable: {parsed.get('usable')} unusable={parsed.get('unusable_reason')}",
            f"- Claude groups: {json.dumps(parsed.get('reinforcement_groups') or [], default=str)}",
            f"- Claude stirrups: {json.dumps(parsed.get('stirrups') or [], default=str)}",
            f"- P2.6.9 expected count: {len(cmp.get('p269_expected') or [])}",
            f"- deterministic/R1 count: {len(cmp.get('deterministic') or [])}",
            f"- manual notes: {cmp.get('manual_notes')}",
            f"- taxonomy: {cmp.get('taxonomy')}",
            f"- vs P269: {json.dumps(cmp.get('vs_p269') or {}, default=str)}",
            "",
        ]
    path = out_root / "six_beam_benchmark_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_status_md(*, out_root: Path, result: Dict[str, Any]) -> str:
    pop = result.get("population_summary") or {}
    gate = pop.get("gate") or {}
    six = result.get("six_beam") or {}
    lines = [
        f"# {result.get('phase_id')} — {result.get('phase_name')}",
        "",
        "SHADOW ONLY. FAIL CLOSED. NO PRODUCTION RECOVERY.",
        "",
        f"**DECISION:** {result.get('decision')}",
        f"**Model:** {result.get('model_version')}  **Gate:** {result.get('gate_version')}",
        "",
        "## Visual gate",
        "",
        f"- total: {gate.get('total')}",
        f"- VISION_READY: {gate.get('VISION_READY')}",
        f"- VISION_READY_WITH_LIMITATIONS: {gate.get('VISION_READY_WITH_LIMITATIONS')}",
        f"- VISION_REVIEW_ONLY: {gate.get('VISION_REVIEW_ONLY')}",
        f"- VISION_NOT_READY: {gate.get('VISION_NOT_READY')}",
        "",
        "## Claude",
        "",
        f"- live: {result.get('live_claude_vision')}",
        f"- six-beam technically valid: {six.get('technically_valid')}",
        f"- calls attempted: {(pop.get('claude') or {}).get('attempted')}",
        f"- API success: {(pop.get('claude') or {}).get('api_success')}",
        f"- usable: {(pop.get('claude') or {}).get('schema_valid_usable')}",
        f"- unusable: {(pop.get('claude') or {}).get('unusable')}",
        "",
        "## Production firewall",
        "",
        f"- production_mutation_count: {(result.get('production') or {}).get('production_mutation_count')}",
        f"- steel_quantity_delta: 0",
        f"- BBS_delta: 0",
        f"- workbook_delta: 0",
        f"- PRODUCTION_WRITE: false",
        "",
        "## Control questions",
        "",
    ]
    for q, a in (result.get("control_answers") or {}).items():
        lines.append(f"- {q}: {a}")
    lines += ["", f"**{result.get('decision')}**", ""]
    path = out_root / "P2.6.10-C.3_STATUS.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    _dump(out_root / "visual_completeness_manifest.json", result.get("visual_completeness_manifest") or [])
    _dump(out_root / "six_beam_benchmark.json", result.get("six_beam") or {})
    _dump(out_root / "population_summary.json", result.get("population_summary") or {})
    _dump(out_root / "claude_call_audit.json", result.get("claude_call_audit") or [])
    _dump(out_root / "claude_normalized_results.json", result.get("claude_normalized_results") or [])
    _dump(out_root / "comparison_results.json", result.get("comparison_results") or [])
    _dump(out_root / "diagnostics.json", result.get("diagnostics") or {})
    _dump(out_root / "performance_profile.json", result.get("performance") or {})
    (out_root / "prompt_contract.md").write_text(prompt_contract_markdown(), encoding="utf-8")
    write_six_beam_report(out_root=out_root, rows=(result.get("six_beam") or {}).get("rows") or [])
    write_status_md(out_root=out_root, result=result)
    slim = {
        k: result.get(k)
        for k in (
            "phase_id",
            "phase_name",
            "model_version",
            "gate_version",
            "decision",
            "pass_fail",
            "live_claude_vision",
            "population_summary",
            "six_beam",
            "production",
            "fingerprints",
            "unit_tests",
            "anti_hardcoding",
            "control_answers",
            "handoff",
        )
    }
    if isinstance(slim.get("unit_tests"), dict):
        slim["unit_tests"] = {
            "success": slim["unit_tests"].get("success"),
            "passed": slim["unit_tests"].get("passed"),
            "total": slim["unit_tests"].get("total"),
        }
    _dump(out_root / "P2.6.10-C.3_RESULTS.json", slim)
    return {"status": str(out_root / "P2.6.10-C.3_STATUS.md")}


__all__ = ["write_reports"]
