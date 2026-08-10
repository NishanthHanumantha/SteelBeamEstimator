"""
Neighbour contamination guard for QA.4.2 recovery candidates.
MODEL_VERSION: 10.5.1
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Set


def build_owned_elsewhere_index(migration_doc: Optional[Dict[str, Any]]) -> Set[str]:
    ids: Set[str] = set()
    for m in (migration_doc or {}).get("migrations") or []:
        eid = str(m.get("entity_id") or "")
        if eid:
            ids.add(eid)
            orig = str(m.get("originally_candidate") or "")
            if orig:
                ids.add(f"{orig}::{eid}")
    return ids


def guard_candidate(
    *,
    eligibility: Dict[str, Any],
    audit_row: Dict[str, Any],
    production_accepted: Set[str],
    production_accepted_other_beams: Dict[str, Set[str]],
    owned_elsewhere_ids: Set[str],
) -> Dict[str, Any]:
    """
    Return contamination assessment. Does not assign ownership.
    """
    eid = str(eligibility.get("entity_id") or "")
    bid = str(eligibility.get("beam_id") or "")
    flags = []
    blocked = False

    if eligibility.get("neighbour_ambiguity"):
        blocked = True
        flags.append("neighbour_ambiguity")
    if eligibility.get("inside_other_beam_envelope"):
        blocked = True
        flags.append("inside_other_beam_envelope")
    if eid in owned_elsewhere_ids:
        blocked = True
        flags.append("owned_elsewhere")

    # Cross-beam: same entity_id accepted on another priority beam
    other_owners = [
        ob
        for ob, s in production_accepted_other_beams.items()
        if ob != bid and eid in s
    ]
    if other_owners:
        blocked = True
        flags.append(f"accepted_on_other_beams:{','.join(sorted(other_owners))}")

    already = eid in production_accepted
    return {
        "contamination_blocked": blocked,
        "contamination_flags": flags,
        "already_in_production_accepted": already,
        "other_beam_owners": other_owners,
        "owned_elsewhere": eid in owned_elsewhere_ids,
    }


def contamination_report(
    audit_rows: List[Dict[str, Any]],
    *,
    duplicate_stable_keys: List[str],
    multi_beam_assignments: List[Dict[str, Any]],
    illegal_cross_beam: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "cross_beam_contamination_count": len(illegal_cross_beam),
        "duplicate_stable_key_count": len(duplicate_stable_keys),
        "duplicate_stable_keys": sorted(duplicate_stable_keys),
        "multi_beam_assignments": multi_beam_assignments,
        "illegal_cross_beam": illegal_cross_beam,
        "outcomes": dict(Counter(r.get("recovery_outcome") for r in audit_rows)),
        "pass": (
            len(illegal_cross_beam) == 0
            and len(duplicate_stable_keys) == 0
            and len(multi_beam_assignments) == 0
        ),
    }
