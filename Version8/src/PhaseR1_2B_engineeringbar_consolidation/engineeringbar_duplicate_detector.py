"""
EngineeringBarDuplicateDetector — evidence-based duplicate detection.
MODEL_VERSION: 8.3.1

Does NOT use object identity. Scores engineering similarity so that multiple
annotations describing the same physical reinforcement are clustered.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "8.3.1"

# Minimum score to treat two bars as the same physical reinforcement
DEFAULT_THRESHOLD = 0.85

_WEIGHTS = {
    "same_beam": 0.20,
    "same_role": 0.20,
    "same_diameter": 0.20,
    "same_quantity": 0.15,
    "same_label": 0.10,
    "same_zone": 0.05,
    "same_spacing": 0.05,
    "same_ld": 0.05,
}


def _norm_label(label: str) -> str:
    if not label:
        return ""
    t = label.upper().replace(" ", "")
    t = t.replace("T", "Y").replace("R", "Y")
    return t


def _spacing_key(bar: Dict[str, Any]) -> Optional[float]:
    sp = bar.get("spacing_mm")
    if sp is not None:
        return float(sp)
    lbl = str(bar.get("bar_label") or "")
    m = re.search(r"@\s*(\d+)", lbl)
    return float(m.group(1)) if m else None


def similarity_score(a: Dict[str, Any], b: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Return (score 0..1, evidence list). Different beams always score 0."""
    evidence: List[str] = []
    score = 0.0

    if a.get("beam_id") != b.get("beam_id"):
        return 0.0, ["different_beam"]
    score += _WEIGHTS["same_beam"]
    evidence.append("same_beam")

    if a.get("bar_role") == b.get("bar_role"):
        score += _WEIGHTS["same_role"]
        evidence.append("same_role")
    else:
        return score, evidence  # different roles cannot be same physical member

    dia_a = float(a.get("diameter_mm") or 0)
    dia_b = float(b.get("diameter_mm") or 0)
    if abs(dia_a - dia_b) < 0.1:
        score += _WEIGHTS["same_diameter"]
        evidence.append("same_diameter")
    else:
        return score, evidence

    qty_a = int(a.get("quantity") or 0)
    qty_b = int(b.get("quantity") or 0)
    if qty_a == qty_b and qty_a > 0:
        score += _WEIGHTS["same_quantity"]
        evidence.append("same_quantity")

    la, lb = _norm_label(a.get("bar_label") or ""), _norm_label(b.get("bar_label") or "")
    if la and lb and la == lb:
        score += _WEIGHTS["same_label"]
        evidence.append("same_label")

    if a.get("zone") and a.get("zone") == b.get("zone"):
        score += _WEIGHTS["same_zone"]
        evidence.append("same_zone")

    sa, sb = _spacing_key(a), _spacing_key(b)
    role = a.get("bar_role")
    if role == "STIRRUP":
        # Spacing is identity for stirrups — mismatch blocks consolidation
        if sa is not None and sb is not None and abs(sa - sb) < 0.5:
            score += _WEIGHTS["same_spacing"]
            evidence.append("same_spacing")
        elif sa is not None and sb is not None and abs(sa - sb) >= 0.5:
            evidence.append("different_stirrup_spacing")
            return min(score, 0.5), evidence
    elif sa is not None and sb is not None and abs(sa - sb) < 0.5:
        score += _WEIGHTS["same_spacing"]
        evidence.append("same_spacing")

    lda, ldb = a.get("development_length_mm"), b.get("development_length_mm")
    if lda is not None and ldb is not None and lda == ldb:
        score += _WEIGHTS["same_ld"]
        evidence.append("same_ld")

    return round(score, 4), evidence


class EngineeringBarDuplicateDetector:
    """Detect duplicate EngineeringBars using engineering similarity."""

    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        self.threshold = threshold

    def audit(self, beam_models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Flatten and audit every EngineeringBar."""
        records = []
        for bm in beam_models:
            bid = bm.get("beam_id")
            for idx, bar in enumerate(bm.get("bars") or []):
                rec = dict(bar)
                rec["_beam_index"] = idx
                rec["_global_id"] = f"{bid}::{idx}"
                rec["beam_id"] = bid
                records.append(rec)

        role_counts: Dict[str, int] = defaultdict(int)
        dia_counts: Dict[str, int] = defaultdict(int)
        for r in records:
            role_counts[str(r.get("bar_role"))] += 1
            dia_counts[str(int(float(r.get("diameter_mm") or 0)))] += int(r.get("quantity") or 0)

        return {
            "model_version": MODEL_VERSION,
            "total_engineering_bars": len(records),
            "total_beams": len(beam_models),
            "role_counts": dict(role_counts),
            "diameter_quantity_counts": dict(dia_counts),
            "bars": [
                {
                    "global_id": r["_global_id"],
                    "beam_id": r.get("beam_id"),
                    "bar_role": r.get("bar_role"),
                    "diameter_mm": r.get("diameter_mm"),
                    "quantity": r.get("quantity"),
                    "bar_label": r.get("bar_label"),
                    "zone": r.get("zone"),
                    "spacing_mm": r.get("spacing_mm"),
                    "development_length_mm": r.get("development_length_mm"),
                    "confidence": (r.get("engineering_metadata") or {}).get("confidence"),
                }
                for r in records
            ],
        }

    def detect(self, beam_models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        For each beam, cluster bars by pairwise similarity >= threshold.
        Returns duplicate groups and similarity score matrix samples.
        """
        groups: List[Dict[str, Any]] = []
        score_samples: List[Dict[str, Any]] = []
        group_id = 0

        for bm in beam_models:
            bid = bm.get("beam_id")
            bars = list(bm.get("bars") or [])
            n = len(bars)
            if n <= 1:
                continue

            parent = list(range(n))

            def find(i: int) -> int:
                while parent[i] != i:
                    parent[i] = parent[parent[i]]
                    i = parent[i]
                return i

            def union(i: int, j: int) -> None:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri

            for i in range(n):
                for j in range(i + 1, n):
                    score, evid = similarity_score(bars[i], bars[j])
                    if score >= self.threshold:
                        union(i, j)
                        score_samples.append({
                            "beam_id": bid,
                            "bar_i": i,
                            "bar_j": j,
                            "label_i": bars[i].get("bar_label"),
                            "label_j": bars[j].get("bar_label"),
                            "score": score,
                            "evidence": evid,
                        })

            clusters: Dict[int, List[int]] = defaultdict(list)
            for i in range(n):
                clusters[find(i)].append(i)

            for root, members in clusters.items():
                if len(members) < 2:
                    continue
                group_id += 1
                groups.append({
                    "group_id": f"DUP-{bid}-{group_id:03d}",
                    "beam_id": bid,
                    "member_indices": members,
                    "size": len(members),
                    "bar_role": bars[members[0]].get("bar_role"),
                    "diameter_mm": bars[members[0]].get("diameter_mm"),
                    "quantity": bars[members[0]].get("quantity"),
                    "labels": [bars[m].get("bar_label") for m in members],
                    "reason": "engineering_similarity>=threshold",
                    "threshold": self.threshold,
                })

        return {
            "model_version": MODEL_VERSION,
            "threshold": self.threshold,
            "duplicate_group_count": len(groups),
            "bars_in_duplicate_groups": sum(g["size"] for g in groups),
            "redundant_bar_count": sum(g["size"] - 1 for g in groups),
            "groups": groups,
            "similarity_scores": score_samples,
        }
