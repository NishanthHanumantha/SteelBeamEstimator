"""Assign DIFFICULT / NORMAL / EASY from production-signal features. No GT."""
from __future__ import annotations

from typing import Any, Dict, List


def assign_stratum(row: Dict[str, Any]) -> str:
    feat = row.get("features") or {}
    score = int(row.get("score") or 0)
    hard = sum(
        1
        for k in (
            "OCR_CORRUPTION_SIGNAL",
            "STIRRUP_TEXT_NO_OBJECT",
            "INCOMPLETE_PARSE_SIGNAL",
            "SPARSE_REINFORCEMENT_SIGNAL",
        )
        if feat.get(k)
    )
    if hard >= 2 or score >= 10:
        return "DIFFICULT"
    easy = (
        not feat.get("OCR_CORRUPTION_SIGNAL")
        and not feat.get("STIRRUP_TEXT_NO_OBJECT")
        and not feat.get("INCOMPLETE_PARSE_SIGNAL")
        and int(feat.get("REINFORCEMENT_DENSITY") or 0) >= 4
        and bool(feat.get("HAS_TOP"))
        and bool(feat.get("HAS_BOTTOM"))
        and int(row.get("annotation_count") or 0) >= 1
        and bool(row.get("has_crop"))
    )
    if easy:
        return "EASY"
    return "NORMAL"


def attach_strata(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for row in rows:
        rec = dict(row)
        rec["stratum"] = assign_stratum(rec)
        out.append(rec)
    return out


__all__ = ["assign_stratum", "attach_strata"]
