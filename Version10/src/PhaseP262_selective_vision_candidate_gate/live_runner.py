"""Optional live Vision for CALL beams only. Hard budget. Default path is replay."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP261_stratified_vision_candidate_recovery.config import MAX_LIVE_CALLS as P261_MAX
from PhaseP261_stratified_vision_candidate_recovery.vision_observer import observe_region

from .config import CLAUDE_MODEL, DECISION_CALL, MAX_LIVE_CALLS, MODE_LIVE, TEMPERATURE


def run_live_for_calls(
    *,
    version10_root: Path,
    decisions: List[Dict[str, Any]],
    regions_by_id: Dict[str, Dict[str, Any]],
    cache_root: Path,
    max_live_calls: int = MAX_LIVE_CALLS,
) -> Dict[str, Any]:
    """Live Vision is optional and budgeted. Not the default P2.6.2 path."""
    live_used = 0
    observations: List[Dict[str, Any]] = []
    for d in decisions:
        if d.get("decision") != DECISION_CALL:
            continue
        region = regions_by_id.get(d.get("region_id") or "")
        if not region:
            observations.append(
                {
                    "beam_id": d.get("beam_id"),
                    "error": "missing_region_package",
                    "live_call": False,
                    "candidates": [],
                }
            )
            continue
        obs = observe_region(
            version10_root=version10_root,
            region=region,
            cache_root=cache_root,
            mode=MODE_LIVE,
            live_calls_used=live_used,
            max_live_calls=min(int(max_live_calls), int(P261_MAX)),
        )
        if obs.get("live_call"):
            live_used += 1
        observations.append(obs)
        if obs.get("budget_stop"):
            break
    return {
        "vision_model": CLAUDE_MODEL,
        "temperature": TEMPERATURE,
        "live_calls": live_used,
        "observations": observations,
        "note": "Optional live validation. Default P2.6.2 execution is REPLAY_P261_CACHED.",
    }


__all__ = ["run_live_for_calls"]
