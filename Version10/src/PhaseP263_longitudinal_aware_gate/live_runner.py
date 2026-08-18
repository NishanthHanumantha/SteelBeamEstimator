"""Optional live Vision for CALL beams only. Default P2.6.3 path is cached replay."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .config import CLAUDE_MODEL, DECISION_CALL, MAX_LIVE_CALLS, TEMPERATURE


def run_live_for_calls(
    *,
    version10_root: Path,
    decisions: List[Dict[str, Any]],
    regions_by_id: Dict[str, Dict[str, Any]],
    cache_root: Path,
    max_live_calls: int = MAX_LIVE_CALLS,
) -> Dict[str, Any]:
    del version10_root, regions_by_id, cache_root
    n_call = sum(1 for d in decisions if d.get("decision") == DECISION_CALL)
    return {
        "vision_model": CLAUDE_MODEL,
        "temperature": TEMPERATURE,
        "live_calls": 0,
        "max_live_calls": int(max_live_calls),
        "call_beams": n_call,
        "observations": [],
        "note": "Live Vision is disabled for P2.6.3. Execution is REPLAY_P261_CACHED only.",
    }


__all__ = ["run_live_for_calls"]
