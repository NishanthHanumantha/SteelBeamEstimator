"""Order-invariant matching with ambiguity detection. Reuses D.1 scoring. No beam-ID logic."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.matching import _score
from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.vision_validator import flag_possible_duplicates

from .config import REASON_AMBIGUOUS, REASON_POSSIBLE_DUP


def match_groups_conservative(vision: List[Dict[str, Any]], det: List[Dict[str, Any]]) -> Dict[str, Any]:
    vision = list(vision or [])
    det = list(det or [])
    ranked: List[Tuple[int, int, int]] = []
    for i, vg in enumerate(vision):
        for j, dg in enumerate(det):
            ranked.append((_score(vg, dg), i, j))
    ranked.sort(key=lambda t: (-t[0], t[1], t[2]))

    best_for_v: Dict[int, int] = {}
    second_for_v: Dict[int, int] = {}
    for score, i, j in ranked:
        if i not in best_for_v:
            best_for_v[i] = score
        elif i not in second_for_v:
            second_for_v[i] = score

    ambiguous_v = {
        i for i, best in best_for_v.items() if best >= 4 and second_for_v.get(i) == best
    }

    pairs = []
    used_d = set()
    used_v = set()
    ambiguous = []
    for score, i, j in ranked:
        if score < 4:
            break
        if i in ambiguous_v:
            if i not in used_v:
                ambiguous.append(
                    {
                        "code": REASON_AMBIGUOUS,
                        "vision_index": i,
                        "deterministic_index": j,
                        "score": score,
                        "vision_id": vision[i].get("physical_group_id"),
                        "deterministic_id": det[j].get("physical_group_id"),
                        "reason": "TIED_TOP_SCORE",
                    }
                )
                used_v.add(i)
            continue
        if i in used_v or j in used_d:
            continue
        used_v.add(i)
        used_d.add(j)
        pairs.append(
            {
                "vision_index": i,
                "deterministic_index": j,
                "score": score,
                "vision_id": vision[i].get("physical_group_id"),
                "deterministic_id": det[j].get("physical_group_id"),
            }
        )
    vision_only = [i for i in range(len(vision)) if i not in used_v]
    det_only = [j for j in range(len(det)) if j not in used_d]
    dups = flag_possible_duplicates(vision)
    return {
        "pairs": pairs,
        "vision_only_indices": vision_only,
        "deterministic_only_indices": det_only,
        "ambiguous": ambiguous,
        "possible_duplicates": dups,
        "possible_duplicate_code": REASON_POSSIBLE_DUP,
    }


def match_stirrups_conservative(vision: List[Dict[str, Any]], det: List[Dict[str, Any]]) -> Dict[str, Any]:
    return match_groups_conservative(vision, det)


__all__ = ["match_groups_conservative", "match_stirrups_conservative"]
