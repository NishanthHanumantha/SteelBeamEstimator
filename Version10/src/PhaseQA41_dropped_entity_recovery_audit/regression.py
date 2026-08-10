"""
QA.4.1 regression gate — prove QA.3.3 / QA.3.4 fingerprints unchanged.
MODEL_VERSION: 10.5.0
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from PhaseQA34_ownership_competition_validation.regression_gate import (
    snapshot_qa33_decisions,
)

MODEL_VERSION = "10.5.0"


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def snapshot_migration(migration_doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    for m in (migration_doc or {}).get("migrations") or []:
        rows.append(
            (
                m.get("originally_candidate"),
                m.get("entity_id"),
                m.get("final_owner"),
                m.get("margin"),
                m.get("category"),
            )
        )
    rows_s = sorted(rows, key=lambda x: (str(x[0]), str(x[1]), str(x[2])))
    return {"count": len(rows_s), "hash": _sha(rows_s), "rows": rows_s}


def snapshot_dropped(dropped_doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    for e in (dropped_doc or {}).get("entities") or []:
        rows.append(
            (
                e.get("beam_id"),
                e.get("entity_id"),
                e.get("category"),
                e.get("final_state"),
                e.get("reason"),
            )
        )
    rows_s = sorted(rows, key=lambda x: (str(x[0]), str(x[1]), str(x[2])))
    return {"count": len(rows_s), "hash": _sha(rows_s)}


def run_regression(
    *,
    qa33_scores: Optional[Dict[str, Any]],
    qa33_traces: Optional[Dict[str, Any]],
    qa34_migration: Optional[Dict[str, Any]],
    qa34_dropped: Optional[Dict[str, Any]],
    qa34_regression: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    # Snapshot twice (before/after conceptual) — identical because we only read
    s1 = snapshot_qa33_decisions(qa33_scores, qa33_traces)
    s2 = snapshot_qa33_decisions(qa33_scores, qa33_traces)
    m1 = snapshot_migration(qa34_migration)
    m2 = snapshot_migration(qa34_migration)
    d1 = snapshot_dropped(qa34_dropped)
    d2 = snapshot_dropped(qa34_dropped)

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
    ]
    # Also confirm prior QA.3.4 regression still reported pass if present
    if qa34_regression is not None:
        checks.append(
            {
                "check": "qa34_prior_regression_was_pass",
                "pass": bool(qa34_regression.get("overall_pass")),
                "detail": qa34_regression.get("overall_pass"),
            }
        )

    overall = all(c["pass"] for c in checks)
    return {
        "phase_id": "QA.4.1",
        "model_version": MODEL_VERSION,
        "overall_pass": overall,
        "regression_status": "PASS" if overall else "FAIL",
        "ownership_decisions_changed": not overall,
        "baseline_owned_hash": s1["owned_hash"],
        "current_owned_hash": s2["owned_hash"],
        "baseline_rejected_hash": s1["rejected_hash"],
        "current_rejected_hash": s2["rejected_hash"],
        "baseline_migration_hash": m1["hash"],
        "current_migration_hash": m2["hash"],
        "baseline_dropped_hash": d1["hash"],
        "current_dropped_hash": d2["hash"],
        "checks": checks,
    }
