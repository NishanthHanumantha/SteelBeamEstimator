"""
Write QA.4.2 artefacts.
MODEL_VERSION: 10.5.1
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .config import MODEL_VERSION, PHASE_ID


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def write_all(
    out_root: Path,
    *,
    recovery_candidates: List[Dict[str, Any]],
    audit_rows: List[Dict[str, Any]],
    summary: Dict[str, Any],
    reconciliation: Dict[str, Any],
    regression: Dict[str, Any],
    contamination: Dict[str, Any],
    pattern_summary: Dict[str, Any],
    high_report: Dict[str, Any],
    tests: Dict[str, Any],
    determinism: Dict[str, Any],
    validation: Dict[str, Any],
    diagnostic_rows: List[Dict[str, Any]],
) -> Dict[str, str]:
    out_root.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}

    p = out_root / "QA42_recovery_candidates.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "count": len(recovery_candidates),
            "note": "Append-only recovery candidate layer; ownership decided by existing T18 engine",
            "candidates": recovery_candidates,
        },
    )
    paths[p.name] = str(p)

    p = out_root / "QA42_recovery_audit.csv"
    _write_csv(p, audit_rows)
    paths[p.name] = str(p)

    p = out_root / "QA42_recovery_audit.json"
    _dump(p, {"phase_id": PHASE_ID, "count": len(audit_rows), "rows": audit_rows})
    paths[p.name] = str(p)

    p = out_root / "QA42_recovery_summary.json"
    _dump(p, summary)
    paths[p.name] = str(p)

    p = out_root / "QA42_reconciliation.json"
    _dump(p, {"phase_id": PHASE_ID, **reconciliation})
    paths[p.name] = str(p)

    p = out_root / "QA42_regression_report.json"
    _dump(p, regression)
    paths[p.name] = str(p)

    p = out_root / "QA42_contamination_report.json"
    _dump(p, {"phase_id": PHASE_ID, **contamination})
    paths[p.name] = str(p)

    p = out_root / "QA42_pattern_summary.json"
    _dump(p, pattern_summary)
    paths[p.name] = str(p)

    p = out_root / "QA42_high_potential_report.json"
    _dump(p, high_report)
    paths[p.name] = str(p)

    p = out_root / "QA42_diagnostic_medium_low.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "count": len(diagnostic_rows),
            "rows": diagnostic_rows,
        },
    )
    paths[p.name] = str(p)

    p = out_root / "QA42_test_cases.json"
    _dump(p, tests)
    paths[p.name] = str(p)

    p = out_root / "QA42_determinism.json"
    _dump(p, determinism)
    paths[p.name] = str(p)

    p = out_root / "PASS_FAIL_REPORT.json"
    _dump(p, validation)
    paths[p.name] = str(p)

    p = out_root / "ExecutionSummary.md"
    p.write_text(_exec_md(summary, validation, reconciliation), encoding="utf-8")
    paths[p.name] = str(p)

    p = out_root / "README.md"
    p.write_text(_readme(), encoding="utf-8")
    paths[p.name] = str(p)

    return paths


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
        "original_dropped": populations.get("original_dropped"),
        "envelope_population": populations.get("envelope_count"),
        "high_potential_population": populations.get("high_count"),
        "recovery_examined": reconciliation.get("recovery_examined"),
        "recovery_eligible": reconciliation.get("recovery_eligible"),
        "recovery_excluded": reconciliation.get("recovery_excluded"),
        "recovery_candidate_added": reconciliation.get("recovery_candidate_added"),
        "recovery_candidate_generated": reconciliation.get("recovery_candidate_generated"),
        "already_in_production_pool": reconciliation.get("already_in_production_pool"),
        "existing_engine_rejected": reconciliation.get("existing_engine_rejected"),
        "existing_engine_accepted": reconciliation.get("existing_engine_accepted"),
        "ownership_decisions_changed": reconciliation.get("ownership_decisions_changed"),
        "cross_beam_contamination_count": contamination.get(
            "cross_beam_contamination_count"
        ),
        "duplicate_count": contamination.get("duplicate_stable_key_count"),
        "fourth_set_count": populations.get("fourth_set_recovery_population"),
        "fifth_set_count": populations.get("fifth_set_recovery_population"),
        "sixth_set_count": populations.get("sixth_set_recovery_population"),
        "regression_status": regression.get("regression_status"),
        "determinism_status": determinism.get("determinism_status"),
        "final_gate_status": validation.get("status"),
        "principle": "Recover candidates first. Let the existing ownership engine decide.",
        "production_envelope_semantics": "UNCHANGED",
        "qa42_assigns_ownership": False,
    }


def build_high_report(audit_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    high = audit_rows  # audit_rows are HIGH-only examined set
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "total_HIGH_envelope_cases": len(high),
        "HIGH_recovered_newly_added": sum(
            1 for r in high if r.get("recovery_candidate_added_to_pool")
        ),
        "HIGH_excluded": sum(
            1
            for r in high
            if str(r.get("recovery_outcome") or "").startswith("recovery_excluded")
        ),
        "HIGH_already_in_production_pool": sum(
            1 for r in high if r.get("recovery_outcome") == "already_in_production_pool"
        ),
        "HIGH_accepted_by_existing_ownership": sum(
            1
            for r in high
            if r.get("final_ownership_decision") == "ACCEPTED"
            or r.get("recovery_outcome") == "already_in_production_pool"
        ),
        "HIGH_rejected_by_existing_ownership": sum(
            1 for r in high if r.get("final_ownership_decision") == "REJECTED"
        ),
        "cases": [
            {
                "beam_id": r.get("beam_id"),
                "entity_id": r.get("entity_id"),
                "stable_key": r.get("stable_key"),
                "spatial_relationship": r.get("spatial_relationship"),
                "distance": r.get("min_distance_to_production_envelope"),
                "target_beam_context": r.get("target_beam_context"),
                "longitudinal_overlap": r.get("longitudinal_overlap"),
                "neighbour_ambiguity": r.get("neighbour_ambiguity"),
                "inside_other_beam_envelope": r.get("inside_other_beam_envelope"),
                "recovery_decision": r.get("recovery_outcome"),
                "existing_ownership_result": r.get("existing_ownership_result")
                or r.get("final_ownership_decision"),
            }
            for r in high
        ],
    }


def build_pattern_summary(
    audit_rows: List[Dict[str, Any]], diagnostic_rows: List[Dict[str, Any]]
) -> Dict[str, Any]:
    from collections import Counter

    return {
        "phase_id": PHASE_ID,
        "high_outcome_counts": dict(Counter(r.get("recovery_outcome") for r in audit_rows)),
        "high_spatial_counts": dict(
            Counter(r.get("spatial_relationship") for r in audit_rows)
        ),
        "diagnostic_potential_counts": dict(
            Counter(r.get("recovery_potential") for r in diagnostic_rows)
        ),
        "diagnostic_spatial_counts": dict(
            Counter(r.get("spatial_relationship") for r in diagnostic_rows)
        ),
        "note": (
            "P1 recovery targets HIGH BOUNDARY/NEAR_OUTSIDE with target-beam evidence. "
            "MEDIUM/LOW remain diagnostic."
        ),
    }


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    fields = [
        "beam_id",
        "entity_id",
        "stable_key",
        "entity_type",
        "recovery_potential",
        "spatial_relationship",
        "min_distance_to_production_envelope",
        "recovery_eligible",
        "recovery_exclusion_reason",
        "recovery_candidate_generated",
        "recovery_candidate_added_to_pool",
        "recovery_outcome",
        "existing_ownership_result",
        "final_ownership_decision",
        "recovery_changed_decision",
        "neighbour_ambiguity",
        "inside_other_beam_envelope",
        "target_beam_context",
        "already_in_production_candidate_pool",
        "engine_path",
        "qa42_assigned_ownership",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fields})


def _exec_md(summary, validation, reconciliation) -> str:
    return "\n".join(
        [
            f"# Phase {PHASE_ID} Execution Summary",
            "",
            f"- MODEL_VERSION: `{MODEL_VERSION}`",
            f"- STATUS: `{summary.get('status')}`",
            "",
            "QA.4.2 implements append-only P1 Candidate / Search Envelope Recovery",
            "for the Fourth Set HIGH envelope population.",
            "",
            "Production envelope semantics are UNCHANGED.",
            "QA.4.2 does not assign ownership; the existing T18 engine decides.",
            "",
            "## Counts",
            f"- original_dropped: `{summary.get('original_dropped')}`",
            f"- envelope_population: `{summary.get('envelope_population')}`",
            f"- high_potential_population: `{summary.get('high_potential_population')}`",
            f"- recovery_examined: `{summary.get('recovery_examined')}`",
            f"- recovery_eligible: `{summary.get('recovery_eligible')}`",
            f"- recovery_excluded: `{summary.get('recovery_excluded')}`",
            f"- recovery_candidate_generated: `{summary.get('recovery_candidate_generated')}`",
            f"- recovery_candidate_added (new): `{summary.get('recovery_candidate_added')}`",
            f"- already_in_production_pool: `{summary.get('already_in_production_pool')}`",
            f"- existing_engine_accepted: `{summary.get('existing_engine_accepted')}`",
            f"- existing_engine_rejected: `{summary.get('existing_engine_rejected')}`",
            f"- ownership_decisions_changed: `{summary.get('ownership_decisions_changed')}`",
            f"- contamination: `{summary.get('cross_beam_contamination_count')}`",
            f"- duplicates: `{summary.get('duplicate_count')}`",
            f"- fifth/sixth: `{summary.get('fifth_set_count')}` / `{summary.get('sixth_set_count')}`",
            f"- regression: `{summary.get('regression_status')}`",
            f"- determinism: `{summary.get('determinism_status')}`",
            "",
            f"Failed gates: `{validation.get('failed_gates')}`",
            "",
            "STOP — do not proceed to QA.4.3 / P2 / P3 without review.",
            "",
        ]
    )


def _readme() -> str:
    return "\n".join(
        [
            f"# Phase {PHASE_ID} — P1 Candidate / Search Envelope Recovery",
            "",
            f"MODEL_VERSION: `{MODEL_VERSION}`",
            "",
            "Append-only recovery layer. Production envelope unchanged.",
            "Existing ownership engine remains authoritative.",
            "",
            "Runner:",
            "`python Run_PY/run_phase_qa42_candidate_search_envelope_recovery.py`",
            "",
        ]
    )
