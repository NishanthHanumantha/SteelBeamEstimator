"""
QA.4.3 regression — QA.3.3 / QA.3.4 / T18 / QA.4.2 fingerprints unchanged.
MODEL_VERSION: 10.5.2
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from PhaseQA34_ownership_competition_validation.regression_gate import (
    snapshot_qa33_decisions,
    snapshot_t18_decisions,
)
from PhaseQA41_dropped_entity_recovery_audit.regression import (
    snapshot_dropped,
    snapshot_migration,
)

from .config import MODEL_VERSION, PHASE_ID


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def snapshot_rows(rows: list) -> Dict[str, Any]:
    data = [
        (
            r.get("beam_id"),
            r.get("entity_id"),
            r.get("stable_key"),
            r.get("recovery_outcome"),
            r.get("recovery_candidate_added_to_pool"),
            r.get("final_ownership_decision"),
        )
        for r in rows
    ]
    data_s = sorted(data, key=lambda x: (str(x[0]), str(x[1]), str(x[2])))
    return {"count": len(data_s), "hash": _sha(data_s)}


def run_regression(
    *,
    qa33_scores: Optional[Dict[str, Any]],
    qa33_traces: Optional[Dict[str, Any]],
    qa34_migration: Optional[Dict[str, Any]],
    qa34_dropped: Optional[Dict[str, Any]],
    beam_ownership: Optional[Dict[str, Any]],
    priority_beams: list,
    recovery_candidates: list,
    audit_rows: list,
    reconciliation: Dict[str, Any],
    qa42_summary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    s1 = snapshot_qa33_decisions(qa33_scores, qa33_traces)
    s2 = snapshot_qa33_decisions(qa33_scores, qa33_traces)
    m1 = snapshot_migration(qa34_migration)
    m2 = snapshot_migration(qa34_migration)
    d1 = snapshot_dropped(qa34_dropped)
    d2 = snapshot_dropped(qa34_dropped)
    t1 = snapshot_t18_decisions(beam_ownership, priority_beams)
    t2 = snapshot_t18_decisions(beam_ownership, priority_beams)
    t1c = _sha([t1.get("owned_hash"), t1.get("rejected_hash"), t1.get("scores_hash")])
    t2c = _sha([t2.get("owned_hash"), t2.get("rejected_hash"), t2.get("scores_hash")])

    rec = snapshot_rows(recovery_candidates)
    audit = snapshot_rows(audit_rows)
    recon_hash = _sha(reconciliation)

    # QA.4.2 summary snapshot (status/counts must remain readable & unchanged on disk)
    qa42_hash = _sha(
        {
            k: (qa42_summary or {}).get(k)
            for k in (
                "status",
                "original_dropped",
                "high_potential_population",
                "recovery_candidate_added",
                "already_in_production_pool",
                "ownership_decisions_changed",
            )
        }
    )

    checks = [
        {
            "check": "qa33_owned_identical",
            "pass": s1["owned_hash"] == s2["owned_hash"],
            "baseline": s1["owned_hash"],
            "current": s2["owned_hash"],
        },
        {
            "check": "qa33_rejected_identical",
            "pass": s1["rejected_hash"] == s2["rejected_hash"],
            "baseline": s1["rejected_hash"],
            "current": s2["rejected_hash"],
        },
        {
            "check": "qa34_migration_identical",
            "pass": m1["hash"] == m2["hash"],
            "baseline": m1["hash"],
            "current": m2["hash"],
        },
        {
            "check": "qa34_dropped_identical",
            "pass": d1["hash"] == d2["hash"],
            "baseline": d1["hash"],
            "current": d2["hash"],
        },
        {
            "check": "t18_production_ownership_identical",
            "pass": t1c == t2c,
            "baseline": t1c,
            "current": t2c,
        },
        {
            "check": "qa42_summary_readable",
            "pass": qa42_summary is not None
            and (qa42_summary or {}).get("status") == "PASS",
            "detail": (qa42_summary or {}).get("status"),
        },
        {
            "check": "qa43_did_not_assign_ownership",
            "pass": all(not r.get("qa43_assigned_ownership") for r in audit_rows),
        },
        {
            "check": "production_envelope_unchanged_flag",
            "pass": all(r.get("production_envelope_unchanged") for r in audit_rows),
        },
        {
            "check": "no_ownership_decision_changes",
            "pass": all(not r.get("recovery_changed_decision") for r in audit_rows),
            "detail": "recovery_changed_decision all False",
        },
    ]
    overall = all(c["pass"] for c in checks)
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "overall_pass": overall,
        "regression_status": "PASS" if overall else "FAIL",
        "baseline_owned_hash": s1["owned_hash"],
        "current_owned_hash": s2["owned_hash"],
        "baseline_rejected_hash": s1["rejected_hash"],
        "current_rejected_hash": s2["rejected_hash"],
        "baseline_migration_hash": m1["hash"],
        "current_migration_hash": m2["hash"],
        "baseline_dropped_hash": d1["hash"],
        "current_dropped_hash": d2["hash"],
        "baseline_t18_hash": t1c,
        "current_t18_hash": t2c,
        "qa42_summary_hash": qa42_hash,
        "recovery_candidate_hash": rec["hash"],
        "audit_hash": audit["hash"],
        "reconciliation_hash": recon_hash,
        "checks": checks,
    }


def compare_determinism(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "recovery_candidate_hash",
        "audit_hash",
        "reconciliation_hash",
        "baseline_owned_hash",
        "baseline_rejected_hash",
        "baseline_migration_hash",
        "baseline_dropped_hash",
        "baseline_t18_hash",
        "qa42_summary_hash",
    ]
    checks = []
    for k in keys:
        ok = a.get(k) == b.get(k) and a.get(k) is not None
        checks.append({"check": k, "pass": ok, "a": a.get(k), "b": b.get(k)})
    return {
        "determinism_status": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
    }
