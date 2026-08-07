"""
Cross-beam entity identity helpers (read-only diagnostics).
MODEL_VERSION: 10.0.4

T18 entity ids are often beam-scoped (e.g. BAR::SYN::B14::...).
Competition validation therefore uses multiple identity keys without
changing ownership logic.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

MODEL_VERSION = "10.0.4"

_HANDLE_RE = re.compile(r"^(LDR|BAR|ANN|SEM)::([0-9A-Fa-f]+)$")
_SYN_BAR_RE = re.compile(r"^BAR::SYN::([^:]+)::(.+)$")


def normalize_text(text: Any) -> Optional[str]:
    if text is None:
        return None
    s = " ".join(str(text).upper().split())
    return s or None


def identity_keys(
    entity_id: str,
    entity_type: Optional[str] = None,
    text: Optional[str] = None,
) -> List[str]:
    """Stable identity keys for joining the same engineering object across beams."""
    keys: List[str] = []
    eid = str(entity_id or "")
    if eid:
        keys.append(f"id:{eid}")
    m = _HANDLE_RE.match(eid)
    if m:
        keys.append(f"handle:{m.group(1)}:{m.group(2).upper()}")
    # Leader/annotation handles embedded differently
    if eid.startswith("LDR::"):
        keys.append(f"leader:{eid.split('::', 1)[-1].upper()}")
    nt = normalize_text(text)
    if nt and (entity_type or "").lower() in ("annotation", "chain", ""):
        keys.append(f"ann_text:{nt}")
    elif nt and "ANN" in eid.upper():
        keys.append(f"ann_text:{nt}")
    return list(dict.fromkeys(keys))  # unique, order preserved


def primary_identity(
    entity_id: str,
    entity_type: Optional[str] = None,
    text: Optional[str] = None,
) -> str:
    """
    Primary grouping key.

    Leaders share DXF handles across beams → use leader handle.
    Bars/annotations are typically beam-scoped node ids → use exact id.
    Annotation-text cross-beam ownership is resolved separately in the
    competition engine (avoids false merges of common callouts like 2-Y12).
    """
    eid = str(entity_id or "")
    et = (entity_type or "").lower()
    if eid.startswith("LDR::") or et == "leader":
        return f"leader:{eid.split('::', 1)[-1].upper()}"
    m = _HANDLE_RE.match(eid)
    if m and m.group(1) == "LDR":
        return f"leader:{m.group(2).upper()}"
    return f"id:{eid}"


def classify_reason_bucket(ownership_reason: Optional[str], rejected_rule: Optional[str]) -> str:
    """Map persisted T18 reason/rule to diagnostic bucket (not a new engineering rule)."""
    reason = (ownership_reason or "").lower()
    rule = (rejected_rule or "").upper()

    if "neighbour" in reason or rule == "R5_NEIGHBOUR_REJECT" and "neighbour" in reason:
        return "neighbour_conflict"
    if any(
        x in reason
        for x in (
            "no_owned_leader",
            "leader_missing",
            "leader_points_to_non_owned",
            "no_owned_leader_bar_chain",
            "missing_tip",
        )
    ) or rule in ("R2_LEADER_TIP", "R3_ANNOTATION_VIA_CHAIN"):
        if "neighbour" in reason:
            return "neighbour_conflict"
        return "leader_chain"
    if any(
        x in reason
        for x in (
            "outside",
            "envelope",
            "concrete",
            "elevation",
            "support",
            "tip_outside",
            "bar_outside",
        )
    ) or rule in ("R1_PHYSICAL_BAR", "R6_VERTICAL_OWNERSHIP", "R7_LD_SUPPORT_ONLY"):
        return "geometry"
    if "stirrup" in reason or rule == "R9_STIRRUP_REGION":
        return "geometry"
    if "side_face" in reason or rule == "R8_SIDE_FACE_WEB":
        return "geometry"
    if not reason and not rule:
        return "unknown"
    return "other"
