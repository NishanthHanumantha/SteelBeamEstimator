"""Optional live Claude refresh. Official P2.5.8 uses frozen P2.5.7 replay."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from PhaseP257_unseen_drawing_controlled_vision_validation.candidate_builder import (
    build_candidates,
)
from PhaseP257_unseen_drawing_controlled_vision_validation.gt_oracle import (
    ground_truth_for_intent,
)
from PhaseP257_unseen_drawing_controlled_vision_validation.live_observer import observe_live
from PhaseP257_unseen_drawing_controlled_vision_validation.metrics import compute_cost_metrics
from PhaseP257_unseen_drawing_controlled_vision_validation.three_way import evaluate_candidate


def refresh_live(
    *,
    version10_root: Path,
    audits: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    invoked_ids = {
        a.get("candidate_id")
        for a in audits
        if a.get("invoke_claude") and a.get("candidate_id")
    }
    all_rows, _eligible = build_candidates(Path(version10_root))
    by_id = {(r.get("candidate") or {}).get("candidate_id"): r for r in all_rows}
    vision_rows: List[Dict[str, Any]] = []
    updated: List[Dict[str, Any]] = []
    for audit in audits:
        cid = audit.get("candidate_id")
        if cid not in invoked_ids:
            updated.append(audit)
            continue
        row = by_id.get(cid)
        if row is None:
            updated.append({**audit, "vision_error": "LIVE_CANDIDATE_MISSING"})
            continue
        obs = observe_live(candidate=row["candidate"], version10_root=Path(version10_root))
        vision_rows.append({"invoke_claude": True, "vision_obs": obs})
        det = (row.get("deterministic") or {}).get("deterministic_result") or audit.get(
            "deterministic_result"
        )
        gt = audit.get("ground_truth") or ground_truth_for_intent(
            det or {}, str(audit.get("annotation_text") or "")
        )
        tw = evaluate_candidate(
            deterministic=row.get("deterministic") or {"deterministic_result": det},
            vision=obs.get("validated_interpretation"),
            ground_truth=gt,
            accepted_shadow_fields=[],
        )
        nxt = dict(audit)
        nxt["vision_result"] = obs.get("validated_interpretation")
        nxt["vision_api_ok"] = obs.get("api_ok")
        nxt["vision_error"] = obs.get("error")
        nxt["three_way"] = tw
        nxt["model"] = obs.get("model")
        nxt["prompt_version"] = obs.get("prompt_version")
        nxt["schema_version"] = obs.get("schema_version")
        nxt["evidence_fingerprint"] = obs.get("evidence_fingerprint")
        nxt["live_refresh"] = True
        updated.append(nxt)
    cost = compute_cost_metrics(
        vision_rows=vision_rows,
        true_incremental_field_count=0,
        eligible_count=len(invoked_ids),
    )
    cost["replay"] = False
    return updated, cost


def replay_cost(n_audits: int) -> Dict[str, Any]:
    return {
        "live_claude_calls": 0,
        "failed_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost_usd": 0.0,
        "replay": True,
        "replayed_p257_audits": n_audits,
        "note": "REPLAY_P257_LIVE_RESULTS — Claude new spend = $0",
    }


__all__ = ["refresh_live", "replay_cost"]
