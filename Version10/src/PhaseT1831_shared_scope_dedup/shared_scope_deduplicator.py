"""
T1.8.3.1 — Deterministic Shared Engineering Scope Deduplicator.
MODEL_VERSION: 9.5.4

Collapses duplicate scopes that represent the same engineering intent
(same normalized text + same owner beam set). Does NOT collapse by text alone
(e.g. two independent Ld scopes on different beam groups stay separate).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "9.5.4"


def normalize_annotation_text(text: str) -> str:
    t = (text or "").upper().replace("%%U", "")
    t = re.sub(r"[^\w\s@/\-\.]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def scope_uniqueness_key(scope: Dict[str, Any]) -> Tuple[Any, ...]:
    """
    Stable key for engineering-intent identity.

    Components:
      - normalized annotation text
      - sorted owner / member beams
      - scope_type

    Annotation UUID / leader id are intentionally NOT required for the key
    when member beam sets match — graph may duplicate one physical DXF note
    onto multiple annotation nodes. Different beam groups with the same text
    remain distinct because sorted(owner_beams) differs.
    """
    text = normalize_annotation_text(str(scope.get("annotation_text") or ""))
    beams = tuple(sorted(str(b) for b in (scope.get("member_beams") or [])))
    stype = str(scope.get("scope_type") or "")
    return (text, beams, stype)


def _annotation_y(
    scope: Dict[str, Any], candidates_by_id: Optional[Dict[str, Dict[str, Any]]]
) -> float:
    for aid in scope.get("member_annotations") or []:
        c = (candidates_by_id or {}).get(str(aid)) or {}
        try:
            return float(c.get("y") or 0.0)
        except Exception:
            continue
    return 0.0


def deduplicate_scopes(
    scopes: List[Dict[str, Any]],
    *,
    candidates: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Return deduplicated scope list + diagnostics.

    Non-shared (single-beam) scopes are kept as-is (keyed individually by
    annotation id so they never collide with multi-beam SFR scopes incorrectly).
    """
    kept: List[Dict[str, Any]] = []
    key_to_index: Dict[Tuple[Any, ...], int] = {}
    duplicates_removed: List[Dict[str, Any]] = []
    merge_log: List[Dict[str, Any]] = []
    candidates_by_id = {
        str(c["annotation_id"]): c for c in (candidates or []) if c.get("annotation_id")
    }

    def _better(new: Dict[str, Any], old: Dict[str, Any]) -> bool:
        """Prefer higher confidence; on tie prefer higher annotation Y (T1.8.3 merge)."""
        nc, oc = float(new.get("confidence") or 0), float(old.get("confidence") or 0)
        if nc > oc:
            return True
        if nc < oc:
            return False
        return _annotation_y(new, candidates_by_id) > _annotation_y(
            old, candidates_by_id
        )

    for sc in scopes:
        sc = dict(sc)
        if not sc.get("shared"):
            # Exclusive / single-beam: unique by annotation membership
            anns = tuple(sorted(str(a) for a in (sc.get("member_annotations") or [])))
            key = ("__single__", anns, str(sc.get("scope_type") or ""))
        else:
            key = scope_uniqueness_key(sc)

        if key not in key_to_index:
            key_to_index[key] = len(kept)
            sc["dedup_key"] = list(key) if isinstance(key[1], tuple) else list(key)
            sc["deduplicated"] = False
            kept.append(sc)
            continue

        # Duplicate shared scope — keep a single canonical annotation id on the
        # survivor (do NOT union member_annotations, or registry would re-fork).
        idx = key_to_index[key]
        survivor = kept[idx]
        if _better(sc, survivor):
            old = survivor
            absorbed_anns = sorted(
                set(old.get("member_annotations") or [])
                | set(old.get("absorbed_annotation_ids") or [])
                | set(sc.get("member_annotations") or [])
            )
            sc["absorbed_annotation_ids"] = [
                a for a in absorbed_anns if a not in (sc.get("member_annotations") or [])
            ]
            sc["dedup_key"] = list(key)
            sc["deduplicated"] = False
            sc["absorbed_scope_ids"] = list(old.get("absorbed_scope_ids") or []) + [
                old.get("scope_id")
            ]
            sc["reason"] = (
                str(sc.get("reason") or "")
                + ";dedup_survived_over="
                + str(old.get("scope_id"))
            )
            kept[idx] = sc
            duplicates_removed.append(
                {
                    "removed_scope_id": old.get("scope_id"),
                    "kept_scope_id": sc.get("scope_id"),
                    "key": list(key),
                    "reason": "replaced_by_higher_rank_duplicate",
                }
            )
        else:
            absorbed = list(survivor.get("absorbed_annotation_ids") or [])
            for a in sc.get("member_annotations") or []:
                if a not in (survivor.get("member_annotations") or []) and a not in absorbed:
                    absorbed.append(a)
            survivor["absorbed_annotation_ids"] = absorbed
            survivor.setdefault("absorbed_scope_ids", [])
            survivor["absorbed_scope_ids"].append(sc.get("scope_id"))
            survivor["reason"] = (
                str(survivor.get("reason") or "")
                + ";dedup_absorbed="
                + str(sc.get("scope_id"))
            )
            duplicates_removed.append(
                {
                    "removed_scope_id": sc.get("scope_id"),
                    "kept_scope_id": survivor.get("scope_id"),
                    "key": list(key),
                    "reason": "duplicate_shared_scope_same_text_and_owner_beams",
                }
            )
        merge_log.append(
            {
                "key": list(key),
                "kept": kept[idx].get("scope_id"),
                "removed": duplicates_removed[-1]["removed_scope_id"],
            }
        )

    shared_kept = [s for s in kept if s.get("shared")]
    return {
        "model_version": MODEL_VERSION,
        "scopes_before": len(scopes),
        "scopes_after": len(kept),
        "shared_scopes_before": sum(1 for s in scopes if s.get("shared")),
        "shared_scopes_after": len(shared_kept),
        "duplicates_removed": duplicates_removed,
        "merge_log": merge_log,
        "scopes": kept,
        "registry_deduplicated": len(duplicates_removed) > 0
        or len(shared_kept) <= sum(1 for s in scopes if s.get("shared")),
    }
