#!/usr/bin/env python3
"""Reconstruct W.13 traces from retained runs. No secrets."""
from pathlib import Path
import json
import sys

sys.path.insert(0, "/opt/steel-beam-estimation/SteelBeamEstimator/Version10/src")
sys.path.insert(0, "/tmp")

from resolution_trace import reconstruct_from_staging  # type: ignore

RUNS = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs")
IDS = [
    "20260826_084708_f74912b8",
    "20260826_111142_32321cb4",
    "20260826_141507_88aff694",
]

def main() -> None:
    for rid in IDS:
        staging = RUNS / rid
        trace = reconstruct_from_staging(staging, run_id=rid)
        out = staging / "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_resolution_trace.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        slim = dict(trace)
        slim["beams"] = [
            {k: b.get(k) for k in (
                "beam_id", "final_status", "reason_code", "existing_code",
                "claude_attempted", "claude_api_success", "e2_accepted",
                "d2_resolved", "r13_patch_applied", "error_type", "api_error",
                "retry_count", "attempts", "failure_category", "skip_reason",
            )}
            for b in trace.get("beams") or []
        ]
        out.write_text(json.dumps(slim, indent=2), encoding="utf-8")
        print("====", rid)
        print(json.dumps({
            "lifecycle_counts": trace.get("lifecycle_counts"),
            "reason_counts": trace.get("reason_counts"),
            "status_counts": trace.get("status_counts"),
            "identity_ok": trace.get("identity_ok"),
            "unexplained": trace.get("unexplained"),
            "handoff": trace.get("handoff"),
        }, indent=2))

if __name__ == "__main__":
    main()
