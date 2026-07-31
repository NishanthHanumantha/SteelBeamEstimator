"""
beam_matcher.py — Deterministic beam matching (ID / alias / normalized name).
No fuzzy AI. MODEL_VERSION: 8.9.1
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from gt_models import BeamRecord, NormalizedWorkbook

MODEL_VERSION = "9.1.0"


def _norm(bid: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(bid or "").upper())


class BeamMatcher:
    """Match Estimator beams to Model beams using deterministic rules."""

    def match(
        self,
        estimator: NormalizedWorkbook,
        model: NormalizedWorkbook,
    ) -> Dict[str, Any]:
        est_beams = list(estimator.beams)
        mod_beams = list(model.beams)

        # Index model by all aliases
        mod_index: Dict[str, BeamRecord] = {}
        for b in mod_beams:
            for key in {_norm(b.beam_id), *(_norm(a) for a in b.aliases)}:
                if key and key not in mod_index:
                    mod_index[key] = b

        used_model: Set[str] = set()
        pairs: List[Dict[str, Any]] = []
        unmatched_est: List[str] = []

        for eb in est_beams:
            candidates = {_norm(eb.beam_id), *(_norm(a) for a in eb.aliases)}
            hit: Optional[BeamRecord] = None
            method = ""
            for c in candidates:
                if c and c in mod_index and mod_index[c].beam_id not in used_model:
                    hit = mod_index[c]
                    method = "EXACT_ID" if c == _norm(eb.beam_id) else "ALIAS"
                    break
            if hit is None:
                # Numeric-only fallback: B17 ↔ 17
                num = re.sub(r"^[A-Z]+", "", _norm(eb.beam_id))
                if num and num in mod_index and mod_index[num].beam_id not in used_model:
                    hit = mod_index[num]
                    method = "NUMERIC_ALIAS"
            if hit is None:
                unmatched_est.append(eb.beam_id)
                pairs.append({
                    "estimator_beam_id": eb.beam_id,
                    "model_beam_id": None,
                    "matched": False,
                    "method": None,
                    "status": "MISSING",
                })
            else:
                used_model.add(hit.beam_id)
                pairs.append({
                    "estimator_beam_id": eb.beam_id,
                    "model_beam_id": hit.beam_id,
                    "matched": True,
                    "method": method,
                    "status": "MATCHED",
                })

        extra = [b.beam_id for b in mod_beams if b.beam_id not in used_model]
        for mid in extra:
            pairs.append({
                "estimator_beam_id": None,
                "model_beam_id": mid,
                "matched": False,
                "method": None,
                "status": "EXTRA",
            })

        total_est = len(est_beams)
        detected = sum(1 for p in pairs if p["status"] == "MATCHED")
        return {
            "model_version": MODEL_VERSION,
            "estimator_beams": total_est,
            "model_beams": len(mod_beams),
            "detected_beams": detected,
            "undetected_beams": len(unmatched_est),
            "extra_beams": len(extra),
            "detection_pct": round(100.0 * detected / total_est, 2) if total_est else 0.0,
            "matching_pct": round(100.0 * detected / total_est, 2) if total_est else 0.0,
            "correctly_matched": detected,
            "incorrect_beams": len(unmatched_est) + len(extra),
            "missing_ids": unmatched_est,
            "extra_ids": extra,
            "pairs": pairs,
        }

    def matched_beam_pairs(
        self,
        estimator: NormalizedWorkbook,
        model: NormalizedWorkbook,
        matching: Dict[str, Any],
    ) -> List[Tuple[BeamRecord, BeamRecord]]:
        est_map = {b.beam_id: b for b in estimator.beams}
        mod_map = {b.beam_id: b for b in model.beams}
        out: List[Tuple[BeamRecord, BeamRecord]] = []
        for p in matching.get("pairs") or []:
            if not p.get("matched"):
                continue
            eb = est_map.get(p["estimator_beam_id"])
            mb = mod_map.get(p["model_beam_id"])
            if eb and mb:
                out.append((eb, mb))
        return out
