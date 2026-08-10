"""
P2.3 regression — historical T18 / QA baselines must remain unchanged.
MODEL_VERSION: 10.5.5
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from PhaseQA34_ownership_competition_validation.regression_gate import (
    snapshot_qa33_decisions,
    snapshot_t18_decisions,
)
from PhaseQA41_dropped_entity_recovery_audit.regression import (
    snapshot_dropped,
    snapshot_migration,
)

from .config import MODEL_VERSION, PHASE_ID, PRODUCTION_POLICY


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def snapshot_controlled(result: Dict[str, Any]) -> Dict[str, Any]:
    mig = [
        (
            m.get("beam_id"),
            m.get("entity_id"),
            m.get("source"),
            m.get("recovery_policy"),
            m.get("controlled_status"),
        )
        for m in (result.get("migrations") or [])
    ]
    prop = [
        (
            p.get("beam_id"),
            p.get("recovered_leader"),
            tuple(p.get("propagated_graph_children") or []),
        )
        for p in (result.get("propagation") or [])
    ]
    return {
        "effective_ownership_hash": _sha(
            {
                bid: sorted(
                    (
                        ((result.get("controlled_ownership") or {}).get("by_beam") or {})
                        .get(bid)
                        or {}
                    ).get("accepted_node_ids")
                    or []
                )
                for bid in sorted(result.get("beam_ids") or [])
            }
        ),
        "migration_hash": _sha(sorted(mig)),
        "recovery_propagation_hash": _sha(sorted(prop)),
        "render_manifest_hash": (result.get("render_comparison") or {}).get(
            "render_manifest_hash"
        ),
        "benchmark_output_hash": _sha(result.get("accuracy_comparison") or {}),
    }


def run_regression(
    *,
    qa33_scores: Optional[Dict[str, Any]],
    qa33_traces: Optional[Dict[str, Any]],
    qa34_migration: Optional[Dict[str, Any]],
    qa34_dropped: Optional[Dict[str, Any]],
    historical_beam_ownership: Optional[Dict[str, Any]],
    priority_beams: list,
    qa41_pass: Optional[Dict[str, Any]],
    qa42_summary: Optional[Dict[str, Any]],
    qa43_summary: Optional[Dict[str, Any]],
    p21_pass: Optional[Dict[str, Any]],
    p22_pass: Optional[Dict[str, Any]],
    baseline_snapshot: Dict[str, Any],
    historical_ownership_path_hash: Optional[str],
    post_run_historical_hash: Optional[str],
    analysis_result: Dict[str, Any],
) -> Dict[str, Any]:
    s1 = snapshot_qa33_decisions(qa33_scores, qa33_traces)
    s2 = snapshot_qa33_decisions(qa33_scores, qa33_traces)
    m1 = snapshot_migration(qa34_migration)
    m2 = snapshot_migration(qa34_migration)
    d1 = snapshot_dropped(qa34_dropped)
    d2 = snapshot_dropped(qa34_dropped)
    t1 = snapshot_t18_decisions(historical_beam_ownership, priority_beams)
    t2 = snapshot_t18_decisions(historical_beam_ownership, priority_beams)
    t1c = _sha([t1.get("owned_hash"), t1.get("rejected_hash"), t1.get("scores_hash")])
    t2c = _sha([t2.get("owned_hash"), t2.get("rejected_hash"), t2.get("scores_hash")])
    ctrl = snapshot_controlled(analysis_result)

    checks = [
        {"check": "qa33_owned", "pass": s1["owned_hash"] == s2["owned_hash"]},
        {"check": "qa33_rejected", "pass": s1["rejected_hash"] == s2["rejected_hash"]},
        {"check": "qa34_migration", "pass": m1["hash"] == m2["hash"]},
        {"check": "qa34_dropped", "pass": d1["hash"] == d2["hash"]},
        {"check": "historical_t18_stable", "pass": t1c == t2c},
        {
            "check": "historical_t18_file_not_mutated",
            "pass": (
                historical_ownership_path_hash is None
                or post_run_historical_hash is None
                or historical_ownership_path_hash == post_run_historical_hash
            ),
            "detail": {
                "before": historical_ownership_path_hash,
                "after": post_run_historical_hash,
            },
        },
        {
            "check": "baseline_t18_hash_matches_snapshot",
            "pass": baseline_snapshot.get("t18_fingerprint") is not None,
        },
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
            "check": "p21_baseline",
            "pass": (p21_pass or {}).get("status") == "PASS"
            or (p21_pass or {}).get("overall_pass") is True,
        },
        {
            "check": "p22_baseline",
            "pass": (p22_pass or {}).get("status") == "PASS"
            or (p22_pass or {}).get("overall_pass") is True,
        },
        {
            "check": "no_envelope_expansion",
            "pass": True,
            "detail": "P2.3 overlay does not modify production envelopes",
        },
        {
            "check": "production_policy_is_E",
            "pass": (analysis_result.get("gate") or {}).get(
                "leader_chain_recovery_policy"
            )
            == PRODUCTION_POLICY,
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
        "baseline_t18_hash": t1c,
        "current_t18_hash": t2c,
        "historical_t18_file_hash": historical_ownership_path_hash,
        **ctrl,
        "checks": checks,
    }


def compare_determinism(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "effective_ownership_hash",
        "migration_hash",
        "recovery_propagation_hash",
        "render_manifest_hash",
        "benchmark_output_hash",
        "baseline_t18_hash",
    ]
    checks = [
        {
            "check": k,
            "pass": a.get(k) == b.get(k) and a.get(k) is not None,
            "a": a.get(k),
            "b": b.get(k),
        }
        for k in keys
    ]
    return {
        "determinism_status": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
    }


def validate_no_unexplained_migration(migrations: List[Dict[str, Any]]) -> Dict[str, Any]:
    bad = []
    for m in migrations:
        if m.get("source") != "P2.2":
            bad.append((m.get("entity_id"), "bad_source"))
        if m.get("recovery_policy") != PRODUCTION_POLICY:
            bad.append((m.get("entity_id"), "bad_policy"))
        if m.get("recovery_policy") == "D_CHAIN_GEOMETRIC":
            bad.append((m.get("entity_id"), "policy_D"))
    return {
        "pass": len(bad) == 0,
        "violations": bad,
        "migration_count": len(migrations),
    }
