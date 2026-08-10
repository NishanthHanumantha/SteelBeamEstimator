"""
Write QA.4.3 artefacts and documentation.
MODEL_VERSION: 10.5.2
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .config import MODEL_VERSION, PHASE_ID


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def build_summary(
    *,
    populations: Dict[str, Any],
    reconciliation: Dict[str, Any],
    contamination: Dict[str, Any],
    regression: Dict[str, Any],
    determinism: Dict[str, Any],
    validation: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "status": validation.get("status"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_dropped_leaders_inspected": populations.get("leader_count"),
        "original_dropped": populations.get("original_dropped"),
        "p2_candidates_generated": reconciliation.get("recovery_candidate_generated"),
        "high_count": populations.get("high_count"),
        "medium_count": populations.get("medium_count"),
        "low_count": populations.get("low_count"),
        "unknown_count": populations.get("unknown_count"),
        "recovery_eligible": reconciliation.get("recovery_eligible"),
        "excluded_count": reconciliation.get("recovery_excluded"),
        "already_in_production_count": reconciliation.get("already_in_production_pool"),
        "newly_added_count": reconciliation.get("recovery_candidate_added"),
        "t18_accepted_count": reconciliation.get("existing_engine_accepted"),
        "t18_rejected_count": reconciliation.get("existing_engine_rejected"),
        "neighbour_ambiguity_count": reconciliation.get("neighbour_ambiguity_count"),
        "inside_other_beam_count": reconciliation.get("inside_other_beam_count"),
        "far_outside_count": reconciliation.get("far_outside_count"),
        "duplicate_stable_keys": contamination.get("duplicate_stable_key_count"),
        "cross_beam_contamination": contamination.get("cross_beam_contamination_count"),
        "fifth_set_count": populations.get("fifth_set_recovery_population"),
        "sixth_set_count": populations.get("sixth_set_recovery_population"),
        "production_ownership_changed": bool(
            reconciliation.get("ownership_decisions_changed")
        ),
        "production_envelope_changed": False,
        "qa42_regression": "PASS"
        if any(
            c.get("check") == "qa42_summary_readable" and c.get("pass")
            for c in (regression.get("checks") or [])
        )
        else "FAIL",
        "t18_regression": "PASS"
        if any(
            c.get("check") == "t18_production_ownership_identical" and c.get("pass")
            for c in (regression.get("checks") or [])
        )
        else "FAIL",
        "regression_status": regression.get("regression_status"),
        "determinism_status": determinism.get("determinism_status"),
        "overall_gate": validation.get("status"),
        "principle": "Detect → Validate → Deduplicate → Defer ownership to T18 → Audit → Regress",
        "qa43_assigns_ownership": False,
        "p3_geometry_recovery_implemented": False,
        "note": (
            "Zero newly-added candidates is a valid PASS when T18 already rejected "
            "the P2 leaders. Do not claim ownership improvement."
        ),
    }


def write_all(
    out_root: Path,
    *,
    recovery_candidates: List[Dict[str, Any]],
    audit_rows: List[Dict[str, Any]],
    summary: Dict[str, Any],
    reconciliation: Dict[str, Any],
    regression: Dict[str, Any],
    contamination: Dict[str, Any],
    tests: Dict[str, Any],
    determinism: Dict[str, Any],
    validation: Dict[str, Any],
) -> Dict[str, str]:
    out_root.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}

    mapping = {
        "recovery_candidates.json": {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "count": len(recovery_candidates),
            "candidates": recovery_candidates,
        },
        "leader_recovery_audit.json": {
            "phase_id": PHASE_ID,
            "count": len(audit_rows),
            "rows": audit_rows,
        },
        "reconciliation.json": {"phase_id": PHASE_ID, **reconciliation},
        "regression.json": regression,
        "QA_SUMMARY.json": summary,
        "QA43_contamination_report.json": {"phase_id": PHASE_ID, **contamination},
        "QA43_test_cases.json": tests,
        "QA43_determinism.json": determinism,
        "PASS_FAIL_REPORT.json": validation,
    }
    for name, obj in mapping.items():
        p = out_root / name
        _dump(p, obj)
        paths[name] = str(p)

    # Also aliases matching QA.4.2 naming style
    _dump(out_root / "QA43_recovery_candidates.json", mapping["recovery_candidates.json"])
    _dump(out_root / "QA43_recovery_summary.json", summary)
    paths["QA43_recovery_summary.json"] = str(out_root / "QA43_recovery_summary.json")

    (out_root / "QA_REPORT.md").write_text(_qa_report(summary, validation, reconciliation), encoding="utf-8")
    (out_root / "ARCHITECTURE_SUMMARY.md").write_text(_architecture(), encoding="utf-8")
    (out_root / "DELIVERY_NOTE.md").write_text(_delivery(summary), encoding="utf-8")
    (out_root / "ExecutionSummary.md").write_text(_exec(summary, validation), encoding="utf-8")
    (out_root / "README.md").write_text(_readme(), encoding="utf-8")
    for name in (
        "QA_REPORT.md",
        "ARCHITECTURE_SUMMARY.md",
        "DELIVERY_NOTE.md",
        "ExecutionSummary.md",
        "README.md",
    ):
        paths[name] = str(out_root / name)
    return paths


def _qa_report(summary, validation, reconciliation) -> str:
    return "\n".join(
        [
            f"# QA.4.3 — P2 Leader Recovery Report",
            "",
            f"- MODEL_VERSION: `{MODEL_VERSION}`",
            f"- Overall gate: `{summary.get('overall_gate')}`",
            "",
            "## Population",
            f"- Dropped leaders inspected: `{summary.get('total_dropped_leaders_inspected')}`",
            f"- HIGH / MEDIUM / LOW / UNKNOWN: "
            f"`{summary.get('high_count')}` / `{summary.get('medium_count')}` / "
            f"`{summary.get('low_count')}` / `{summary.get('unknown_count')}`",
            "",
            "## Recovery",
            f"- Candidates generated: `{summary.get('p2_candidates_generated')}`",
            f"- Eligible: `{summary.get('recovery_eligible')}`",
            f"- Excluded / diagnostic: `{summary.get('excluded_count')}`",
            f"- Already in production accepted: `{summary.get('already_in_production_count')}`",
            f"- Newly added: `{summary.get('newly_added_count')}`",
            f"- T18 accepted / rejected: `{summary.get('t18_accepted_count')}` / `{summary.get('t18_rejected_count')}`",
            "",
            "## Safety",
            f"- Neighbour ambiguity: `{summary.get('neighbour_ambiguity_count')}`",
            f"- Inside other beam: `{summary.get('inside_other_beam_count')}`",
            f"- Far outside: `{summary.get('far_outside_count')}`",
            f"- Duplicates: `{summary.get('duplicate_stable_keys')}`",
            f"- Contamination: `{summary.get('cross_beam_contamination')}`",
            f"- Fifth / Sixth: `{summary.get('fifth_set_count')}` / `{summary.get('sixth_set_count')}`",
            f"- Production ownership changed: `{summary.get('production_ownership_changed')}`",
            f"- Production envelope changed: `{summary.get('production_envelope_changed')}`",
            "",
            "## Gates",
            f"- QA.4.2 regression: `{summary.get('qa42_regression')}`",
            f"- T18 regression: `{summary.get('t18_regression')}`",
            f"- Determinism: `{summary.get('determinism_status')}`",
            f"- Failed gates: `{validation.get('failed_gates')}`",
            "",
            "## Outcomes",
            f"`{reconciliation.get('outcome_counts')}`",
            "",
            "P3 geometry recovery was NOT implemented.",
            "",
        ]
    )


def _architecture() -> str:
    return "\n".join(
        [
            "# QA.4.3 Architecture Summary",
            "",
            "## Pipeline",
            "",
            "```",
            "Input (QA.4.1 DroppedEntityAudit)",
            "  ↓",
            "Dropped Leader Inventory (LEADER_CHAIN_FAILURE, Fourth Set)",
            "  ↓",
            "P2 Candidate Detection",
            "  ↓",
            "Spatial / Context Validation (QA.4.1 evidence flags)",
            "  ↓",
            "Eligibility (HIGH/MEDIUM; exclude FAR/neighbour/inside-other)",
            "  ↓",
            "Deduplication (accepted_node_ids + T18 leader_results)",
            "  ↓",
            "Existing T18 Ownership (leader_results / evaluate_leader)",
            "  ↓",
            "QA.4.3 Audit",
            "  ↓",
            "Regression / Determinism Gate",
            "```",
            "",
            "## Why P2 exists",
            "",
            "QA.4.2 showed HIGH envelope satellites were already in T18 accepted nodes.",
            "The remaining ownership gap class from QA.4.1 is LEADER_CHAIN_FAILURE (23).",
            "P2 asks whether those leaders can safely re-enter the candidate path.",
            "",
            "## What P2 may recover",
            "",
            "- Leaders with HIGH/MEDIUM potential and non-contaminated geometry",
            "- Only as recovery *candidates* passed to existing T18 evaluation",
            "",
            "## What P2 must not recover",
            "",
            "- Neighbour-ambiguous leaders",
            "- Leaders inside another beam envelope",
            "- Far-outside leaders",
            "- Owned-elsewhere entities",
            "- Anything via a second ownership score",
            "",
            "## Why T18 remains authoritative",
            "",
            "QA.4.3 reads `leader_results` / rejected annotations, or calls",
            "`evaluate_leader` / `evaluate_annotation_chain` without changing rules.",
            "It never writes BeamOwnership.json or mutates accepted_node_ids.",
            "",
            "## Contamination prevention",
            "",
            "Eligibility rejects neighbour_ambiguity and inside_other_beam_envelope.",
            "Cross-beam accepted_node_ids checks block illegal multi-beam adds.",
            "",
            "## Deduplication",
            "",
            "If a leader is already in accepted_node_ids → ALREADY_IN_PRODUCTION_POOL.",
            "If already in T18 leader_results as rejected → ownership_rejected,",
            "recovery_candidate_added_to_pool = false (already scored).",
            "",
            "## Production artefacts",
            "",
            "Unchanged by design. Append-only QA.4.3 outputs only.",
            "",
        ]
    )


def _delivery(summary) -> str:
    return "\n".join(
        [
            "# QA.4.3 Delivery Note",
            "",
            f"MODEL_VERSION: `{MODEL_VERSION}`",
            f"Status: `{summary.get('overall_gate')}`",
            "",
            "Package: `Version10/src/PhaseQA43_p2_leader_recovery/`",
            "Runner: `python Run_PY/run_phase_qa43_p2_leader_recovery.py`",
            "Output: `Version10/data/output/PhaseQA43_p2_leader_recovery/`",
            "",
            f"Newly added candidates: `{summary.get('newly_added_count')}`",
            f"T18 rejected: `{summary.get('t18_rejected_count')}`",
            f"Production ownership changed: `{summary.get('production_ownership_changed')}`",
            "",
            "P3 was NOT implemented. STOP after QA.4.3.",
            "",
        ]
    )


def _exec(summary, validation) -> str:
    return "\n".join(
        [
            f"# Phase {PHASE_ID} Execution Summary",
            "",
            f"- MODEL_VERSION: `{MODEL_VERSION}`",
            f"- STATUS: `{summary.get('overall_gate')}`",
            "",
            "QA.4.3 is append-only P2 Leader Recovery for Fourth Set.",
            "T18 remains authoritative. No production ownership assignment.",
            "P3 geometry recovery was not implemented.",
            "",
            f"- Leaders inspected: `{summary.get('total_dropped_leaders_inspected')}`",
            f"- Candidates generated: `{summary.get('p2_candidates_generated')}`",
            f"- Newly added: `{summary.get('newly_added_count')}`",
            f"- T18 accepted/rejected: `{summary.get('t18_accepted_count')}` / `{summary.get('t18_rejected_count')}`",
            f"- Regression: `{summary.get('regression_status')}`",
            f"- Determinism: `{summary.get('determinism_status')}`",
            f"- Failed gates: `{validation.get('failed_gates')}`",
            "",
        ]
    )


def _readme() -> str:
    return "\n".join(
        [
            f"# Phase {PHASE_ID} — P2 Leader Recovery",
            "",
            f"MODEL_VERSION: `{MODEL_VERSION}`",
            "",
            "Append-only diagnostic recovery layer for LEADER_CHAIN_FAILURE entities.",
            "Existing T18 ownership engine remains authoritative.",
            "",
            "`python Run_PY/run_phase_qa43_p2_leader_recovery.py`",
            "",
        ]
    )
