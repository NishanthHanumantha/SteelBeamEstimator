"""
Part 10 — Prove QA.3.3 / T18 ownership decisions unchanged.
MODEL_VERSION: 10.0.4
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "10.0.4"


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _sha(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def snapshot_qa33_decisions(
    ownership_scores: Optional[Dict[str, Any]],
    decision_traces: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Fingerprint owned/rejected entity sets and scores from QA.3.3 artefacts."""
    owned = []
    rejected = []
    scores = []
    for beam in (ownership_scores or {}).get("beams") or []:
        bid = beam.get("beam_id")
        for s in beam.get("t18_scored_entities") or []:
            row = {
                "beam_id": bid,
                "entity_id": s.get("entity_id"),
                "accepted": s.get("accepted"),
                "ownership_score": s.get("total_ownership_score"),
                "ownership_reason": s.get("ownership_reason"),
                "rejected_rule": s.get("rejected_rule"),
            }
            scores.append(row)
            if s.get("accepted"):
                owned.append((bid, s.get("entity_id")))
            else:
                rejected.append((bid, s.get("entity_id")))

    trace_outcomes = []
    for beam in (decision_traces or {}).get("beams") or []:
        bid = beam.get("beam_id")
        for t in beam.get("traces") or []:
            trace_outcomes.append(
                (bid, t.get("entity_id"), t.get("outcome"))
            )

    owned_s = sorted(owned, key=lambda x: (str(x[0]), str(x[1])))
    rejected_s = sorted(rejected, key=lambda x: (str(x[0]), str(x[1])))
    scores_s = sorted(scores, key=lambda r: (str(r["beam_id"]), str(r["entity_id"])))
    traces_s = sorted(trace_outcomes, key=lambda x: (str(x[0]), str(x[1]), str(x[2])))

    return {
        "owned_count": len(owned_s),
        "rejected_count": len(rejected_s),
        "score_row_count": len(scores_s),
        "trace_outcome_count": len(traces_s),
        "owned_hash": _sha(owned_s),
        "rejected_hash": _sha(rejected_s),
        "scores_hash": _sha(scores_s),
        "traces_hash": _sha(traces_s),
        "owned": owned_s,
        "rejected": rejected_s,
        "scores": scores_s,
    }


def snapshot_t18_decisions(
    beam_ownership: Optional[Dict[str, Any]], priority_beams: List[str]
) -> Dict[str, Any]:
    by = (beam_ownership or {}).get("by_beam") or {}
    owned = []
    rejected = []
    scores = []
    for bid in priority_beams:
        own = by.get(bid) or {}
        for ann in (own.get("accepted_annotations") or []):
            owned.append((bid, ann.get("id"), "ann"))
            scores.append(
                (bid, ann.get("id"), True, ann.get("ownership_score"), ann.get("ownership_reason"))
            )
        for ann in (own.get("rejected_annotations") or []):
            rejected.append((bid, ann.get("id"), "ann"))
            scores.append(
                (bid, ann.get("id"), False, ann.get("ownership_score"), ann.get("ownership_reason"))
            )
        for nid, res in (own.get("bar_results") or {}).items():
            res = res or {}
            tup = (bid, nid, "bar")
            if res.get("accepted"):
                owned.append(tup)
            else:
                rejected.append(tup)
            scores.append(
                (bid, nid, bool(res.get("accepted")), res.get("ownership_score"), res.get("ownership_reason"))
            )
        for nid, res in (own.get("leader_results") or {}).items():
            res = res or {}
            tup = (bid, nid, "leader")
            if res.get("accepted"):
                owned.append(tup)
            else:
                rejected.append(tup)
            scores.append(
                (
                    bid,
                    nid,
                    bool(res.get("accepted")),
                    res.get("ownership_score"),
                    res.get("ownership_reason"),
                )
            )
    owned_s = sorted(owned)
    rejected_s = sorted(rejected)
    scores_s = sorted(scores)
    return {
        "owned_count": len(owned_s),
        "rejected_count": len(rejected_s),
        "owned_hash": _sha(owned_s),
        "rejected_hash": _sha(rejected_s),
        "scores_hash": _sha(scores_s),
    }


def verify_regression(
    *,
    qa33_before: Dict[str, Any],
    qa33_after: Dict[str, Any],
    t18_before: Dict[str, Any],
    t18_after: Dict[str, Any],
    qa33_files: Dict[str, str],
) -> Dict[str, Any]:
    checks = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    add(
        "qa33_owned_identical",
        qa33_before.get("owned_hash") == qa33_after.get("owned_hash"),
        f"{qa33_before.get('owned_hash')} vs {qa33_after.get('owned_hash')}",
    )
    add(
        "qa33_rejected_identical",
        qa33_before.get("rejected_hash") == qa33_after.get("rejected_hash"),
        f"{qa33_before.get('rejected_hash')} vs {qa33_after.get('rejected_hash')}",
    )
    add(
        "qa33_scores_identical",
        qa33_before.get("scores_hash") == qa33_after.get("scores_hash"),
        f"{qa33_before.get('scores_hash')} vs {qa33_after.get('scores_hash')}",
    )
    add(
        "qa33_traces_identical",
        qa33_before.get("traces_hash") == qa33_after.get("traces_hash"),
        f"{qa33_before.get('traces_hash')} vs {qa33_after.get('traces_hash')}",
    )
    add(
        "t18_owned_identical",
        t18_before.get("owned_hash") == t18_after.get("owned_hash"),
        f"{t18_before.get('owned_hash')} vs {t18_after.get('owned_hash')}",
    )
    add(
        "t18_rejected_identical",
        t18_before.get("rejected_hash") == t18_after.get("rejected_hash"),
        f"{t18_before.get('rejected_hash')} vs {t18_after.get('rejected_hash')}",
    )
    add(
        "t18_scores_identical",
        t18_before.get("scores_hash") == t18_after.get("scores_hash"),
        f"{t18_before.get('scores_hash')} vs {t18_after.get('scores_hash')}",
    )

    # File hashes of QA.3.3 inputs (read-only consumption)
    for label, path in qa33_files.items():
        p = Path(path) if path else None
        add(f"qa33_file_exists:{label}", bool(p and p.exists()), str(path))

    overall = all(c["pass"] for c in checks)
    return {
        "model_version": MODEL_VERSION,
        "overall_pass": overall,
        "ownership_decisions_changed": not overall,
        "checks": checks,
        "qa33_snapshot": {
            "owned_count": qa33_before.get("owned_count"),
            "rejected_count": qa33_before.get("rejected_count"),
            "owned_hash": qa33_before.get("owned_hash"),
            "rejected_hash": qa33_before.get("rejected_hash"),
            "scores_hash": qa33_before.get("scores_hash"),
            "traces_hash": qa33_before.get("traces_hash"),
        },
        "t18_snapshot": {
            "owned_count": t18_before.get("owned_count"),
            "rejected_count": t18_before.get("rejected_count"),
            "owned_hash": t18_before.get("owned_hash"),
            "rejected_hash": t18_before.get("rejected_hash"),
            "scores_hash": t18_before.get("scores_hash"),
        },
    }
