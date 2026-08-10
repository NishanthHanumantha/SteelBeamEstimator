"""
Immutable baseline snapshot for P2.3 comparison.
MODEL_VERSION: 10.5.5
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import MODEL_VERSION, PHASE_ID
from .overlay import ownership_counts


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def _sha_file(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def snapshot_baseline(
    *,
    ownership: Dict[str, Any],
    scoped: Optional[Dict[str, Any]],
    beam_ids: List[str],
    qa30_report: Optional[Dict[str, Any]],
    p22_candidates: Dict[str, Any],
    ownership_path: Optional[Path] = None,
) -> Dict[str, Any]:
    by_beam = ownership.get("by_beam") or {}
    accepted = []
    rejected = []
    for bid in sorted(beam_ids):
        beam = by_beam.get(bid) or {}
        for nid in beam.get("accepted_node_ids") or []:
            accepted.append((bid, nid))
        for lid, lr in (beam.get("leader_results") or {}).items():
            if not lr.get("accepted"):
                rejected.append((bid, lid, lr.get("rejected_rule")))

    accepted_s = sorted(accepted)
    rejected_s = sorted(rejected)
    counts = ownership_counts(ownership, beam_ids)
    overall = (qa30_report or {}).get("overall_metrics") or {}
    fourth = next(
        (
            r
            for r in (qa30_report or {}).get("drawing_set_results") or []
            if "Fourth" in str(r.get("drawing_set") or "")
        ),
        {},
    )

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "label": "IMMUTABLE BASELINE — historical T18",
        "ownership_file_hash": _sha_file(Path(ownership_path)) if ownership_path else None,
        "ownership_content_hash": _sha(
            {
                bid: sorted((by_beam.get(bid) or {}).get("accepted_node_ids") or [])
                for bid in sorted(beam_ids)
            }
        ),
        "accepted_node_ids_hash": _sha(accepted_s),
        "rejected_leaders_hash": _sha(rejected_s),
        "t18_fingerprint": _sha(
            [
                _sha(accepted_s),
                _sha(rejected_s),
                counts,
            ]
        ),
        "p22_candidate_fingerprint": _sha(
            sorted((p22_candidates or {}).get("accepted_keys") or [])
        ),
        "counts": counts,
        "accepted_node_ids": [
            {"beam_id": b, "entity_id": e} for b, e in accepted_s
        ],
        "rejected_leaders": [
            {"beam_id": b, "entity_id": e, "rejected_rule": r}
            for b, e, r in rejected_s
        ],
        "benchmark_metrics": {
            "overall": overall,
            "fourth_set": {
                "beam_detection_pct": fourth.get("beam_detection_pct"),
                "bar_detection_pct": fourth.get("bar_detection_pct"),
                "bar_matching_pct": fourth.get("bar_accuracy_pct")
                or fourth.get("bar_matching_pct"),
                "steel_accuracy_pct": fourth.get("steel_accuracy_pct"),
                "overall_accuracy_pct": fourth.get("overall_accuracy_pct"),
            },
        },
        "scoped_node_total": sum(
            int(((scoped or {}).get("by_beam") or {}).get(b, {}).get("node_count") or 0)
            for b in beam_ids
        )
        if scoped
        else None,
    }
