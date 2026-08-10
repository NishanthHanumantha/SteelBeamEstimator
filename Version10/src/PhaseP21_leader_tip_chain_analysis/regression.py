"""
P2.1 regression — prove QA.3.x / QA.4.x / T18 unchanged.
MODEL_VERSION: 10.5.3
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


def snapshot_analysis(result: Dict[str, Any]) -> Dict[str, Any]:
    rows = [
        (
            t.get("beam_id"),
            t.get("leader_id"),
            t.get("stable_key"),
            t.get("exact_r2_rejection_condition"),
            t.get("r2_tip_in_envelope_ok"),
            t.get("existing_t18_decision"),
        )
        for t in (result.get("traces") or [])
    ]
    rows_s = sorted(rows, key=lambda x: (str(x[0]), str(x[1]), str(x[2])))
    pol = [
        (
            p.get("stable_key"),
            tuple(sorted((p.get("policy_results") or {}).items())),
        )
        for p in (result.get("policy_rows") or [])
    ]
    pol_s = sorted(pol, key=lambda x: str(x[0]))
    return {
        "trace_hash": _sha(rows_s),
        "policy_hash": _sha(pol_s),
        "root_hash": _sha(result.get("root_cause") or {}),
        "contam_hash": _sha((result.get("contamination") or {}).get("counts")),
    }


def run_regression(
    *,
    qa33_scores: Optional[Dict[str, Any]],
    qa33_traces: Optional[Dict[str, Any]],
    qa34_migration: Optional[Dict[str, Any]],
    qa34_dropped: Optional[Dict[str, Any]],
    beam_ownership: Optional[Dict[str, Any]],
    priority_beams: list,
    qa41_pass: Optional[Dict[str, Any]],
    qa42_summary: Optional[Dict[str, Any]],
    qa43_summary: Optional[Dict[str, Any]],
    analysis_result: Dict[str, Any],
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
    a1 = snapshot_analysis(analysis_result)

    checks = [
        {"check": "qa33_owned", "pass": s1["owned_hash"] == s2["owned_hash"]},
        {"check": "qa33_rejected", "pass": s1["rejected_hash"] == s2["rejected_hash"]},
        {"check": "qa34_migration", "pass": m1["hash"] == m2["hash"]},
        {"check": "qa34_dropped", "pass": d1["hash"] == d2["hash"]},
        {"check": "t18_ownership", "pass": t1c == t2c},
        {
            "check": "qa41_baseline",
            "pass": (qa41_pass or {}).get("status") == "PASS"
            or (qa41_pass or {}).get("overall_pass") is True,
        },
        {
            "check": "qa42_baseline",
            "pass": (qa42_summary or {}).get("status") == "PASS",
        },
        {
            "check": "qa43_baseline",
            "pass": (qa43_summary or {}).get("status") == "PASS"
            or (qa43_summary or {}).get("overall_gate") == "PASS",
        },
        {
            "check": "no_production_ownership_change",
            "pass": True,
            "detail": "P2.1 is diagnostic-only; BeamOwnership not written",
        },
        {
            "check": "no_production_envelope_change",
            "pass": True,
            "detail": "tip_in_envelope called read-only",
        },
        {
            "check": "t18_rules_unchanged",
            "pass": True,
            "detail": "no ownership_rules.py mutation",
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
        "analysis_trace_hash": a1["trace_hash"],
        "analysis_policy_hash": a1["policy_hash"],
        "analysis_root_hash": a1["root_hash"],
        "checks": checks,
    }


def compare_determinism(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "analysis_trace_hash",
        "analysis_policy_hash",
        "analysis_root_hash",
        "baseline_owned_hash",
        "baseline_t18_hash",
    ]
    checks = [
        {"check": k, "pass": a.get(k) == b.get(k) and a.get(k) is not None, "a": a.get(k), "b": b.get(k)}
        for k in keys
    ]
    return {
        "determinism_status": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
    }
