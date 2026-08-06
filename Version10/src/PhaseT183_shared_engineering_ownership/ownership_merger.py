"""
T1.8.3 — Additive merge: owned + shared → effective (runtime only).
MODEL_VERSION: 9.5.3

Never mutates BeamOwnership / BeamScopedAnnotations artefacts.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Set

MODEL_VERSION = "9.5.3"


def _norm_text(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").upper().replace("%%U", "")).strip()


def _owned_ann_ids(ownership: Dict[str, Any]) -> Set[str]:
    return {
        str(a["id"])
        for a in (ownership.get("accepted_annotations") or [])
        if a.get("id")
    }


def merge_beam_ownership(
    beam_id: str,
    ownership: Dict[str, Any],
    registry_by_beam: Dict[str, List[Dict[str, Any]]],
    *,
    enable_shared: bool = True,
) -> Dict[str, Any]:
    """
    Produce per-beam merge view:

      owner_annotations  — unchanged from T1.8 accepted
      shared_annotations — additive shared SFR (excluding already owned ids)
      effective_annotations — union
    """
    owned_ids = _owned_ann_ids(ownership)
    owned = [
        {
            "id": a.get("id"),
            "text": a.get("text"),
            "source": "owned",
        }
        for a in (ownership.get("accepted_annotations") or [])
    ]
    owned_texts = {_norm_text(o.get("text") or "") for o in owned}

    shared_raw = list((registry_by_beam or {}).get(beam_id) or []) if enable_shared else []
    shared = []
    for s in shared_raw:
        aid = str(s.get("annotation_id") or "")
        text = str(s.get("annotation_text") or "")
        # Skip if already exclusively owned on this beam (id or equivalent text)
        if aid and aid in owned_ids:
            continue
        if _norm_text(text) in owned_texts:
            continue
        extra = s.get("extra") or {}
        shared.append(
            {
                "id": aid,
                "text": text,
                "source": "shared",
                "scope_id": s.get("scope_id"),
                "scope_type": s.get("scope_type"),
                "primary_beam": s.get("primary_beam"),
                "confidence": s.get("confidence"),
                "reason": s.get("reason"),
                "leader_ids": s.get("leader_ids") or [],
                "y": extra.get("y"),
            }
        )

    # Deduplicate shared by annotation id AND normalized text.
    # Prefer higher-confidence / higher-Y annotation when texts collide
    # (continuous SFR callouts typically sit above the framing line).
    by_text: Dict[str, Dict[str, Any]] = {}
    for s in shared:
        nt = _norm_text(s.get("text") or "") or str(s.get("id"))
        prev = by_text.get(nt)
        if prev is None:
            by_text[nt] = s
            continue
        prev_c = float(prev.get("confidence") or 0)
        cur_c = float(s.get("confidence") or 0)
        prev_y = float(prev.get("y") or 0)
        cur_y = float(s.get("y") or 0)
        if cur_c > prev_c or (cur_c == prev_c and cur_y > prev_y):
            by_text[nt] = s
    shared_dedup = list(by_text.values())

    effective = list(owned)
    owned_id_set = {o["id"] for o in owned if o.get("id")}
    for s in shared_dedup:
        if s["id"] not in owned_id_set:
            effective.append(s)

    return {
        "beam": beam_id,
        "model_version": MODEL_VERSION,
        "enable_shared": enable_shared,
        "owner_annotations": owned,
        "shared_annotations": shared_dedup,
        "effective_annotations": effective,
        "counts": {
            "owned": len(owned),
            "shared": len(shared_dedup),
            "effective": len(effective),
        },
    }
