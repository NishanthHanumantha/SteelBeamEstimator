"""P2.6.10-C.4 read-only reports. No production routing."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from .config import (
    ENGINEERING_CHANGES,
    LIVE_CLAUDE_CALL,
    MODEL_VERSION,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_WRITE,
)


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def write_review_tree(*, out_root: Path, records: List[Dict[str, Any]]) -> None:
    for rec in records:
        bid = rec.get("beam_id")
        base = Path(out_root) / "review" / str(bid)
        _dump(base / "evidence_summary.json", rec.get("evidence_inventory") or [])
        _dump(base / "deterministic" / "interpretation.json", rec.get("deterministic_interpretation") or [])
        _dump(base / "p269" / "interpretation.json", rec.get("p269_interpretation") or [])
        _dump(base / "vision" / "interpretation.json", rec.get("vision_interpretation") or [])
        _dump(base / "reconciled" / "truth.json", rec.get("reconciled_groups") or [])
        _dump(
            base / "source_provenance.json",
            {
                "beam_id": bid,
                "context_provenance": rec.get("context_provenance"),
                "detail_provenance": rec.get("detail_provenance"),
                "note": "Source PNGs are referenced, not copied or mutated.",
            },
        )


def write_calibration_report(*, out_root: Path, result: Dict[str, Any]) -> None:
    metrics = result.get("calibration_metrics") or {}
    records = result.get("records") or []
    anchors = [
        r
        for r in records
        if str(r.get("truth_source_summary") or "").upper().startswith("MANUAL")
    ]
    lines = [
        f"# {PHASE_ID} — {PHASE_NAME}",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        "Shadow / benchmark calibration only. Predecessor artefacts are evidence, not automatic ground truth.",
        "",
        "## Population",
        "",
        f"- discovered control beams: {metrics.get('control_beam_count')}",
        f"- source: existing C.3 six-beam artefact",
        "",
        "## Evidence availability",
        "",
        f"- LIVE_CLAUDE_CALL = {LIVE_CLAUDE_CALL}",
        f"- PRODUCTION_WRITE = {PRODUCTION_WRITE}",
        f"- ENGINEERING_CHANGES = {ENGINEERING_CHANGES}",
        "",
        "## Beam-level reconciliation",
        "",
        f"- beams_reconciled: {metrics.get('beams_reconciled')}",
        f"- VISION_CONFIRMED: {metrics.get('beams_vision_confirmed')}",
        f"- DETERMINISTIC_CONFIRMED: {metrics.get('beams_deterministic_confirmed')}",
        f"- BOTH_EQUIVALENT: {metrics.get('beams_both_equivalent')}",
        f"- AMBIGUOUS_EVIDENCE: {metrics.get('beams_ambiguous')}",
        f"- INSUFFICIENT_EVIDENCE: {metrics.get('beams_insufficient_evidence')}",
        "",
        "| beam_id | status | strength | vision_result | deterministic_result | truth_source |",
        "|---|---|---|---|---|---|",
    ]
    for rec in records:
        lines.append(
            f"| {rec.get('beam_id')} | {rec.get('reconciliation_status')} | "
            f"{rec.get('evidence_strength')} | {rec.get('vision_result')} | "
            f"{rec.get('deterministic_result')} | {rec.get('truth_source_summary')} |"
        )
    lines += [
        "",
        "## Group-level comparison against reconciled truth",
        "",
        "Unresolved groups are excluded from forced correctness claims.",
        "",
        f"- reconciled_expected_group_count: {metrics.get('reconciled_expected_group_count')}",
        f"- vision_correct / missing / spurious: "
        f"{metrics.get('vision_correct_group_count')} / "
        f"{metrics.get('vision_missing_group_count')} / "
        f"{metrics.get('vision_spurious_group_count')}",
        f"- deterministic_correct / missing / spurious: "
        f"{metrics.get('deterministic_correct_group_count')} / "
        f"{metrics.get('deterministic_missing_group_count')} / "
        f"{metrics.get('deterministic_spurious_group_count')}",
        "",
        "## Explicit verification anchors",
        "",
    ]
    if not anchors:
        lines.append("No explicit MANUAL_VERIFICATION rows were consumed.")
    for rec in anchors:
        lines += [
            f"### {rec.get('beam_id')}",
            "",
            f"- reconciliation_status: {rec.get('reconciliation_status')}",
            f"- reconciled_groups: {json.dumps(rec.get('reconciled_groups') or [], default=str)}",
            f"- vision_interpretation: {json.dumps(rec.get('vision_interpretation') or [], default=str)}",
            f"- deterministic_interpretation: {json.dumps(rec.get('deterministic_interpretation') or [], default=str)}",
            f"- outcome reached by generic engine from supplied evidence (no beam-ID branch).",
            "",
        ]
    lines += [
        "## Unresolved cases",
        "",
        "Beams without independent verification remain AMBIGUOUS_EVIDENCE or INSUFFICIENT_EVIDENCE.",
        "A C.3 VISION_DISAGREEMENT is an observation, not a Vision error and not a deterministic error.",
        "",
        "## Limitations",
        "",
        "- Visual PNG pixels are not programmatically read as group truth.",
        "- Phase-sketch free-text notes are not parsed into groups.",
        "- Only explicitly supplied MANUAL_VERIFICATION can independently confirm one interpretation.",
        "- This phase did not call Claude and did not rerender DXF.",
        "",
        "## Decision and recommendation",
        "",
        f"- decision: {metrics.get('decision')}",
        f"- recommendation: {metrics.get('recommendation')}",
        f"- {metrics.get('recommendation_text')}",
        "",
        "If expansion is later approved, use a stratified sample covering, where available:",
        "normal/high-quality renders; clipped/limited renders; neighbouring-beam interference;",
        "same-spec distinct physical groups; MAIN/EXTRA separation; multi-group beams;",
        "stirrup interpretation; blank/crushed reporting cohort; long-horizontal reporting cohort.",
        "Do not automatically send the full LIMITED population.",
        "",
        "## Safety",
        "",
        f"- LIVE_CLAUDE_CALL = {LIVE_CLAUDE_CALL}",
        f"- PRODUCTION_WRITE = {PRODUCTION_WRITE}",
        f"- ENGINEERING_CHANGES = {ENGINEERING_CHANGES}",
        "",
    ]
    path = Path(out_root) / "benchmark_calibration_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")


def write_status_md(*, out_root: Path, result: Dict[str, Any]) -> None:
    metrics = result.get("calibration_metrics") or {}
    qa = result.get("handoff_answers") or {}
    text = "\n".join(
        [
            f"# {PHASE_ID} STATUS",
            "",
            f"- decision: {result.get('decision')}",
            f"- pass_fail: {result.get('pass_fail')}",
            f"- LIVE_CLAUDE_CALL: {LIVE_CLAUDE_CALL}",
            f"- PRODUCTION_WRITE: {PRODUCTION_WRITE}",
            f"- ENGINEERING_CHANGES: {ENGINEERING_CHANGES}",
            f"- production_mutation_count: {(result.get('production') or {}).get('production_mutation_count')}",
            "",
            "## Handoff",
            "",
            *[f"- {k}: {v}" for k, v in qa.items()],
            "",
            f"- recommendation: {metrics.get('recommendation')}",
            "",
        ]
    )
    (Path(out_root) / "P2.6.10-C.4_STATUS.md").write_text(text, encoding="utf-8")


def write_reports(*, out_root: Path, result: Dict[str, Any], package_dir: Path) -> None:
    out_root = Path(out_root)
    records = result.get("records") or []
    _dump(out_root / "reconciliation_manifest.json", records)
    _dump(
        out_root / "reconciled_truth.json",
        {
            "schema": "P2610C4_RECONCILED_TRUTH_V1",
            "note": "New non-destructive truth layer. Does not overwrite P2.6.9, R.1, or C.3 artefacts.",
            "beams": [
                {
                    "beam_id": r.get("beam_id"),
                    "reconciliation_status": r.get("reconciliation_status"),
                    "reconciled_groups": r.get("reconciled_groups"),
                    "truth_established": r.get("truth_established"),
                    "truth_source_summary": r.get("truth_source_summary"),
                    "unresolved_items": r.get("unresolved_items"),
                }
                for r in records
            ],
        },
    )
    _dump(out_root / "calibration_metrics.json", result.get("calibration_metrics") or {})
    write_review_tree(out_root=out_root, records=records)
    write_calibration_report(out_root=out_root, result=result)
    write_status_md(out_root=out_root, result=result)
    tmpl = Path(package_dir) / "fixtures" / "manual_verification_template.json"
    if tmpl.exists():
        shutil.copy2(tmpl, out_root / "manual_verification_template.json")
    slim = {
        k: result.get(k)
        for k in (
            "phase_id",
            "phase_name",
            "model_version",
            "gate_version",
            "decision",
            "pass_fail",
            "calibration_metrics",
            "handoff_answers",
            "production",
            "fingerprints",
            "unit_tests",
            "anti_hardcoding",
            "live_claude_call",
        )
    }
    if isinstance(slim.get("unit_tests"), dict):
        slim["unit_tests"] = {
            "success": slim["unit_tests"].get("success"),
            "passed": slim["unit_tests"].get("passed"),
            "total": slim["unit_tests"].get("total"),
        }
    _dump(out_root / "P2.6.10-C.4_RESULTS.json", slim)


__all__ = ["write_reports"]
